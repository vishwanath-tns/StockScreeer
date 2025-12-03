"""Alert API endpoints."""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from ..auth import AuthUser, get_current_user
from ...core.enums import AlertType, AlertCondition, AlertStatus, AssetType, NotificationChannel, Priority
from ...services.alert_service import AlertService

router = APIRouter()


# ==================== Pydantic Models ====================

class AlertCreate(BaseModel):
    """Request model for creating an alert."""
    symbol: str = Field(..., min_length=1, max_length=50, description="Stock symbol (e.g., RELIANCE)")
    asset_type: AssetType = Field(..., description="Type of asset")
    alert_type: AlertType = Field(AlertType.PRICE, description="Type of alert")
    condition: AlertCondition = Field(..., description="Alert condition")
    target_value: float = Field(..., gt=0, description="Target value for condition")
    target_value_2: Optional[float] = Field(None, description="Second value for BETWEEN conditions")
    priority: Priority = Field(Priority.NORMAL, description="Alert priority")
    notification_channels: List[NotificationChannel] = Field(
        default=[NotificationChannel.DESKTOP],
        description="Notification channels"
    )
    webhook_url: Optional[str] = Field(None, description="Webhook URL for notifications")
    trigger_once: bool = Field(True, description="Trigger only once or repeatedly")
    cooldown_minutes: int = Field(60, ge=1, le=1440, description="Cooldown between repeated triggers")
    expires_at: Optional[datetime] = Field(None, description="Alert expiration time")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "RELIANCE",
                "asset_type": "nse_equity",
                "alert_type": "price",
                "condition": "price_above",
                "target_value": 2500.00,
                "priority": "normal",
                "notification_channels": ["desktop", "sound"],
                "trigger_once": True,
            }
        }


class AlertUpdate(BaseModel):
    """Request model for updating an alert."""
    target_value: Optional[float] = Field(None, gt=0)
    target_value_2: Optional[float] = None
    status: Optional[AlertStatus] = None
    priority: Optional[Priority] = None
    notification_channels: Optional[List[NotificationChannel]] = None
    webhook_url: Optional[str] = None
    trigger_once: Optional[bool] = None
    cooldown_minutes: Optional[int] = Field(None, ge=1, le=1440)
    expires_at: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=500)


class AlertResponse(BaseModel):
    """Response model for an alert."""
    id: str
    user_id: int
    symbol: str
    yahoo_symbol: str
    asset_type: str
    alert_type: str
    condition: str
    target_value: float
    target_value_2: Optional[float]
    status: str
    priority: str
    notification_channels: List[str]
    webhook_url: Optional[str]
    trigger_once: bool
    cooldown_minutes: int
    expires_at: Optional[datetime]
    source: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_triggered_at: Optional[datetime]
    trigger_count: int

    class Config:
        from_attributes = True


# ==================== Endpoints ====================

@router.post("/alerts", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate,
    user: AuthUser = Depends(get_current_user),
):
    """Create a new price alert."""
    service = AlertService()
    
    try:
        alert = service.create_alert(
            user_id=user.user_id,
            symbol=alert_data.symbol,
            asset_type=alert_data.asset_type,
            alert_type=alert_data.alert_type,
            condition=alert_data.condition,
            target_value=alert_data.target_value,
            target_value_2=alert_data.target_value_2,
            priority=alert_data.priority,
            notification_channels=alert_data.notification_channels,
            webhook_url=alert_data.webhook_url,
            trigger_once=alert_data.trigger_once,
            cooldown_minutes=alert_data.cooldown_minutes,
            expires_at=alert_data.expires_at,
            notes=alert_data.notes,
            source="api" if user.auth_type == "api_key" else "manual",
        )
        
        return AlertResponse(
            id=alert.id,
            user_id=alert.user_id,
            symbol=alert.symbol,
            yahoo_symbol=alert.yahoo_symbol,
            asset_type=alert.asset_type.value,
            alert_type=alert.alert_type.value,
            condition=alert.condition.value,
            target_value=alert.target_value,
            target_value_2=alert.target_value_2,
            status=alert.status.value,
            priority=alert.priority.value,
            notification_channels=[nc.value for nc in alert.notification_channels],
            webhook_url=alert.webhook_url,
            trigger_once=alert.trigger_once,
            cooldown_minutes=alert.cooldown_minutes,
            expires_at=alert.expires_at,
            source=alert.source,
            notes=alert.notes,
            created_at=alert.created_at,
            updated_at=alert.updated_at,
            last_triggered_at=alert.last_triggered_at,
            trigger_count=alert.trigger_count,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/alerts", response_model=List[AlertResponse])
async def list_alerts(
    user: AuthUser = Depends(get_current_user),
    status_filter: Optional[AlertStatus] = Query(None, alias="status"),
    asset_type: Optional[AssetType] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get all alerts for the current user."""
    service = AlertService()
    
    alerts = service.get_user_alerts(
        user_id=user.user_id,
        status=status_filter,
        asset_type=asset_type,
        limit=limit,
        offset=offset,
    )
    
    return [
        AlertResponse(
            id=a.id,
            user_id=a.user_id,
            symbol=a.symbol,
            yahoo_symbol=a.yahoo_symbol,
            asset_type=a.asset_type.value,
            alert_type=a.alert_type.value,
            condition=a.condition.value,
            target_value=a.target_value,
            target_value_2=a.target_value_2,
            status=a.status.value,
            priority=a.priority.value,
            notification_channels=[nc.value for nc in a.notification_channels],
            webhook_url=a.webhook_url,
            trigger_once=a.trigger_once,
            cooldown_minutes=a.cooldown_minutes,
            expires_at=a.expires_at,
            source=a.source,
            notes=a.notes,
            created_at=a.created_at,
            updated_at=a.updated_at,
            last_triggered_at=a.last_triggered_at,
            trigger_count=a.trigger_count,
        )
        for a in alerts
    ]


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    user: AuthUser = Depends(get_current_user),
):
    """Get a specific alert."""
    service = AlertService()
    
    alert = service.get_alert(alert_id, user.user_id)
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )
    
    return AlertResponse(
        id=alert.id,
        user_id=alert.user_id,
        symbol=alert.symbol,
        yahoo_symbol=alert.yahoo_symbol,
        asset_type=alert.asset_type.value,
        alert_type=alert.alert_type.value,
        condition=alert.condition.value,
        target_value=alert.target_value,
        target_value_2=alert.target_value_2,
        status=alert.status.value,
        priority=alert.priority.value,
        notification_channels=[nc.value for nc in alert.notification_channels],
        webhook_url=alert.webhook_url,
        trigger_once=alert.trigger_once,
        cooldown_minutes=alert.cooldown_minutes,
        expires_at=alert.expires_at,
        source=alert.source,
        notes=alert.notes,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
        last_triggered_at=alert.last_triggered_at,
        trigger_count=alert.trigger_count,
    )


@router.patch("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    alert_data: AlertUpdate,
    user: AuthUser = Depends(get_current_user),
):
    """Update an alert."""
    service = AlertService()
    
    # Build updates dict excluding None values
    updates = {k: v for k, v in alert_data.model_dump().items() if v is not None}
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )
    
    alert = service.update_alert(alert_id, user.user_id, **updates)
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )
    
    return AlertResponse(
        id=alert.id,
        user_id=alert.user_id,
        symbol=alert.symbol,
        yahoo_symbol=alert.yahoo_symbol,
        asset_type=alert.asset_type.value,
        alert_type=alert.alert_type.value,
        condition=alert.condition.value,
        target_value=alert.target_value,
        target_value_2=alert.target_value_2,
        status=alert.status.value,
        priority=alert.priority.value,
        notification_channels=[nc.value for nc in alert.notification_channels],
        webhook_url=alert.webhook_url,
        trigger_once=alert.trigger_once,
        cooldown_minutes=alert.cooldown_minutes,
        expires_at=alert.expires_at,
        source=alert.source,
        notes=alert.notes,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
        last_triggered_at=alert.last_triggered_at,
        trigger_count=alert.trigger_count,
    )


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: str,
    user: AuthUser = Depends(get_current_user),
):
    """Delete an alert."""
    service = AlertService()
    
    if not service.delete_alert(alert_id, user.user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )


@router.post("/alerts/{alert_id}/pause", response_model=AlertResponse)
async def pause_alert(
    alert_id: str,
    user: AuthUser = Depends(get_current_user),
):
    """Pause an alert."""
    service = AlertService()
    
    if not service.pause_alert(alert_id, user.user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )
    
    return await get_alert(alert_id, user)


@router.post("/alerts/{alert_id}/resume", response_model=AlertResponse)
async def resume_alert(
    alert_id: str,
    user: AuthUser = Depends(get_current_user),
):
    """Resume a paused alert."""
    service = AlertService()
    
    if not service.resume_alert(alert_id, user.user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )
    
    return await get_alert(alert_id, user)


@router.get("/alerts/history/all")
async def get_alert_history(
    user: AuthUser = Depends(get_current_user),
    alert_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    """Get alert trigger history."""
    service = AlertService()
    
    history = service.get_alert_history(
        user_id=user.user_id,
        alert_id=alert_id,
        limit=limit,
    )
    
    return history
