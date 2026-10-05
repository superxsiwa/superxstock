from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_admin_user
from app.models.all_models import SystemConfig
from app.schemas import ConfigUpdate

router = APIRouter(
    prefix="/api/config",
    tags=["Configuration"],
    dependencies=[Depends(get_admin_user)],
)


@router.get("", response_model=dict[str, str])
def get_config(db: Session = Depends(get_db)):
    return {setting.key: setting.value for setting in db.query(SystemConfig).all()}


@router.put("")
def update_config(config: ConfigUpdate, db: Session = Depends(get_db)):
    setting = db.query(SystemConfig).filter(SystemConfig.key == config.key).first()
    if setting is None:
        raise HTTPException(status_code=404, detail="Configuration key not found.")

    setting.value = str(config.value)
    db.commit()
    db.refresh(setting)
    return {"key": setting.key, "value": config.value}