# Ping API

A simple FastAPI service with a `/ping` endpoint that returns the current datetime in the user's timezone.

## What It Does

- **Endpoint**: `GET /ping`
- **Response**: HTTP 200 with `{"message": "Pong @ {datetime}"}`
- **Timezone**: Accepts `X-Timezone` header (IANA format like `America/New_York`)
- **Default**: UTC if no timezone header provided
- **Validation**: Returns HTTP 400 with helpful error for invalid timezones

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

Server runs at http://localhost:8000

## Usage

```bash
# Default (UTC)
curl http://localhost:8000/ping

# With timezone
curl -H "X-Timezone: America/New_York" http://localhost:8000/ping
curl -H "X-Timezone: Europe/London" http://localhost:8000/ping
curl -H "X-Timezone: Asia/Tokyo" http://localhost:8000/ping
```

## Response

```json
{
  "message": "Pong @ 2024-01-15 14:30:45 EST"
}
```

## Run Tests

```bash
pip install pytest httpx
pytest -v
```

## API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Development Rules Followed

This project was created by Claude Code following these principles:

### Code Quality
- **Type hints everywhere**: All function parameters and return types are annotated
- **Pydantic models**: Used `PingResponse` model for structured, validated responses
- **Explicit error handling**: Invalid timezones return HTTP 400 with actionable error messages
- **No magic strings**: Used FastAPI's `status` constants instead of raw integers

### Security
- **Input validation**: Timezone header is validated before use
- **Safe error messages**: Error responses don't leak internal details, just helpful guidance
- **No hardcoded secrets**: No credentials or sensitive data in code

### API Design
- **RESTful conventions**: GET for read-only operation, proper HTTP status codes
- **Self-documenting**: OpenAPI docs auto-generated with descriptions
- **Header-based timezone**: Clean separation of concerns (data vs metadata)

### Python Best Practices
- **Standard library first**: Used `zoneinfo` (Python 3.9+) instead of third-party `pytz`
- **Modern Python**: `Annotated` types, f-strings, type hints
- **Minimal dependencies**: Only FastAPI, Pydantic, Uvicorn

### Project Structure
- **Simple and flat**: Single `main.py` for a single-endpoint API (no over-engineering)
- **Clear requirements**: Pinned minimum versions for reproducibility
- **Comprehensive .gitignore**: Covers Python, venvs, IDEs, testing artifacts

### Git Workflow
- **Conventional commits**: `feat:` prefix with descriptive message
- **Atomic commits**: Each commit represents a complete, working state
- **Co-authorship**: Proper attribution for AI-assisted code

---

## Time to Create

**Total: 3 minutes 6 seconds**

| Step | Description |
|------|-------------|
| Initial setup | Project structure, FastAPI app, /ping endpoint |
| Documentation | README with rules and explanations |
| Repository | Created public repo at palpito-hunch/ping-api |
| Testing | 20 tests covering happy paths and edge cases |
| Final push | All changes committed and pushed |

*Generated entirely by Claude Code (claude-opus-4-5-20251101)*
