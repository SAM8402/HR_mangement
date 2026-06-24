from __future__ import annotations

import re

from docx import Document


def parse_docx(file_content: bytes) -> dict:
    """Parse a .docx file and extract structured role information."""
    doc = Document(file_content)  # type: ignore[arg-type]

    title = ""
    description = ""
    responsibilities = ""
    skills: list[str] = []

    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    if paragraphs:
        title = paragraphs[0]

    current_section = "description"
    section_buffers: dict[str, list[str]] = {
        "description": [],
        "responsibilities": [],
        "skills": [],
    }

    skill_keywords = {"skills", "required skills", "requirements", "qualifications"}
    resp_keywords = {"responsibilities", "duties", "key responsibilities", "what you'll do"}

    for para in paragraphs[1:]:
        lower = para.lower().rstrip(":")
        if lower in skill_keywords:
            current_section = "skills"
            continue
        if lower in resp_keywords:
            current_section = "responsibilities"
            continue

        # Detect bullet points for skills
        if current_section == "skills" and re.match(r"^[\-\*\•]", para):
            skill_text = re.sub(r"^[\-\*\•\s]+", "", para).strip()
            if skill_text:
                skills.append(skill_text)
        elif current_section == "responsibilities":
            section_buffers["responsibilities"].append(para)
        else:
            section_buffers["description"].append(para)

    description = " ".join(section_buffers["description"])
    responsibilities = " ".join(section_buffers["responsibilities"])

    # Fallback: if no explicit sections found, put everything in description
    if not description and not responsibilities:
        description = " ".join(paragraphs[1:])

    return {
        "title": title or "Untitled Role",
        "description": description,
        "responsibilities": responsibilities,
        "skills": skills,
    }
