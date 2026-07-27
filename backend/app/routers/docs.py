"""Document upload, role management, and rule management routes.

Consolidated router for all document-related operations:
  - /api/docs — file listing, serving, and deletion from disk
  - /api/roles — CRUD for company job roles (including upload + parse)
  - /api/rules — CRUD for company policy rules (including upload + parse)
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.company_role import CompanyRole
from app.models.company_rule import CompanyRule
from app.models.user import User
from app.schemas.company import (
    CompanyRoleCreate,
    CompanyRoleResponse,
    CompanyRoleUpdate,
    CompanyRuleCreate,
    CompanyRuleResponse,
    CompanyRuleUpdate,
)
from app.services.doc_processor import (
    extract_text_from_docx,
    extract_text_from_pdf,
    parse_docx,
    parse_role_text_with_llm,
)

router = APIRouter(prefix="/api/docs", tags=["docs"])
roles_router = APIRouter(prefix="/api/roles", tags=["roles"])
rules_router = APIRouter(prefix="/api/rules", tags=["rules"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DOCS_DIR = PROJECT_ROOT / "Docs"
ROLES_DIR = DOCS_DIR / "Company Roles"
RULES_DIR = DOCS_DIR / "Company Rules"


def _ensure_dirs():
    ROLES_DIR.mkdir(parents=True, exist_ok=True)
    RULES_DIR.mkdir(parents=True, exist_ok=True)


# ── Helper: embed document / delete embedding ─────────────────────────────────


def _embed_role(background_tasks: BackgroundTasks | None, role: CompanyRole, filename: str = ""):
    if background_tasks:
        try:
            from app.ai.embeddings import embed_document

            background_tasks.add_task(
                embed_document,
                text=(
                    f"Role: {role.title}\n"
                    f"Description: {role.description}\n"
                    f"Responsibilities: {role.responsibilities}\n"
                    f"Skills: {', '.join(role.required_skills) if role.required_skills else ''}"
                ),
                metadata={
                    "type": "company_role",
                    "title": role.title,
                    "source": filename or "",
                    "id": str(role.id),
                },
            )
        except Exception:
            pass


def _embed_rule(background_tasks: BackgroundTasks | None, rule: CompanyRule, filename: str = ""):
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
                    "source": filename or "",
                    "id": str(rule.id),
                },
            )
        except Exception:
            pass


def _delete_embedding(entity_id: str):
    try:
        from app.ai.embeddings import delete_embeddings

        delete_embeddings(entity_id)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  /api/docs  —  file listing, serving, deletion
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/roles")
async def list_role_docs(current_user: User = Depends(get_current_user)):
    _ensure_dirs()
    files = []
    for f in sorted(ROLES_DIR.iterdir(), key=lambda p: p.name):
        if f.suffix in (".docx", ".pdf"):
            files.append(
                {
                    "name": f.name,
                    "size": f.stat().st_size,
                    "modified": f.stat().st_mtime,
                    "type": "role",
                }
            )
    logger.info("Role document list fetched by user %s", current_user.id)
    return files


@router.get("/roles/{filename}", response_class=FileResponse)
async def get_role_doc(filename: str, current_user: User = Depends(get_current_user)):
    filepath = ROLES_DIR / filename
    if not filepath.exists() or filepath.suffix not in (".docx", ".pdf"):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(filepath))


@router.get("/rules")
async def list_rule_docs(current_user: User = Depends(get_current_user)):
    _ensure_dirs()
    files = []
    for f in sorted(RULES_DIR.iterdir(), key=lambda p: p.name):
        if f.suffix in (".docx", ".pdf"):
            files.append(
                {
                    "name": f.name,
                    "size": f.stat().st_size,
                    "modified": f.stat().st_mtime,
                    "type": "rule",
                }
            )
    logger.info("Rule document list fetched by user %s", current_user.id)
    return files


@router.get("/rules/{filename}", response_class=FileResponse)
async def get_rule_doc(filename: str, current_user: User = Depends(get_current_user)):
    filepath = RULES_DIR / filename
    if not filepath.exists() or filepath.suffix not in (".docx", ".pdf"):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(filepath))


@router.delete("/roles/{filename}")
async def delete_role_doc(
    filename: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
):
    filepath = ROLES_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    filepath.unlink()

    result = await db.execute(
        select(CompanyRole).where(
            CompanyRole.title.ilike(f"%{filename.rsplit('.', 1)[0]}%")
        )
    )
    role = result.scalar_one_or_none()
    if role:
        await db.delete(role)
        await db.flush()

    return {"message": f"Role document '{filename}' deleted"}


@router.delete("/rules/{filename}")
async def delete_rule_doc(
    filename: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
):
    filepath = RULES_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    filepath.unlink()

    result = await db.execute(
        select(CompanyRule).where(
            CompanyRule.title.ilike(f"%{filename.rsplit('.', 1)[0]}%")
        )
    )
    rule = result.scalar_one_or_none()
    if rule:
        rule.is_active = False
        await db.flush()

    return {"message": f"Rule document '{filename}' deleted"}


@router.post("/roles/upload")
async def upload_role_doc_backward(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
    background_tasks: BackgroundTasks = None,
):
    return await upload_role_doc(file, db, current_user, background_tasks)


@router.post("/rules/upload")
async def upload_rule_doc_backward(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
    background_tasks: BackgroundTasks = None,
):
    return await upload_rule_doc(file, db, current_user, background_tasks)


# ═══════════════════════════════════════════════════════════════════════════════
#  /api/roles  —  company role CRUD (including document upload)
# ═══════════════════════════════════════════════════════════════════════════════


@roles_router.post(
    "/upload-doc",
    response_model=CompanyRoleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_role_doc(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
    background_tasks: BackgroundTasks = None,
):
    if not file.filename or not (
        file.filename.endswith(".docx") or file.filename.endswith(".pdf")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .docx and .pdf files are supported",
        )

    content = await file.read()

    _ensure_dirs()
    filepath = ROLES_DIR / file.filename
    filepath.write_bytes(content)

    if file.filename.endswith(".pdf"):
        raw_text = extract_text_from_pdf(content)
        parsed = await parse_role_text_with_llm(raw_text)
    else:
        parsed = parse_docx(content)

    role = CompanyRole(
        id=uuid.uuid4(),
        title=parsed["title"],
        description=parsed["description"],
        responsibilities=parsed["responsibilities"],
        required_skills=parsed["skills"],
        created_by=current_user.id,
    )
    db.add(role)
    await db.flush()
    await db.refresh(role)

    _embed_role(background_tasks, role, file.filename)
    logger.info("Role document %s uploaded and processed", file.filename)
    return role


@roles_router.get("", response_model=list[CompanyRoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CompanyRole).order_by(CompanyRole.created_at.desc())
    )
    roles = list(result.scalars().all())
    logger.info("Roles list fetched (%d roles)", len(roles))
    return roles


@roles_router.post(
    "",
    response_model=CompanyRoleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_role(
    data: CompanyRoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
    background_tasks: BackgroundTasks = None,
):
    role = CompanyRole(
        title=data.title,
        description=data.description,
        responsibilities=data.responsibilities,
        required_skills=data.required_skills,
        created_by=current_user.id,
    )
    db.add(role)
    await db.flush()
    await db.refresh(role)
    logger.info("Role %s created by user %s", role.id, current_user.id)

    _embed_role(background_tasks, role)
    return role


@roles_router.patch("/{role_id}", response_model=CompanyRoleResponse)
async def update_role(
    role_id: uuid.UUID,
    data: CompanyRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
    background_tasks: BackgroundTasks = None,
):
    result = await db.execute(select(CompanyRole).where(CompanyRole.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(role, field, value)

    await db.flush()
    await db.refresh(role)
    logger.info("Role %s updated by user %s", role_id, current_user.id)

    _embed_role(background_tasks, role)
    return role


@roles_router.delete("/{role_id}")
async def delete_role(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
):
    result = await db.execute(select(CompanyRole).where(CompanyRole.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )

    await db.delete(role)
    await db.flush()
    _delete_embedding(str(role_id))
    logger.info("Role %s deleted by user %s", role_id, current_user.id)
    return {"message": f"Role '{role.title}' deleted"}


# ═══════════════════════════════════════════════════════════════════════════════
#  /api/rules  —  company rule CRUD (including document upload)
# ═══════════════════════════════════════════════════════════════════════════════


@rules_router.get("", response_model=list[CompanyRuleResponse])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CompanyRule)
        .where(CompanyRule.is_active == True)  # noqa: E712
        .order_by(CompanyRule.created_at.desc())
    )
    rules = list(result.scalars().all())
    logger.info("Company rules list fetched (%d rules)", len(rules))
    return rules


@rules_router.post(
    "",
    response_model=CompanyRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_rule(
    data: CompanyRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
    background_tasks: BackgroundTasks = None,
):
    rule = CompanyRule(
        title=data.title,
        content=data.content,
        category=data.category,
        created_by=current_user.id,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    logger.info("Rule %s created by user %s", rule.id, current_user.id)

    _embed_rule(background_tasks, rule)
    return rule


@rules_router.patch("/{rule_id}", response_model=CompanyRuleResponse)
async def update_rule(
    rule_id: uuid.UUID,
    data: CompanyRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
    background_tasks: BackgroundTasks = None,
):
    result = await db.execute(select(CompanyRule).where(CompanyRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found"
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)

    await db.flush()
    await db.refresh(rule)
    logger.info("Rule %s updated by user %s", rule_id, current_user.id)

    _embed_rule(background_tasks, rule)
    return rule


@rules_router.delete("/{rule_id}")
async def deactivate_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
):
    result = await db.execute(select(CompanyRule).where(CompanyRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found"
        )

    rule.is_active = False
    await db.flush()
    _delete_embedding(str(rule_id))
    logger.info("Rule %s deactivated by user %s", rule_id, current_user.id)
    return {"message": f"Rule '{rule.title}' deactivated"}


@rules_router.post(
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
    if not file.filename or not (
        file.filename.endswith(".docx") or file.filename.endswith(".pdf")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .docx and .pdf files are supported",
        )

    content = await file.read()

    _ensure_dirs()
    filepath = RULES_DIR / file.filename
    filepath.write_bytes(content)

    text = (
        extract_text_from_pdf(content)
        if file.filename.endswith(".pdf")
        else extract_text_from_docx(content)
    )

    from langchain_core.messages import HumanMessage, SystemMessage

    from app.ai.agent import clean_content, get_llm

    llm = await get_llm(temperature=0.1)
    prompt = (
        "Identify a suitable title and category for this company policy document text. "
        "Categories must be one of: 'leave', 'conduct', 'benefits', 'general'. "
        "Respond ONLY with a valid JSON object like:\n"
        '{"title": "string", "category": "string"}\n\n'
        f"Text snippet:\n{text[:1000]}"
    )

    try:
        res = await llm.ainvoke(
            [
                SystemMessage(content="You parse text metadata to JSON."),
                HumanMessage(content=prompt),
            ]
        )
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

    _embed_rule(background_tasks, rule, file.filename)
    logger.info("Rule document %s uploaded and processed", file.filename)
    return rule