from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# WhatsApp Settings
# ============================================================

class WhatsAppSettingsResponse(BaseModel):
    instance_name: Optional[str] = None
    status: str = "close"
    connected_at: Optional[datetime] = None
    qr_code: Optional[str] = None
    agent_enabled: bool = False
    agent_name: str = "Asistente del SPA"
    agent_tone: str = "amable"
    notifications_enabled: bool = False
    webhook_registered: bool = False


class WhatsAppSettingsUpdate(BaseModel):
    agent_enabled: Optional[bool] = None
    agent_name: Optional[str] = Field(None, max_length=100)
    agent_tone: Optional[str] = Field(None, max_length=20)
    notifications_enabled: Optional[bool] = None


# ============================================================
# Instance management
# ============================================================

class WhatsAppConnectResponse(BaseModel):
    instance_name: str
    state: Optional[str] = None
    qr: Optional[str] = None


class WhatsAppStatusResponse(BaseModel):
    connected: bool
    state: Optional[str] = None
    instance_name: Optional[str] = None


# ============================================================
# Messages and Conversations
# ============================================================

class WhatsAppMessageResponse(BaseModel):
    id: str
    role: str
    content: Optional[str] = None
    created_at: datetime


class WhatsAppConversationResponse(BaseModel):
    id: str
    phone: str
    push_name: Optional[str] = None
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    status: str
    last_message_at: Optional[datetime] = None
    last_message_content: Optional[str] = None
    last_message_role: Optional[str] = None
    created_at: datetime


class WhatsAppConversationListResponse(BaseModel):
    conversations: list[WhatsAppConversationResponse]
    total: int


class WhatsAppMessageListResponse(BaseModel):
    messages: list[WhatsAppMessageResponse]
    total: int