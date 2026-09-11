"""How often would tailoring put an unsupported claim on a resume?

Run from the backend directory:  python -m evals.tailor_eval

Two passes over evals/tailor_cases.json:

  configured   The real proposer: OpenAI when OPENAI_API_KEY is set, otherwise
               the extractive mode. Reports how many proposed bullets the checker
               rejected, and fails if a technology the resume lacks still reached
               an accepted bullet, or if a gap the job asks for went unreported.

  adversarial  A proposer that fabricates on purpose. For every resume line it
               offers the line itself, the line plus a technology the job wants
               but the resume lacks, and the line plus an invented number. Every
               fabrication must be rejected and every faithful line accepted.
               This measures the checker, independent of any model.

Exits 1 if anything unsupported gets through, so CI can run it.
"""

import asyncio
import json
import sys
from pathlib import Path

from app.core.config import settings
from app.services.tailor import resume_lines, tailor_resume, tech_terms

CASES = Path(__file__).with_name("tailor_cases.json")
FAKE_NUMBER = "37%"


def _adversarial_proposals(lines: list[str], term: str) -> list[tuple[str, dict]]:
    proposals = []
    for index, line in enumerate(lines, 1):
        base = line.rstrip(".")
        proposals.append(("faithful", {"text": line, "line": index}))
        proposals.append(("tool", {"text": f"{base} using {term}.", "line": index}))
        proposals.append(("number", {"text": f"{base}, improving results by {FAKE_NUMBER}.", "line": index}))
    return proposals


def _configured(case: dict) -> tuple[list[str], list[str]]:
    result = asyncio.run(tailor_resume(case["job_description"], case["resume"]))
    leaked = sorted({term for bullet in result.bullets for term in tech_terms(bullet.text)} & set(case["forbidden"]))
    expected = set(case["expected_missing"])
    found = expected & set(result.missing_keywords)
    row = [
        case["name"],
        str(result.generated),
        str(len(result.bullets)),
        str(len(result.rejected)),
        f"{result.unsupported_rate:.0%}",
        ", ".join(leaked) or "none",
        f"{len(found)}/{len(expected)}",
    ]
    failures = []
    if leaked:
        failures.append(f"{case['name']}: accepted bullet claims {', '.join(leaked)}")
    if found != expected:
        failures.append(f"{case['name']}: gaps not reported: {', '.join(sorted(expected - found))}")
    return row, failures


def _adversarial(case: dict) -> tuple[list[str], list[str], int, int]:
    lines = resume_lines(case["resume"])
    labelled = _adversarial_proposals(lines, case["forbidden"][0])

    async def propose(*_):
        return [proposal for _, proposal in labelled]

    result = asyncio.run(
        tailor_resume(case["job_description"], case["resume"], max_bullets=len(labelled), proposer=propose)
    )
    rejected = {item.text for item in result.rejected}
    fabricated = [proposal["text"] for kind, proposal in labelled if kind != "faithful"]
    faithful = [proposal["text"] for kind, proposal in labelled if kind == "faithful"]
    caught = sum(text in rejected for text in fabricated)
    wrongly = sum(text in rejected for text in faithful)
    row = [case["name"], str(len(fabricated)), str(caught), str(len(faithful)), str(wrongly)]
    failures = []
    if caught < len(fabricated):
        failures.append(f"{case['name']}: {len(fabricated) - caught} fabricated bullets were accepted")
    if wrongly:
        failures.append(f"{case['name']}: {wrongly} faithful lines were rejected")
    return row, failures, caught, len(fabricated)


def _table(header: list[str], rows: list[list[str]]) -> str:
    widths = [max(len(cell) for cell in column) for column in zip(header, *rows)]
    lines = ["  ".join(cell.ljust(width) for cell, width in zip(header, widths))]
    lines.append("  ".join("-" * width for width in widths))
    lines += ["  ".join(cell.ljust(width) for cell, width in zip(row, widths)) for row in rows]
    return "\n".join(lines)


def main() -> int:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    mode = "openai" if settings.openai_api_key else "extractive (set OPENAI_API_KEY to evaluate the model)"
    failures: list[str] = []

    print(f"Tailor eval - configured proposer: {mode}\n")
    rows = []
    for case in cases:
        row, case_failures = _configured(case)
        rows.append(row)
        failures += case_failures
    print(_table(["case", "proposed", "accepted", "rejected", "unsupported", "leaked", "gaps found"], rows))

    print("\nAdversarial proposer - measures the checker itself\n")
    rows, caught_total, fabricated_total = [], 0, 0
    for case in cases:
        row, case_failures, caught, fabricated = _adversarial(case)
        rows.append(row)
        failures += case_failures
        caught_total += caught
        fabricated_total += fabricated
    print(_table(["case", "fabricated", "caught", "faithful", "wrongly rejected"], rows))

    print()
    if failures:
        print("RESULT: FAIL")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"RESULT: PASS - no unsupported claim reached an accepted bullet; "
          f"the checker caught {caught_total}/{fabricated_total} fabrications.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
