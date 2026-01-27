from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel

app = FastAPI(title="Ping API", version="1.0.0")


class PingResponse(BaseModel):
    message: str


@app.get(
    "/ping",
    response_model=PingResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check with timestamp",
    description="Returns 'Pong' with the current datetime in the user's timezone.",
)
def ping(
    x_timezone: Annotated[str, Header(description="IANA timezone (e.g., America/New_York)")] = "UTC",
) -> PingResponse:
    """Return Pong with current datetime in the user's timezone."""
    if not x_timezone:
        x_timezone = "UTC"

    try:
        tz = ZoneInfo(x_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timezone: '{x_timezone}'. Use IANA format (e.g., America/New_York, Europe/London).",
        )

    current_time = datetime.now(tz)
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S %Z")

    return PingResponse(message=f"Pong @ {formatted_time}")
