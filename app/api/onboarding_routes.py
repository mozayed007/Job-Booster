"""FastAPI router for the onboarding agent — personal context collection."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from app.middleware.auth_middleware import get_current_user_dependency
from app.models.db_models import User
from app.services.db_service import get_db_session

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


class ChatTurnRequest(BaseModel):
    """Single chat turn for the onboarding interview."""

    user_message: str
    history: list[dict[str, str]] = Field(default_factory=list)


class ChatTurnResponse(BaseModel):
    """Response for a chat turn."""

    reply: str
    profile_ready: bool = False
    history: list[dict[str, str]] = Field(default_factory=list)


class PersonalContextResponse(BaseModel):
    """Saved personal context for the current user."""

    success: bool = True
    personal_context: dict[str, Any] | None = None


class SaveProfileRequest(BaseModel):
    """Request to persist a finalized personal profile."""

    profile: dict[str, Any]


def _serialize_profile(profile: Any) -> dict[str, Any]:
    """Coerce a PersonalProfileOutput (or dict) into a plain dict for JSON storage."""
    if hasattr(profile, "model_dump"):
        result = profile.model_dump()
        return result if isinstance(result, dict) else {}
    if isinstance(profile, dict):
        return profile
    return {}


@router.get("/profile", response_model=PersonalContextResponse)
async def get_personal_context(
    current_user: User = Depends(get_current_user_dependency),
):
    """Return the saved personal context for the authenticated user."""
    profile = current_user.profile_json or {}
    context = profile.get("personal_context")
    return PersonalContextResponse(
        success=True,
        personal_context=context if isinstance(context, dict) else None,
    )


@router.put("/profile", response_model=PersonalContextResponse)
async def save_personal_context(
    request: SaveProfileRequest,
    current_user: User = Depends(get_current_user_dependency),
):
    """Persist finalized personal context under user.profile_json['personal_context'].

    This is the storage seam for the onboarding agent. Personal context is
    STRICTLY isolated — only the gap-recommendation agent reads it; resume and
    cover-letter agents never access it to avoid fabricating resume bullets.
    """
    from app.agents.onboarding import PersonalProfileOutput

    # Validate the incoming profile against the Pydantic model so we never
    # persist malformed personal context.
    try:
        validated = PersonalProfileOutput.model_validate(request.profile)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid personal context: {e}",
        )

    db = get_db_session()
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        profile = user.profile_json or {}
        profile["personal_context"] = validated.model_dump()
        user.profile_json = profile
        db.commit()
        db.refresh(user)
        logger.info(f"Saved personal context for user id={current_user.id}")
        return PersonalContextResponse(
            success=True,
            personal_context=profile["personal_context"],
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Save personal context error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@router.post("/chat", response_model=ChatTurnResponse)
async def onboarding_chat(
    request: ChatTurnRequest,
    current_user: User = Depends(get_current_user_dependency),
):
    """Single chat turn for the onboarding interview.

    The client maintains the conversation history and sends it with each turn.
    When the agent emits [PROFILE_READY], the client should call finalize or
    the user can click Save to persist manually.
    """
    from app.agents.onboarding import PROFILE_READY_MARKER, chat_turn

    if not request.user_message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_message is required",
        )

    try:
        reply = await chat_turn(request.user_message, request.history)
    except Exception as e:
        logger.error(f"Onboarding chat error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    ready = PROFILE_READY_MARKER in reply
    # Strip the marker from the reply shown to the user.
    clean_reply = reply.replace(PROFILE_READY_MARKER, "").strip()
    # Build the updated history to return so the client can echo it back.
    updated_history = list(request.history) + [
        {"role": "user", "content": request.user_message},
        {"role": "assistant", "content": clean_reply},
    ]
    return ChatTurnResponse(
        reply=clean_reply,
        profile_ready=ready,
        history=updated_history,
    )


@router.post("/finalize", response_model=PersonalContextResponse)
async def finalize_onboarding(
    request: ChatTurnRequest,
    current_user: User = Depends(get_current_user_dependency),
):
    """Finalize an onboarding conversation into a structured profile and persist it.

    Accepts the full conversation history and runs the structured-output agent
    to produce a PersonalProfileOutput, then saves it to profile_json.
    """
    from app.agents.onboarding import finalize_onboarding as _finalize

    if not request.history:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="history is required to finalize",
        )

    try:
        profile = await _finalize(request.history)
    except Exception as e:
        logger.error(f"Onboarding finalize error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    # Persist the finalized profile.
    payload = _serialize_profile(profile)
    db = get_db_session()
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        profile_json = user.profile_json or {}
        profile_json["personal_context"] = payload
        user.profile_json = profile_json
        db.commit()
        logger.info(f"Finalized onboarding for user id={current_user.id}")
        return PersonalContextResponse(success=True, personal_context=payload)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Persist finalized profile error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()
