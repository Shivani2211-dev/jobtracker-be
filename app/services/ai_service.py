import asyncio
import json
import re

from openai import AsyncOpenAI, OpenAIError
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.schemas import AIAnalysisResult, CoverLetterResult, InterviewQuestionResult, ResumeParseResult


STOPWORDS = {"and", "the", "for", "with", "you", "are", "that", "this", "from", "will", "have", "our"}


def _keywords(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z+#.]{2,}", text.lower())
    return {word for word in words if word not in STOPWORDS}


def _fallback_analysis(job_description: str, resume_text: str | None) -> AIAnalysisResult:
    resume = resume_text or ""
    jd_keywords = _keywords(job_description)
    resume_keywords = _keywords(resume)
    matched = sorted(jd_keywords & resume_keywords)
    missing = sorted(jd_keywords - resume_keywords)
    score = 35 if not jd_keywords else min(95, max(20, round((len(matched) / len(jd_keywords)) * 100)))

    strengths = [f"Your resume already mentions {kw}." for kw in matched[:5]] or [
        "You have a resume baseline ready to tailor for this role."
    ]
    gaps = [f"Add evidence for {kw}." for kw in missing[:5]] or [
        "The resume covers most of the visible job keywords."
    ]
    suggested = [
        "Rewrite the summary to mirror the job title and top responsibilities.",
        "Add 2-3 quantified bullets that prove impact in the required skills.",
        "Move the most relevant projects or experience above less relevant sections.",
    ]

    return AIAnalysisResult(
        fit_score=score,
        strengths=strengths,
        gaps=gaps,
        suggested_edits=suggested,
        summary=f"Resume match is {score}%. Focus first on the missing keywords and quantified proof.",
    )


async def analyze_resume_fit(job_description: str, resume_text: str | None) -> AIAnalysisResult:
    if not settings.openai_api_key:
        return _fallback_analysis(job_description, resume_text)

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        schema = AIAnalysisResult.model_json_schema()

        prompt = f"""Analyze how well this resume matches the job description.

Return practical feedback as JSON. Score fit from 0-100.

JOB DESCRIPTION:
{job_description}

RESUME:
{resume_text or "No resume provided"}
"""

        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert career coach. Analyze resumes against job descriptions. Return detailed, personalized feedback in JSON format.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "resume_fit_analysis",
                        "schema": schema,
                        "strict": True,
                    }
                },
                temperature=0.7,
            ),
            timeout=30.0
        )
        
        content = response.choices[0].message.content
        result = AIAnalysisResult.model_validate(json.loads(content))
        return result
        
    except asyncio.TimeoutError:
        print(f"OpenAI API timeout")
        return _fallback_analysis(job_description, resume_text)
    except (OpenAIError, ValidationError, json.JSONDecodeError) as e:
        print(f"OpenAI API error: {type(e).__name__}: {str(e)[:200]}")
        return _fallback_analysis(job_description, resume_text)
    except Exception as e:
        print(f"Unexpected error in analyze_resume_fit: {type(e).__name__}: {str(e)[:200]}")
        return _fallback_analysis(job_description, resume_text)


def parse_resume_text(resume_text: str) -> ResumeParseResult:
    keywords = sorted(_keywords(resume_text))
    skills = [word for word in keywords if word in {
        "python", "fastapi", "react", "next", "typescript", "sql", "postgresql", "aws", "docker",
        "analytics", "machine", "learning", "javascript", "api", "leadership", "finance", "saas",
    }]
    summary = " ".join(resume_text.strip().split()[:35])
    return ResumeParseResult(
        resume_text=resume_text,
        summary=summary or "Resume text saved. Add more detail for stronger analysis.",
        skills=skills[:12],
    )


async def generate_cover_letter(job_description: str, company: str, title: str, resume_text: str | None) -> CoverLetterResult:
    analysis = await analyze_resume_fit(job_description, resume_text)
    strengths = " ".join(analysis.strengths[:3])
    return CoverLetterResult(
        cover_letter=(
            f"Dear {company} Hiring Team,\n\n"
            f"I am excited to apply for the {title} role. My background aligns with the needs of this position, "
            f"especially around the strengths highlighted in my resume: {strengths}\n\n"
            f"I would welcome the chance to bring a practical, impact-focused approach to {company} and contribute "
            f"quickly to the team.\n\n"
            "Sincerely,\n"
            "Your Name"
        )
    )


async def generate_interview_questions(job_description: str, resume_text: str | None) -> InterviewQuestionResult:
    keywords = sorted(_keywords(job_description))[:8]
    questions = [f"Tell me about your experience with {keyword}." for keyword in keywords[:5]]
    questions.extend([
        "Walk me through a project where you had to learn a new domain quickly.",
        "How would you prioritize your first 30 days in this role?",
        "What accomplishment on your resume best matches this job description?",
    ])
    return InterviewQuestionResult(questions=questions[:8])