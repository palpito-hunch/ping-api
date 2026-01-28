from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import User, create_tables, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    create_tables()
    yield


app = FastAPI(title="Ping API", version="2.0.0", lifespan=lifespan)


class PingResponse(BaseModel):
    message: str
    views: int
    updated_at: str


@app.get(
    "/ping",
    response_model=PingResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check with timestamp and view tracking",
    description="Returns 'Pong' with the current datetime in the user's timezone. Tracks views per user.",
)
def ping(
    db: Annotated[Session, Depends(get_db)],
    x_user_id: Annotated[str, Header(description="Unique user identifier")],
    x_timezone: Annotated[str, Header(description="IANA timezone (e.g., America/New_York)")] = "UTC",
) -> PingResponse:
    """Return Pong with current datetime and update user view count atomically."""
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-User-Id header is required and cannot be empty.",
        )

    x_user_id = x_user_id.strip()

    if not x_timezone:
        x_timezone = "UTC"

    try:
        tz = ZoneInfo(x_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timezone: '{x_timezone}'. Use IANA format (e.g., America/New_York, Europe/London).",
        )

    # Atomic upsert: INSERT or UPDATE with increment at database level
    # This prevents race conditions by doing the increment in SQL, not Python
    now = datetime.now(timezone.utc)

    db.execute(
        text("""
            INSERT INTO users (id, views, created_at, updated_at)
            VALUES (:user_id, 1, :now, :now)
            ON CONFLICT(id) DO UPDATE SET
                views = users.views + 1,
                updated_at = :now
        """),
        {"user_id": x_user_id, "now": now},
    )
    db.commit()

    # Fetch the updated user to return current state
    user = db.query(User).filter(User.id == x_user_id).first()

    current_time = datetime.now(tz)
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S %Z")

    # Format updated_at in the user's timezone
    updated_at_local = user.updated_at.replace(tzinfo=timezone.utc).astimezone(tz)
    formatted_updated_at = updated_at_local.strftime("%Y-%m-%d %H:%M:%S %Z")

    return PingResponse(
        message=f"Pong @ {formatted_time}",
        views=user.views,
        updated_at=formatted_updated_at,
    )
