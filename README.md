# Ping API

A simple FastAPI service with a `/ping` endpoint that returns the current datetime in the user's timezone.

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

## API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
