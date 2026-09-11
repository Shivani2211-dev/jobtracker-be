# Job Tracker — API

FastAPI backend for an AI-assisted job application tracker: save jobs and
applications, track status and follow-up dates, and get a resume-fit analysis
for a job description.

Frontend: [jobtracker-fe](https://github.com/Shivani2211-dev/jobtracker-fe)

## Stack

FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL (SQLite for local development) ·
JWT auth with bcrypt password hashing · optional OpenAI analysis with a
deterministic keyword fallback.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # then edit SECRET_KEY
alembic upgrade head            # builds the schema - the app does not create tables itself
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

Optional demo account: set `DEMO_PASSWORD` in `.env` and run
`python -m scripts.seed_demo`. It creates `demo@example.com` with sample data and
resets that data every time it runs.

## Tests

```bash
pytest
alembic upgrade head && alembic check   # migrations build the schema and match the models
```

CI runs both on every push.

## Honest resume tailor

`POST /analyze/tailor` turns a job description into resume bullets without
inventing experience. Every bullet points at a real line of the saved resume,
and a deterministic check rejects any bullet that names a technology the resume
never mentions or uses a number its source line doesn't contain. Rejected
bullets come back with the reason, and technologies the job wants but the resume
lacks are listed as gaps - never written into a bullet.

With `OPENAI_API_KEY` set, a model proposes rewritten bullets. Without it, the
extractive mode ranks the resume's own lines for the job and rewrites nothing.

```bash
python -m evals.tailor_eval
```

The eval runs the configured proposer and a deliberately fabricating one over
`evals/tailor_cases.json`, and fails if any unsupported claim reaches an
accepted bullet. It can't catch everything: a rewrite that inflates a verb
("helped" to "led") without adding a technology or a number still passes.

## Configuration

| Variable | Purpose |
| --- | --- |
| `ENVIRONMENT` | `development` or `production`. Production refuses to start with the default `SECRET_KEY` or a SQLite database. |
| `SECRET_KEY` | Signs login tokens. Use a long random value. |
| `DATABASE_URL` | Postgres in production. `postgres://` URLs from hosting providers are accepted as-is. |
| `FRONTEND_ORIGIN` | Allowed browser origin(s) for CORS, comma-separated. |
| `OPENAI_API_KEY` | Optional. Without it, analysis uses the local keyword fallback. |
| `DEMO_PASSWORD` | Optional. Enables the shared demo account. |

## Deploy (Render)

`render.yaml` defines the API and a Postgres database. In Render, choose
**New → Blueprint**, select this repository, then set `FRONTEND_ORIGIN` (the
deployed frontend URL) and, if you want the demo account, `DEMO_PASSWORD`.
`SECRET_KEY` is generated for you. Each start runs `alembic upgrade head`, then
the demo seed, then the server.

Free Render services sleep after 15 minutes idle and take about a minute to wake,
and free Postgres databases expire after 30 days.

## Security notes

- Every query is scoped to the signed-in user; requests for another user's jobs
  or applications return 404.
- Resume uploads are plain text only, limited to 1 MB.
- Login tokens are stored by the frontend in `localStorage`, which is simple but
  readable by any script running on the page.
