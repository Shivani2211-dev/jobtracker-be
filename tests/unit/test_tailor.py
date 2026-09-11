import asyncio

from app.services.tailor import check_bullet, numbers, resume_lines, tailor_resume, tech_terms

RESUME = """Alex Rivera
- Built 12+ reusable React components with TypeScript, cutting delivery time by 15%.
- Designed REST APIs in FastAPI backed by Postgres.
• Wrote pytest suites and ran them in GitHub Actions.
Skills: Python, React, FastAPI
"""

JOB = "We need a React and TypeScript engineer with Kubernetes and AWS experience."


def test_resume_lines_strip_bullets_and_skip_short_lines():
    lines = resume_lines(RESUME)
    assert lines[0].startswith("Built 12+ reusable React components")
    assert "Alex Rivera" not in lines  # too short to be evidence
    assert all(not line.startswith(("-", "•")) for line in lines)


def test_tech_terms_understand_aliases_and_word_boundaries():
    assert tech_terms("React.js, Postgres and k8s") == {"react", "postgresql", "kubernetes"}
    assert "java" not in tech_terms("JavaScript only")
    assert tech_terms("PostgreSQL and MySQL") == {"postgresql", "mysql"}
    assert tech_terms("for the rest of the team") == set()


def test_numbers_ignore_digits_inside_names():
    assert numbers("Moved files to S3 and EC2, 40% faster, 1,200 users") == {"40", "1200"}


def test_check_accepts_a_faithful_rewrite():
    evidence = "Built 12+ reusable React components with TypeScript, cutting delivery time by 15%."
    bullet = "Cut delivery time 15% by building 12+ reusable React components"
    assert check_bullet(bullet, evidence, tech_terms(RESUME)) is None


def test_check_rejects_an_invented_technology():
    evidence = "Designed REST APIs in FastAPI backed by Postgres."
    reason = check_bullet("Designed FastAPI services deployed on Kubernetes", evidence, tech_terms(RESUME))
    assert reason and "kubernetes" in reason


def test_check_rejects_an_invented_number():
    evidence = "Designed REST APIs in FastAPI backed by Postgres."
    reason = check_bullet("Designed FastAPI APIs serving 10,000 users", evidence, tech_terms(RESUME))
    assert reason and "10000" in reason


def test_check_rejects_a_bullet_without_a_source_line():
    assert check_bullet("Led the platform team", None, tech_terms(RESUME))


def test_extractive_mode_only_returns_real_resume_lines():
    result = asyncio.run(tailor_resume(JOB, RESUME))
    lines = resume_lines(RESUME)
    assert result.source == "extractive"
    assert result.bullets
    assert all(bullet.text in lines and bullet.evidence == bullet.text for bullet in result.bullets)
    assert result.rejected == []
    assert set(result.missing_keywords) == {"kubernetes", "aws"}


def test_fabricated_proposals_are_rejected_and_counted():
    async def fabricating(job, lines, max_bullets):
        return [
            {"text": lines[0], "line": 1},  # faithful
            {"text": "Deployed React apps to Kubernetes on AWS", "line": 1},  # invented tools
            {"text": "Designed REST APIs in FastAPI, cutting latency 40%", "line": 2},  # invented number
            {"text": "Mentored five engineers", "line": 99},  # no such line
        ]

    result = asyncio.run(tailor_resume(JOB, RESUME, proposer=fabricating))
    assert result.source == "ai"
    assert [bullet.text for bullet in result.bullets] == [resume_lines(RESUME)[0]]
    assert len(result.rejected) == 3
    assert result.generated == 4
    assert result.unsupported_rate == 0.75


def test_a_failing_model_falls_back_to_extractive():
    async def broken(job, lines, max_bullets):
        raise ValueError("model returned garbage")

    result = asyncio.run(tailor_resume(JOB, RESUME, proposer=broken))
    assert result.source == "extractive"
    assert result.bullets
