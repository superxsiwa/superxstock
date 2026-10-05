from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.line_messaging import (
    LineMessagingError,
    decrypt_channel_access_token,
    encrypt_channel_access_token,
    send_line_message,
)
from app.models.all_models import User, UserNotificationSettings
from app.schemas import LineNotificationUpdate

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("/settings")
def get_notification_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = db.query(UserNotificationSettings).filter_by(user_id=current_user.id).first()
    return {
        "line_user_id": settings.line_user_id if settings else "",
        "configured": settings is not None,
    }


@router.put("/settings")
def update_notification_settings(
    update: LineNotificationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = db.query(UserNotificationSettings).filter_by(user_id=current_user.id).first()
    if settings is None and update.channel_access_token is None:
        raise HTTPException(status_code=422, detail="Channel access token is required.")

    if settings is None:
        settings = UserNotificationSettings(
            user_id=current_user.id,
            line_user_id=update.line_user_id,
            encrypted_channel_access_token=encrypt_channel_access_token(update.channel_access_token),
        )
        db.add(settings)
    else:
        settings.line_user_id = update.line_user_id
        if update.channel_access_token is not None:
            settings.encrypted_channel_access_token = encrypt_channel_access_token(update.channel_access_token)

    db.commit()
    return {"line_user_id": settings.line_user_id, "configured": True}


@router.delete("/settings")
def delete_notification_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = db.query(UserNotificationSettings).filter_by(user_id=current_user.id).first()
    if settings is not None:
        db.delete(settings)
        db.commit()
    return {"ok": True}


@router.post("/test")
def test_notification(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = db.query(UserNotificationSettings).filter_by(user_id=current_user.id).first()
    if settings is None:
        raise HTTPException(status_code=400, detail="Save LINE notification settings first.")

    try:
        token = decrypt_channel_access_token(settings.encrypted_channel_access_token)
        send_line_message(token, settings.line_user_id, "SuperX Stock test notification.")
    except LineMessagingError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"ok": True}