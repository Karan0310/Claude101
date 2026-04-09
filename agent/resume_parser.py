"""
Resume Parser - Uses Claude to extract structured data from resumes.
Supports PDF and DOCX formats.
"""
import io
import json
from pathlib import Path
from typing import Union

import anthropic
import pdfplumber
from docx import Document

from config.settings import settings
from models.schemas import ResumeProfile


def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX bytes."""
    doc = Document(io.BytesIO(file_content))
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    return "\n\n".join(paragraphs)


def extract_text(file_content: bytes, filename: str) -> str:
    """Extract text from resume file based on extension."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(file_content)
    elif suffix in (".docx", ".doc"):
        return extract_text_from_docx(file_content)
    elif suffix == ".txt":
        return file_content.decode("utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use PDF, DOCX, or TXT.")


PARSE_SYSTEM_PROMPT = """You are an expert resume analyzer. Extract structured information from resumes accurately and completely.
Always respond with valid JSON matching the exact schema provided. Do not include markdown code blocks."""

PARSE_USER_PROMPT = """Analyze this resume and extract structured information. Return a JSON object with exactly these fields:

{{
  "name": "full name or null",
  "email": "email or null",
  "phone": "phone or null",
  "location": "city, state/country or null",
  "summary": "professional summary in 2-3 sentences or null",
  "skills": ["list", "of", "technical", "and", "soft", "skills"],
  "experience_years": <total years of experience as a number or null>,
  "job_titles": ["list of previous job titles held"],
  "companies": ["list of companies worked at"],
  "education": ["Degree - Institution - Year"],
  "certifications": ["list of certifications"],
  "languages": ["programming or spoken languages"],
  "search_keywords": ["10-15 keywords for job searching based on this resume"],
  "preferred_roles": ["5-8 most suitable job roles for this person based on their background"]
}}

Resume Text:
{resume_text}"""


async def parse_resume(file_content: bytes, filename: str) -> ResumeProfile:
    """Parse a resume file and return a structured ResumeProfile using Claude."""
    raw_text = extract_text(file_content, filename)

    if not raw_text.strip():
        raise ValueError("Could not extract text from resume. Please ensure the file is not image-based or empty.")

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    message = await client.messages.create(
        model=settings.claude_model,
        max_tokens=2048,
        system=PARSE_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": PARSE_USER_PROMPT.format(resume_text=raw_text[:12000]),
            }
        ],
    )

    response_text = message.content[0].text.strip()

    # Strip markdown code fences if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    parsed = json.loads(response_text)

    return ResumeProfile(
        raw_text=raw_text,
        name=parsed.get("name"),
        email=parsed.get("email"),
        phone=parsed.get("phone"),
        location=parsed.get("location"),
        summary=parsed.get("summary"),
        skills=parsed.get("skills", []),
        experience_years=parsed.get("experience_years"),
        job_titles=parsed.get("job_titles", []),
        companies=parsed.get("companies", []),
        education=parsed.get("education", []),
        certifications=parsed.get("certifications", []),
        languages=parsed.get("languages", []),
        search_keywords=parsed.get("search_keywords", []),
        preferred_roles=parsed.get("preferred_roles", []),
    )
