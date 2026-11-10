# backend/app/models/__init__.py
# Registro de todos los modelos del sistema
from .base import Base, TenantBaseModel
from .tenant import Tenant
from .user import User
from .patient import Patient
from .service import Service
from .appointment import Appointment
from .clinical_record import ClinicalRecord
from .pass_registration import PassRegistration
from .assistant import AssistantQuery
from .notification import Notification
from .whatsapp import WhatsAppSettings, WhatsAppConversation, WhatsAppMessage
from .appointment_item import AppointmentItem, AppointmentPayment
from .service_related import ServiceRelated

__all__ = [
    "Base",
    "TenantBaseModel",
    "Tenant",
    "User",
    "Patient",
    "Service",
    "Appointment",
    "ClinicalRecord",
    "PassRegistration",
    "AssistantQuery",
    "Notification",
    "WhatsAppSettings",
    "WhatsAppConversation",
    "WhatsAppMessage",
    "AppointmentItem",
    "AppointmentPayment",
    "ServiceRelated",
]