# ============================================================
# backend/app/services/tenant_service.py - Lógica de negocio de Tenants
# CRUD y operaciones de tenants (SPAs)
# ============================================================

import logging
import re
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.tenant import Tenant
from ..models.user import User
from ..schemas.tenant import TenantCreate, TenantUpdate, TenantConfig
from ..utils.security import generate_uuid

logger = logging.getLogger(__name__)

# Límites por defecto según el plan del SPA. Se aplican al crear o al
# cambiar de plan si no se proporcionan límites explícitos.
PLAN_LIMITS: Dict[str, Dict[str, int]] = {
    "basic": {"limite_usuarios": 3, "limite_pacientes": 300},
    "professional": {"limite_usuarios": 10, "limite_pacientes": 1500},
    "enterprise": {"limite_usuarios": 50, "limite_pacientes": 10000},
}

# Precios mensuales por plan (para el cálculo del MRR estimado)
PLAN_PRECIOS: Dict[str, int] = {
    "basic": 29,
    "professional": 79,
    "enterprise": 199,
}


def resolve_plan_limits(
    plan: str,
    limite_usuarios: Optional[int] = None,
    limite_pacientes: Optional[int] = None,
    usuarios_explicit: bool = False,
    pacientes_explicit: bool = False,
) -> Dict[str, int]:
    """
    Resuelve los límites de un tenant según su plan.

    Usa los valores por defecto del plan solo cuando el campo NO fue
    proporcionado explícitamente por el caller.
    """
    defaults = PLAN_LIMITS.get(plan, {"limite_usuarios": 10, "limite_pacientes": 1000})
    return {
        "limite_usuarios": limite_usuarios if usuarios_explicit else defaults["limite_usuarios"],
        "limite_pacientes": limite_pacientes if pacientes_explicit else defaults["limite_pacientes"],
    }


def _build_unique_username(db: Session, tenant_id: str, email: str) -> str:
    """
    Deriva un username alfanumérico desde el email y garantiza que sea
    único dentro del tenant (sufijo numérico si colisiona).
    """
    base = re.sub(r"[^a-z0-9]", "", email.split("@")[0].lower())[:20]
    base = base or "admin"
    if len(base) < 3:
        base = base.ljust(3, "0")

    username = base
    suffix = 1
    while (
        db.query(User)
        .filter(User.tenant_id == tenant_id, User.username == username)
        .first()
    ):
        suf = str(suffix)
        username = f"{base[:20 - len(suf)]}{suf}"
        suffix += 1
    return username


# ============================================================
# Crear tenant
# ============================================================

def generate_subdomain(db: Session, nombre: str) -> str:
    """
    Genera un subdominio único y seguro a partir del nombre del SPA.

    El subdominio ya NO es obligatorio ni se usa para enrutamiento
    (login universal por email); solo se conserva como identificador
    secundario opcional, así que esta función garantiza un valor que
    respete el índice único de la columna si el usuario no proporcionó uno.
    """
    base = re.sub(r"[^a-z0-9]", "", (nombre or "").lower()) or "spa"
    base = base[:20]

    candidate = base
    suffix = 1
    while not validate_subdomain_available(db, candidate):
        suf = str(suffix)
        candidate = f"{base[: 20 - len(suf)]}{suf}"
        suffix += 1
    return candidate


def _normalize_subdomain(db: Session, provided: Optional[str], nombre: str) -> str:
    """
    Devuelve el subdominio final a usar: si no se proporcionó (o viene vacío),
    se auto-genera uno único; si el proporcionado ya está en uso, se auto-genera
    un alternativo en lugar de rechazar la operación.
    """
    sd = (provided or "").strip().lower()
    if not sd:
        return generate_subdomain(db, nombre)
    if not validate_subdomain_available(db, sd):
        logger.info(f"Subdominio '{sd}' en uso; auto-generando alternativo")
        return generate_subdomain(db, sd)
    return sd


def create_tenant(db: Session, tenant_data: TenantCreate) -> Tenant:
    """
    Crea un nuevo tenant.

    El subdominio ya no es obligatorio (login universal por email): si no se
    proporciona, se auto-genera un valor único.

    Si tenant_data.admin trae credenciales (flujo superadmin), se crea
    también el usuario administrador del tenant, vinculado vía tenant_id,
    en la misma transacción.

    Args:
        db: Sesión de base de datos
        tenant_data: Datos del tenant a crear (puede incluir 'admin')
        
    Returns:
        Tenant creado
        
    Raises:
        ValueError: Si el email del admin ya está en uso
    """
    subdominio = _normalize_subdomain(db, tenant_data.subdominio, tenant_data.nombre)

    if tenant_data.admin:
        existing_email = db.query(User).filter(
            User.email == tenant_data.admin.email.lower()
        ).first()
        if existing_email:
            raise ValueError(
                "Ya existe un usuario con este correo electrónico"
            )

    # Límites por defecto según el plan (si no se proporcionaron explícitamente)
    fields_set = tenant_data.model_fields_set
    plan_limits = resolve_plan_limits(
        tenant_data.plan,
        tenant_data.limite_usuarios,
        tenant_data.limite_pacientes,
        usuarios_explicit="limite_usuarios" in fields_set,
        pacientes_explicit="limite_pacientes" in fields_set,
    )

    tenant = Tenant(
        id=generate_uuid(),
        nombre=tenant_data.nombre,
        subdominio=subdominio,
        plan=tenant_data.plan,
        limite_usuarios=plan_limits["limite_usuarios"],
        limite_pacientes=plan_limits["limite_pacientes"],
        email=tenant_data.email,
        telefono=tenant_data.telefono,
        direccion=tenant_data.direccion,
        timezone=tenant_data.timezone,
        moneda=tenant_data.moneda,
        configuracion=TenantConfig().model_dump(),
        is_active=True,
    )
    db.add(tenant)
    db.flush()  # Para obtener el ID antes de crear el usuario admin

    # Crear usuario administrador del tenant (flujo superadmin)
    if tenant_data.admin:
        admin = tenant_data.admin
        admin_user = User(
            id=generate_uuid(),
            tenant_id=tenant.id,
            username=_build_unique_username(db, tenant.id, admin.email),
            email=admin.email.lower(),
            nombre=admin.nombre,
            apellido=admin.apellido,
            rol=admin.rol,
            email_verificado=False,
            is_active=True,
        )
        admin_user.set_password(admin.password)
        db.add(admin_user)
        logger.info(f"Admin creado para {tenant.nombre}: {admin_user.email}")

    db.commit()
    db.refresh(tenant)
    
    logger.info(f"Tenant creado: {tenant.nombre} ({tenant.id})")
    return tenant


# ============================================================
# Obtener tenant
# ============================================================

def get_tenant_by_id(db: Session, tenant_id: str) -> Optional[Tenant]:
    """
    Obtiene un tenant por su ID.
    """
    return db.query(Tenant).filter(
        Tenant.id == tenant_id,
        Tenant.deleted_at == None,
    ).first()


def get_tenant_by_subdomain(db: Session, subdomain: str) -> Optional[Tenant]:
    """
    Obtiene un tenant por su subdominio.
    """
    return db.query(Tenant).filter(
        Tenant.subdominio == subdomain.lower(),
        Tenant.deleted_at == None,
    ).first()


# ============================================================
# Listar tenants con paginación
# ============================================================

def list_tenants(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    plan: Optional[str] = None,
    activo: Optional[bool] = None,
    search: Optional[str] = None,
) -> List[Tenant]:
    """
    Lista tenants con paginación y filtros opcionales.
    
    Args:
        db: Sesión de base de datos
        skip: Número de registros a saltar
        limit: Máximo de registros a retornar
        plan: Filtrar por plan
        activo: Filtrar por estado activo
        search: Buscar por nombre o subdominio
        
    Returns:
        Lista de tenants
    """
    query = db.query(Tenant).filter(Tenant.deleted_at == None)
    
    if plan:
        query = query.filter(Tenant.plan == plan)
    
    if activo is not None:
        query = query.filter(Tenant.is_active == activo)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Tenant.nombre.ilike(search_pattern)) |
            (Tenant.subdominio.ilike(search_pattern))
        )
    
    return query.order_by(Tenant.fecha_creacion.desc()).offset(skip).limit(limit).all()


def count_tenants(
    db: Session,
    plan: Optional[str] = None,
    activo: Optional[bool] = None,
) -> int:
    """Cuenta el total de tenants con filtros opcionales."""
    query = db.query(func.count(Tenant.id)).filter(Tenant.deleted_at == None)
    
    if plan:
        query = query.filter(Tenant.plan == plan)
    if activo is not None:
        query = query.filter(Tenant.is_active == activo)
    
    return query.scalar() or 0


# ============================================================
# Actualizar tenant
# ============================================================

def update_tenant(db: Session, tenant_id: str, tenant_data: TenantUpdate) -> Optional[Tenant]:
    """
    Actualiza los datos de un tenant.
    
    Args:
        db: Sesión de base de datos
        tenant_id: ID del tenant a actualizar
        tenant_data: Datos a actualizar (solo campos no None)
        
    Returns:
        Tenant actualizado o None si no existe
    """
    tenant = get_tenant_by_id(db, tenant_id)
    if not tenant:
        return None
    
    # Actualizar solo los campos proporcionados
    update_data = tenant_data.model_dump(exclude_unset=True)

    # "activo" es una property de solo lectura en el modelo; el campo
    # real en la base de datos es "is_active".
    if "activo" in update_data:
        update_data["is_active"] = update_data.pop("activo")

    # Al cambiar de plan, aplicar los límites por defecto del nuevo plan
    # solo si el usuario no los proporcionó explícitamente.
    if "plan" in update_data:
        defaults = PLAN_LIMITS.get(update_data["plan"])
        if defaults:
            if "limite_usuarios" not in update_data:
                update_data["limite_usuarios"] = defaults["limite_usuarios"]
            if "limite_pacientes" not in update_data:
                update_data["limite_pacientes"] = defaults["limite_pacientes"]

    # Subdominio opcional: si viene vacío no se cambia; si entra en
    # conflicto con otro tenant se auto-genera un alternativo.
    if "subdominio" in update_data:
        sd = (update_data["subdominio"] or "").strip().lower()
        if not sd:
            update_data.pop("subdominio")
        else:
            conflicto = db.query(Tenant.id).filter(
                Tenant.subdominio == sd,
                Tenant.id != tenant_id,
                Tenant.deleted_at == None,
            ).first()
            update_data["subdominio"] = (
                generate_subdomain(db, sd) if conflicto else sd
            )

    for field, value in update_data.items():
        setattr(tenant, field, value)
    
    db.commit()
    db.refresh(tenant)
    
    logger.info(f"Tenant actualizado: {tenant.nombre} ({tenant.id})")
    return tenant


# ============================================================
# Eliminar tenant (soft delete)
# ============================================================

def delete_tenant(db: Session, tenant_id: str) -> bool:
    """
    Elimina un tenant de forma lógica (soft delete).
    
    Args:
        db: Sesión de base de datos
        tenant_id: ID del tenant a eliminar
        
    Returns:
        True si se eliminó correctamente, False si no existe
    """
    tenant = get_tenant_by_id(db, tenant_id)
    if not tenant:
        return False
    
    tenant.soft_delete()
    db.commit()
    
    logger.info(f"Tenant eliminado (soft delete): {tenant.nombre} ({tenant.id})")
    return True


# ============================================================
# Validación de subdominio
# ============================================================

def validate_subdomain_available(db: Session, subdomain: str) -> bool:
    """
    Verifica si un subdominio está disponible.
    
    Args:
        db: Sesión de base de datos
        subdomain: Subdominio a verificar
        
    Returns:
        True si está disponible, False si ya está en uso
    """
    existing = db.query(Tenant).filter(
        Tenant.subdominio == subdomain.lower(),
        Tenant.deleted_at == None,
    ).first()
    return existing is None


# ============================================================
# Estadísticas del tenant
# ============================================================

def get_tenant_stats(db: Session, tenant_id: str) -> Dict[str, Any]:
    """
    Obtiene estadísticas de un tenant.
    
    Args:
        db: Sesión de base de datos
        tenant_id: ID del tenant
        
    Returns:
        Diccionario con estadísticas
    """
    # Contar usuarios activos
    total_usuarios = db.query(func.count(User.id)).filter(
        User.tenant_id == tenant_id,
        User.is_active == True,
        User.deleted_at == None,
    ).scalar() or 0
    
    # Contar usuarios por rol
    usuarios_por_rol = dict(
        db.query(User.rol, func.count(User.id))
        .filter(User.tenant_id == tenant_id, User.is_active == True)
        .group_by(User.rol)
        .all()
    )
    
    return {
        "total_usuarios": total_usuarios,
        "usuarios_por_rol": usuarios_por_rol,
    }


# ============================================================
# Estadísticas globales (superadmin)
# ============================================================

def get_global_stats(db: Session) -> Dict[str, Any]:
    """
    Métricas globales de la plataforma para el superadmin:
    total de SPAs (activos/suspendidos), usuarios globales, MRR estimado
    y distribución por plan.
    """
    tenants = db.query(Tenant).filter(Tenant.deleted_at == None).all()

    total_spas = len(tenants)
    activos = sum(1 for t in tenants if t.is_active)
    inactivos = total_spas - activos

    total_usuarios_globales = db.query(func.count(User.id)).filter(
        User.deleted_at == None,
    ).scalar() or 0

    mrr_estimado = sum(
        PLAN_PRECIOS.get(t.plan, 0) for t in tenants if t.is_active
    )

    distribucion_planes = {plan: 0 for plan in PLAN_PRECIOS}
    for t in tenants:
        distribucion_planes[t.plan] = distribucion_planes.get(t.plan, 0) + 1

    return {
        "total_spas": total_spas,
        "activos": activos,
        "inactivos": inactivos,
        "total_usuarios_globales": total_usuarios_globales,
        "mrr_estimado": mrr_estimado,
        "distribucion_planes": distribucion_planes,
    }
