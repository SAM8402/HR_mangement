"""Company role management routes.

Provides endpoints for creating, updating, listing, and deleting
job roles, including document upload and LLM-assisted parsing.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.company_role import CompanyRole
from app.models.user import User
from app.schemas.company import (
    CompanyRoleCreate,
    CompanyRoleResponse,
    CompanyRoleUpdate,
)
from app.services.doc_parser import parse_docx
from app.services.doc_processor import extract_text_from_pdf, parse_role_text_with_llm

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.post(
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
    """Upload a .docx or .pdf file, parse it, and create a company role."""
    if not file.filename or not (
        file.filename.endswith(".docx") or file.filename.endswith(".pdf")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .docx and .pdf files are supported",
        )

    content = await file.read()
    if file.filename.endswith(".pdf"):
        raw_text = extract_text_from_pdf(content)
        parsed = await parse_role_text_with_llm(raw_text)
    else:
        parsed = parse_docx(content)

    role_id = uuid.uuid4()
    # Embed document for RAG in background
    if background_tasks:
        try:
            from app.ai.embeddings import embed_document

            background_tasks.add_task(
                embed_document,
                text=(
                    f"Role: {parsed['title']}\n"
                    f"Description: {parsed['description']}\n"
                    f"Responsibilities: {parsed['responsibilities']}\n"
                    f"Skills: {', '.join(parsed['skills'])}"
                ),
                metadata={
                    "type": "company_role",
                    "title": parsed["title"],
                    "source": file.filename,
                    "id": str(role_id),
                },
            )
        except Exception:
            pass  # Non-critical: log but don't fail

    role = CompanyRole(
        id=role_id,
        title=parsed["title"],
        description=parsed["description"],
        responsibilities=parsed["responsibilities"],
        required_skills=parsed["skills"],
        created_by=current_user.id,
    )
    db.add(role)
    await db.flush()
    await db.refresh(role)
    return role


@router.get("", response_model=list[CompanyRoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all company roles."""
    result = await db.execute(
        select(CompanyRole).order_by(CompanyRole.created_at.desc())
    )
    roles = list(result.scalars().all())
    logger.info("Roles list fetched (%d roles)", len(roles))
    return roles


@router.post(
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
    """Manually add a company role."""
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

    # Embed for RAG in background
    if background_tasks:
        try:
            from app.ai.embeddings import embed_document

            background_tasks.add_task(
                embed_document,
                text=(
                    f"Role: {role.title}\n"
                    f"Description: {role.description}\n"
                    f"Responsibilities: {role.responsibilities}\n"
                    f"Skills: {', '.join(role.required_skills)}"
                ),
                metadata={
                    "type": "company_role",
                    "title": role.title,
                    "id": str(role.id),
                },
            )
        except Exception:
            pass

    return role


@router.patch("/{role_id}", response_model=CompanyRoleResponse)
async def update_role(
    role_id: uuid.UUID,
    data: CompanyRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
    background_tasks: BackgroundTasks = None,
):
    """Update a company role."""
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

    # Re-embed in background
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
                    "id": str(role.id),
                },
            )
        except Exception:
            pass

    return role


@router.delete("/{role_id}")
async def delete_role(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager", "hr")),
):
    """Delete a company role."""
    result = await db.execute(select(CompanyRole).where(CompanyRole.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )

    await db.delete(role)
    await db.flush()
    try:
        from app.ai.embeddings import delete_embeddings

        delete_embeddings(str(role_id))
    except Exception:
        pass
    logger.info("Role %s deleted by user %s", role_id, current_user.id)
    return {"message": f"Role '{role.title}' deleted"}
