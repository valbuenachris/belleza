-- ============================================================
-- database/seed.sql - Datos semilla / bootstrap
-- Sistema de Gestión SPA - Arquitectura Multitenant
-- ============================================================
-- Ejecutado automáticamente al inicializar un volumen MySQL nuevo
-- (docker-entrypoint-initdb.d). Idempotente: usa INSERT IGNORE
-- con IDs fijos para no duplicar registros.
-- ============================================================
-- ⚠️  ADVERTENCIA DE SEGURIDAD - LEER ANTES DE DESPLEGAR  ⚠️
-- ------------------------------------------------------------
-- Estas credenciales semilla son PÚBLICAS y NO deben usarse en
-- producción. El superadmin se crea con la contraseña placeholder
-- "CHANGE_ME_ON_FIRST_LOGIN_!23" (cámbiala en el primer login).
--   * NO ejecutes este archivo contra una base de datos de producción
--     sin cambiar la contraseña del superadmin inmediatamente.
--   * En producción crea el superadmin con una contraseña única y
--     gestionada con un secret manager.
-- ============================================================

SET NAMES utf8mb4;

-- ------------------------------------------------------------
-- Tenant por defecto (ID fijo, coincide con DEFAULT_TENANT_ID)
-- ------------------------------------------------------------
INSERT IGNORE INTO `tenants` (
    `id`,
    `nombre`,
    `subdominio`,
    `plan`,
    `fecha_creacion`,
    `fecha_expiracion`,
    `configuracion`,
    `limite_usuarios`,
    `limite_pacientes`,
    `logo_url`,
    `direccion`,
    `telefono`,
    `email`,
    `timezone`,
    `moneda`,
    `is_active`
) VALUES (
    '00000000-0000-0000-0000-000000000001', -- DEFAULT_TENANT_ID
    'SPA Demo',
    'demo',
    'enterprise',
    CURRENT_TIMESTAMP,
    NULL,                                     -- sin expiración
    JSON_OBJECT('horario', '9:00-19:00'),
    25,
    2000,
    NULL,
    'Calle Demo 123',
    '+1 555 000 0000',
    'demo@spa.com',
    'America/Bogota',
    'USD',
    TRUE
);

-- ------------------------------------------------------------
-- Superadmin global (tenant_id = NULL)
-- Email: superadmin@spa.com
-- Contraseña: CHANGE_ME_ON_FIRST_LOGIN_!23  (PLACEHOLDER - cambiar en el primer login)
-- Hash bcrypt generado con el mismo CryptContext de utils/security.py
-- ------------------------------------------------------------
INSERT IGNORE INTO `users` (
    `id`,
    `tenant_id`,
    `username`,
    `email`,
    `password_hash`,
    `nombre`,
    `apellido`,
    `rol`,
    `ultimo_acceso`,
    `telefono`,
    `avatar_url`,
    `email_verificado`,
    `is_active`
) VALUES (
    '11111111-1111-1111-1111-111111111111',
    NULL,                                     -- superadmin global no pertenece a un tenant
    'superadmin',
    'superadmin@spa.com',
    '$2b$12$fuvvcyJV..Rdd6cj60kDUO5V692DIAywMRNxJAeCKH4RS6.YAFy0.',
    'Super',
    'Admin',
    'superadmin',
    NULL,
    NULL,
    NULL,
    TRUE,
    TRUE
);

-- Mensaje de confirmación
SELECT '✅ Datos semilla insertados correctamente (superadmin + tenant demo)' AS status;