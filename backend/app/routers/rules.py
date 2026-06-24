from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.company_rule import CompanyRule
from app.models.user import User
from app.schemas.company import CompanyRuleCreate, CompanyRuleResponse, CompanyRuleUpdate
from app.services.doc_processor import extract_text_from_pdf, extract_text_from_docx

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", response_model=list[CompanyRuleResponse])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all active company rules."""
    result = await db.execute(
        select(CompanyRule)
        .where(CompanyRule.is_active == True)  # noqa: E712
        .order_by(CompanyRule.created_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/",
    response_model=CompanyRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_rule(
    data: CompanyRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
    background_tasks: BackgroundTasks = None,
):
    """Add a company rule and embed it in vector store."""
    rule = CompanyRule(
        title=data.title,
        content=data.content,
        category=data.category,
        created_by=current_user.id,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)

    # Embed for RAG in background
    if background_tasks:
        try:
            from app.ai.embeddings import embed_document

            background_tasks.add_task(
                embed_document,
                text=(
                    f"Company Rule - {rule.category}: {rule.title}\n"
                    f"{rule.content}"
                ),
                metadata={
                    "type": "company_rule",
                    "title": rule.title,
                    "category": rule.category,
                    "id": str(rule.id),
                },
            )
        except Exception:
            pass

    return rule


@router.patch("/{rule_id}", response_model=CompanyRuleResponse)
async def update_rule(
    rule_id: uuid.UUID,
    data: CompanyRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
    background_tasks: BackgroundTasks = None,
):
    """Update a company rule and re-embed."""
    result = await db.execute(
        select(CompanyRule).where(CompanyRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found"
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)

    await db.flush()
    await db.refresh(rule)

    # Re-embed in background
    if background_tasks:
        try:
            from app.ai.embeddings import embed_document

            background_tasks.add_task(
                embed_document,
                text=(
                    f"Company Rule - {rule.category}: {rule.title}\n"
                    f"{rule.content}"
                ),
                metadata={
                    "type": "company_rule",
                    "title": rule.title,
                    "category": rule.category,
                    "id": str(rule.id),
                },
            )
        except Exception:
            pass

    return rule


@router.delete("/{rule_id}")
async def deactivate_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
):
    """Soft-delete a company rule."""
    result = await db.execute(
        select(CompanyRule).where(CompanyRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found"
        )

    rule.is_active = False
    await db.flush()
    try:
        from app.ai.embeddings import delete_embeddings
        delete_embeddings(str(rule_id))
    except Exception:
        pass
    return {"message": f"Rule '{rule.title}' deactivated"}


@router.post(
    "/upload-doc",
    response_model=CompanyRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_rule_doc(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
    background_tasks: BackgroundTasks = None,
):
    """Upload a .docx or .pdf file, parse it, and create a company rule."""
    if not file.filename or not (file.filename.endswith(".docx") or file.filename.endswith(".pdf")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .docx and .pdf files are supported",
        )

    content = await file.read()
    if file.filename.endswith(".pdf"):
        text = extract_text_from_pdf(content)
    else:
        text = extract_text_from_docx(content)

    # Ask LLM to determine title and category
    from langchain_core.messages import SystemMessage, HumanMessage
    from app.ai.agent import get_llm
    
    llm = await get_llm(temperature=0.1)
    prompt = (
        "Identify a suitable title and category for this company policy document text. "
        "Categories must be one of: 'leave', 'conduct', 'benefits', 'general'. "
        "Respond ONLY with a valid JSON object like:\n"
        "{\"title\": \"string\", \"category\": \"string\"}\n\n"
        f"Text snippet:\n{text[:1000]}"
    )
    
    try:
        res = await llm.ainvoke([SystemMessage(content="You parse text metadata to JSON."), HumanMessage(content=prompt)])
        from app.ai.agent import clean_content
        cleaned = clean_content(res.content).strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("\n", 1)[0]
        if cleaned.startswith("json"):
            cleaned = cleaned.split("json", 1)[1].strip()
        meta = json.loads(cleaned)
        title = meta.get("title", file.filename.rsplit(".", 1)[0])
        category = meta.get("category", "general")
    except Exception:
        title = file.filename.rsplit(".", 1)[0]
        category = "general"

    rule = CompanyRule(
        title=title,
        content=text,
        category=category,
        created_by=current_user.id,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)

    # Embed for RAG in background
    if background_tasks:
        try:
            from app.ai.embeddings import embed_document
            background_tasks.add_task(
                embed_document,
                text=f"Company Rule - {rule.category}: {rule.title}\n{rule.content}",
                metadata={
                    "type": "company_rule",
                    "title": rule.title,
                    "category": rule.category,
                    "source": file.filename,
                    "id": str(rule.id),
                },
            )
        except Exception:
            pass

    return rule

