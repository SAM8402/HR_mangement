"""Document upload and management routes.

Provides endpoints for uploading, listing, retrieving, and deleting
role and rule documents (.docx / .pdf) with automatic parsing and
LLM-based metadata extraction.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

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
from app.schemas.company import CompanyRoleResponse, CompanyRuleResponse
from app.services.doc_parser import parse_docx
from app.services.doc_processor import (
    extract_text_from_docx,
    extract_text_from_pdf,
    parse_role_text_with_llm,
)

router = APIRouter(prefix="/api/docs", tags=["docs"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DOCS_DIR = PROJECT_ROOT / "Docs"
ROLES_DIR = DOCS_DIR / "Company Roles"
RULES_DIR = DOCS_DIR / "Company Rules"


def _ensure_dirs():
    ROLES_DIR.mkdir(parents=True, exist_ok=True)
    RULES_DIR.mkdir(parents=True, exist_ok=True)


# ── Role Documents ────────────────────────────────────────────────────────────


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
    return files


@router.get("/roles/{filename}", response_class=FileResponse)
async def get_role_doc(filename: str, current_user: User = Depends(get_current_user)):
    filepath = ROLES_DIR / filename
    if not filepath.exists() or filepath.suffix not in (".docx", ".pdf"):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(filepath))


@router.post("/roles/upload")
async def upload_role_doc(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
    background_tasks: BackgroundTasks = None,
):
    _ensure_dirs()
    if not file.filename or not (
        file.filename.endswith(".docx") or file.filename.endswith(".pdf")
    ):
        raise HTTPException(
            status_code=400, detail="Only .docx and .pdf files are supported"
        )

    content = await file.read()
    filepath = ROLES_DIR / file.filename
    filepath.write_bytes(content)

    try:
        if file.filename.endswith(".pdf"):
            raw_text = extract_text_from_pdf(content)
            parsed = await parse_role_text_with_llm(raw_text)
        else:
            parsed = parse_docx(content)

        role = CompanyRole(
            id=uuid.uuid4(),
            title=parsed.get("title", file.filename.rsplit(".", 1)[0]),
            description=parsed.get("description", ""),
            responsibilities=parsed.get("responsibilities", ""),
            required_skills=parsed.get("skills", []),
            created_by=current_user.id,
        )
        db.add(role)
        await db.flush()
        await db.refresh(role)

        if background_tasks:
            try:
                from app.ai.embeddings import embed_document

                background_tasks.add_task(
                    embed_document,
                    text=f"Role: {role.title}\nDescription: {role.description}\nResponsibilities: {role.responsibilities}\nSkills: {', '.join(role.required_skills)}",
                    metadata={
                        "type": "company_role",
                        "title": role.title,
                        "source": file.filename,
                        "id": str(role.id),
                    },
                )
            except Exception:
                pass

        return {
            "message": "Role document uploaded",
            "file": file.filename,
            "role": CompanyRoleResponse.model_validate(role),
        }
    except Exception as e:
        filepath.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to parse document: {str(e)}"
        )


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


# ── Rule Documents ────────────────────────────────────────────────────────────


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
    return files


@router.get("/rules/{filename}", response_class=FileResponse)
async def get_rule_doc(filename: str, current_user: User = Depends(get_current_user)):
    filepath = RULES_DIR / filename
    if not filepath.exists() or filepath.suffix not in (".docx", ".pdf"):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(filepath))


@router.post("/rules/upload")
async def upload_rule_doc(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
    background_tasks: BackgroundTasks = None,
):
    _ensure_dirs()
    if not file.filename or not (
        file.filename.endswith(".docx") or file.filename.endswith(".pdf")
    ):
        raise HTTPException(
            status_code=400, detail="Only .docx and .pdf files are supported"
        )

    content = await file.read()
    filepath = RULES_DIR / file.filename
    filepath.write_bytes(content)

    try:
        if file.filename.endswith(".pdf"):
            text = extract_text_from_pdf(content)
        else:
            text = extract_text_from_docx(content)

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

        return {
            "message": "Rule document uploaded",
            "file": file.filename,
            "rule": CompanyRuleResponse.model_validate(rule),
        }
    except Exception as e:
        filepath.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to parse document: {str(e)}"
        )


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
