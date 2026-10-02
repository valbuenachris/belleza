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
]