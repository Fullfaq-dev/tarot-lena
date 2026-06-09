from fastapi import APIRouter, Header, HTTPException, Request

from app.core.config import get_settings
from app.services.media.service import MediaJobService

router = APIRouter(prefix="/callbacks/kie", tags=["kie-callbacks"])


@router.post("")
async def kie_callback(
    request: Request,
    x_kie_signature: str | None = Header(default=None),
) -> dict[str, str]:
    settings = get_settings()
    if settings.kie_callback_secret and x_kie_signature not in {None, settings.kie_callback_secret}:
        raise HTTPException(status_code=401, detail="Invalid callback signature")

    payload = await request.json()
    await MediaJobService().handle_callback(payload)
    return {"status": "accepted"}
