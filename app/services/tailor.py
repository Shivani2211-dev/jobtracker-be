"""Tailor resume bullets to a job description without inventing experience.

Every bullet has to point at a real line of the resume, and each one passes a
deterministic check before it is shown. The check rejects the two ways generated
resumes most often lie: naming a technology the resume never mentions, and
quoting a number that the source line doesn't contain.

With an OpenAI key, a model proposes rewritten bullets. Without one, the
"extractive" mode ranks the resume's own lines for the job and rewrites nothing.
Both go through the same check, so nothing unsupported reaches the user.

What it can't catch: a rewrite that inflates a verb ("helped" -> "led") without
adding a technology or a number still passes. evals/tailor_eval.py measures what
the check does catch.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable

from openai import AsyncOpenAI

from app.core.config import settings
from app.schemas.schemas import RejectedBullet, TailoredBullet, TailorResult

# Proposes candidate bullets as [{"text": ..., "line": <1-based resume line>}].
Proposer = Callable[[str, list[str], int], Awaitable[list[dict]]]

# Technologies the checker recognises, canonical and lowercase. Everyday words
# that double as tech names are left out on purpose ("go", "express", "spring",
# "rest"), so "the rest of the team" is never mistaken for a claim.
TECH_TERMS = {
    # languages
    "python", "java", "javascript", "typescript", "kotlin", "swift", "rust", "golang", "ruby", "php",
    "scala", "c++", "c#", "sql", "bash", "html", "css", "sass",
    # frontend
    "react", "next.js", "angular", "vue", "svelte", "redux", "zustand", "tailwind", "material ui", "mui",
    "bootstrap", "jquery", "webpack", "vite",
    # backend
    "node.js", "express.js", "fastapi", "django", "flask", "spring boot", "ruby on rails", ".net",
    "graphql", "rest api", "grpc", "celery", "kafka", "rabbitmq", "websockets",
    # data
    "postgresql", "mysql", "mongodb", "redis", "sqlite", "dynamodb", "elasticsearch", "snowflake",
    "sqlalchemy", "alembic", "hibernate", "prisma", "pandas", "numpy", "pyspark",
    # cloud and ops
    "aws", "azure", "gcp", "ec2", "s3", "aws lambda", "ecs", "eks", "rds", "cloudformation", "terraform",
    "docker", "kubernetes", "jenkins", "github actions", "gitlab ci", "circleci", "nginx", "linux",
    "vercel", "heroku", "cloudwatch", "datadog", "prometheus", "grafana",
    # auth and security
    "oauth", "oidc", "jwt", "saml", "okta", "cognito", "rbac",
    # testing
    "pytest", "jest", "cypress", "playwright", "selenium", "junit", "mockito",
    # ai
    "pytorch", "tensorflow", "scikit-learn", "langchain", "llm", "openai",
}

ALIASES = {
    "reactjs": "react", "react.js": "react",
    "nextjs": "next.js",
    "nodejs": "node.js",
    "expressjs": "express.js",
    "vuejs": "vue", "vue.js": "vue",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "js": "javascript", "ts": "typescript",
    "k8s": "kubernetes",
    "springboot": "spring boot",
    "rails": "ruby on rails",
    "tailwindcss": "tailwind",
    "material-ui": "material ui",
    "rest apis": "rest api", "restful": "rest api", "restful apis": "rest api",
    "amazon web services": "aws", "google cloud": "gcp",
    "asp.net": ".net",
    "sklearn": "scikit-learn",
    "html5": "html", "css3": "css",
    "oauth2": "oauth",
    "llms": "llm",
}

# Words too common in job ads and resumes to say anything about relevance.
_STOP = {
    "and", "the", "for", "with", "you", "are", "that", "this", "from", "will", "have", "our", "your", "who",
    "what", "able", "about", "experience", "years", "year", "team", "teams", "work", "working", "role",
    "job", "skills", "strong", "ability", "including", "using", "use", "used", "must", "plus", "preferred",
    "required", "requirements", "responsibilities", "knowledge", "understanding", "such", "other",
    "across", "into", "within", "their", "they", "them", "more", "well", "also", "new", "etc", "not",
    "all", "any", "can", "may", "per", "via", "based", "engineer", "engineering", "developer", "looking",
    "join", "help", "we're", "you'll", "including", "ideal", "candidate", "company",
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def _term_pattern(term: str) -> re.Pattern[str]:
    # Not preceded by a letter, digit or dot (so "js" in "react.js" doesn't
    # count) and not followed by one (so "java" in "javascript" doesn't).
    return re.compile(r"(?<![a-z0-9.])" + re.escape(term) + r"(?![a-z0-9+#])")


_TERM_PATTERNS = [(_term_pattern(term), term) for term in TECH_TERMS] + [
    (_term_pattern(alias), canonical) for alias, canonical in ALIASES.items()
]
_NUMBER = re.compile(r"(?<![a-z0-9.])\d+(?:[.,]\d+)*")
_WORD = re.compile(r"[a-z][a-z0-9+#.'-]{2,}")
_BULLET = re.compile(r"^\s*(?:[-*•·▪‣◦–—>]+|\(?\d+[.)])\s*")
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def tech_terms(text: str) -> set[str]:
    """The known technologies a piece of text mentions, as canonical names."""
    norm = _norm(text)
    return {canonical for pattern, canonical in _TERM_PATTERNS if pattern.search(norm)}


def numbers(text: str) -> set[str]:
    """Numbers in the text, commas removed: '1,200 users, 40%' -> {'1200', '40'}.

    Digits inside names such as S3 or EC2 are ignored."""
    return {match.group().replace(",", "") for match in _NUMBER.finditer(_norm(text))}


def _content_words(text: str) -> set[str]:
    return {word.strip(".-'") for word in _WORD.findall(_norm(text))} - _STOP


def resume_lines(resume_text: str) -> list[str]:
    """The resume split into lines a bullet can cite.

    Bullet markers are stripped, long paragraphs are split into sentences, and
    anything shorter than four words (names, headings) is dropped."""
    lines: list[str] = []
    for raw in resume_text.splitlines():
        text = re.sub(r"\s+", " ", _BULLET.sub("", raw)).strip()
        parts = _SENTENCE.split(text) if len(text) > 280 else [text]
        lines.extend(part for part in parts if len(part.split()) >= 4)
    return lines


def check_bullet(text: str, evidence: str | None, resume_terms: set[str]) -> str | None:
    """Why a bullet can't be shown, or None when the resume supports it."""
    if not evidence:
        return "It doesn't point to a line of your resume."
    invented = sorted(tech_terms(text) - resume_terms)
    if invented:
        return f"Mentions {', '.join(invented)}, which your resume doesn't."
    new_numbers = sorted(numbers(text) - numbers(evidence))
    if new_numbers:
        return f"Uses the number {', '.join(new_numbers)}, which its source line doesn't contain."
    return None


def _extractive(job_description: str, lines: list[str], max_bullets: int) -> list[dict]:
    """The resume's own lines, most relevant to the job first. Rewrites nothing."""
    job_words = _content_words(job_description)
    job_terms = tech_terms(job_description)
    scored = []
    for index, line in enumerate(lines, 1):
        score = len(_content_words(line) & job_words) + 2 * len(tech_terms(line) & job_terms)
        if score:
            scored.append((score, index, line))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [{"text": line, "line": index} for _, index, line in scored[:max_bullets]]


_SYSTEM_PROMPT = (
    "You tailor resume bullets to a job description. Each bullet must rewrite exactly one of the "
    "numbered resume lines, and you must give that line's number. Use only facts the line states: "
    "do not add tools, technologies, numbers, results, titles or employers that it doesn't mention. "
    "Emphasise what in the line matters for this job. If the job asks for something the resume "
    "doesn't show, leave it out - never claim it."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "bullets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "line": {"type": "integer"}},
                "required": ["text", "line"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["bullets"],
    "additionalProperties": False,
}


async def _openai_proposer(job_description: str, lines: list[str], max_bullets: int) -> list[dict]:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    numbered = "\n".join(f"{index}. {line}" for index, line in enumerate(lines, 1))
    response = await asyncio.wait_for(
        client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "tailored_bullets", "schema": _SCHEMA, "strict": True},
            },
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"JOB DESCRIPTION:\n{job_description}\n\nRESUME LINES:\n{numbered}\n\n"
                    f"Write up to {max_bullets} bullets.",
                },
            ],
        ),
        timeout=30.0,
    )
    return json.loads(response.choices[0].message.content)["bullets"]


async def tailor_resume(
    job_description: str,
    resume_text: str,
    max_bullets: int = 6,
    proposer: Proposer | None = None,
) -> TailorResult:
    lines = resume_lines(resume_text)
    resume_terms = tech_terms(resume_text)
    missing = sorted(tech_terms(job_description) - resume_terms)

    if proposer is None and settings.openai_api_key:
        proposer = _openai_proposer

    source = "extractive"
    proposals: list[dict] | None = None
    if proposer is not None and lines:
        try:
            proposals = await proposer(job_description, lines, max_bullets)
            source = "ai"
        except Exception as exc:  # the model is outside our control: fall back, don't fail
            print(f"tailor: proposer failed, using extractive mode: {type(exc).__name__}: {str(exc)[:200]}")
            proposals = None
    if proposals is None:
        proposals = _extractive(job_description, lines, max_bullets)
        source = "extractive"

    job_words = _content_words(job_description) | tech_terms(job_description)
    bullets: list[TailoredBullet] = []
    rejected: list[RejectedBullet] = []
    seen: set[str] = set()
    generated = 0
    for item in proposals:
        text = re.sub(r"\s+", " ", str(item.get("text", ""))).strip() if isinstance(item, dict) else ""
        if not text or text.lower() in seen:
            continue
        seen.add(text.lower())
        generated += 1

        line = item.get("line")
        evidence = lines[line - 1] if isinstance(line, int) and 1 <= line <= len(lines) else None
        reason = check_bullet(text, evidence, resume_terms)
        if reason:
            rejected.append(RejectedBullet(text=text, reason=reason))
        elif len(bullets) < max_bullets:
            matched = sorted((_content_words(text) | tech_terms(text)) & job_words)
            bullets.append(TailoredBullet(text=text, evidence=evidence, matched_keywords=matched[:8]))

    return TailorResult(
        source=source,
        bullets=bullets,
        rejected=rejected,
        missing_keywords=missing,
        generated=generated,
        unsupported_rate=round(len(rejected) / generated, 3) if generated else 0.0,
    )
