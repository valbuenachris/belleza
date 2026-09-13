-- ============================================================
-- database/schema.sql - Esquema completo de la base de datos
-- Sistema de Gestión SPA - Arquitectura Multitenant
-- ============================================================
-- ENGINE: InnoDB
-- CHARSET: utf8mb4
-- COLLATE: utf8mb4_unicode_ci
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- Tabla: tenants
-- Almacena cada SPA/centro de estética registrado
-- ============================================================
CREATE TABLE IF NOT EXISTS `tenants` (
    `id` CHAR(36) NOT NULL COMMENT 'UUID del tenant',
    `nombre` VARCHAR(255) NOT NULL COMMENT 'Nombre del SPA',
    `subdominio` VARCHAR(100) NOT NULL COMMENT 'Subdominio único',
    `plan` VARCHAR(50) NOT NULL DEFAULT 'basic' COMMENT 'Plan: basic, professional, enterprise',
    `activo` BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Estado activo/inactivo',
    `fecha_creacion` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Fecha de creación',
    `fecha_expiracion` DATETIME NULL DEFAULT NULL COMMENT 'Fecha de expiración de suscripción',
    `configuracion` JSON NULL DEFAULT NULL COMMENT 'Configuración específica del tenant',
    `limite_usuarios` INT NOT NULL DEFAULT 10 COMMENT 'Máximo de usuarios permitidos',
    `limite_pacientes` INT NOT NULL DEFAULT 1000 COMMENT 'Máximo de pacientes permitidos',
    `logo_url` VARCHAR(500) NULL DEFAULT NULL COMMENT 'URL del logo',
    `direccion` VARCHAR(500) NULL DEFAULT NULL COMMENT 'Dirección física',
    `telefono` VARCHAR(50) NULL DEFAULT NULL COMMENT 'Teléfono de contacto',
    `email` VARCHAR(255) NULL DEFAULT NULL COMMENT 'Email de contacto',
    `timezone` VARCHAR(50) NOT NULL DEFAULT 'America/Bogota' COMMENT 'Zona horaria',
    `moneda` VARCHAR(3) NOT NULL DEFAULT 'USD' COMMENT 'Moneda principal (ISO 4217)',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` DATETIME NULL DEFAULT NULL COMMENT 'Soft delete timestamp',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_tenants_subdominio` (`subdominio`),
    INDEX `idx_tenants_activo` (`is_active`),
    INDEX `idx_tenants_plan` (`plan`),
    INDEX `idx_tenants_deleted` (`deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tabla de tenants (SPAs registrados)';

-- ============================================================
-- Tabla: users
-- Almacena los usuarios del sistema
-- ============================================================
CREATE TABLE IF NOT EXISTS `users` (
    `id` CHAR(36) NOT NULL COMMENT 'UUID del usuario',
    `tenant_id` CHAR(36) NOT NULL COMMENT 'FK al tenant',
    `username` VARCHAR(100) NOT NULL COMMENT 'Nombre de usuario',
    `email` VARCHAR(255) NOT NULL COMMENT 'Correo electrónico',
    `password_hash` VARCHAR(255) NOT NULL COMMENT 'Contraseña hasheada (bcrypt)',
    `nombre` VARCHAR(100) NOT NULL COMMENT 'Nombre',
    `apellido` VARCHAR(100) NOT NULL COMMENT 'Apellido',
    `rol` VARCHAR(50) NOT NULL COMMENT 'Rol: superadmin, admin, manager, receptionist, therapist',
    `activo` BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Estado activo',
    `ultimo_acceso` DATETIME NULL DEFAULT NULL COMMENT 'Último acceso al sistema',
    `telefono` VARCHAR(50) NULL DEFAULT NULL COMMENT 'Teléfono',
    `avatar_url` VARCHAR(500) NULL DEFAULT NULL COMMENT 'URL del avatar',
    `email_verificado` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Email verificado',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` DATETIME NULL DEFAULT NULL COMMENT 'Soft delete timestamp',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    
    PRIMARY KEY (`id`),
    INDEX `idx_users_tenant` (`tenant_id`),
    INDEX `idx_users_email` (`email`),
    INDEX `idx_users_username` (`username`),
    INDEX `idx_users_rol` (`rol`),
    INDEX `idx_users_tenant_active` (`tenant_id`, `is_active`),
    INDEX `idx_users_deleted` (`deleted_at`),
    
    CONSTRAINT `fk_users_tenant` 
        FOREIGN KEY (`tenant_id`) 
        REFERENCES `tenants` (`id`) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tabla de usuarios del sistema';

-- ============================================================
-- Trigger: Actualizar updated_at automáticamente en tenants
-- ============================================================
DELIMITER //
DROP TRIGGER IF EXISTS `trg_tenants_updated_at`//
CREATE TRIGGER `trg_tenants_updated_at`
    BEFORE UPDATE ON `tenants`
    FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END//
DELIMITER ;

-- ============================================================
-- Trigger: Actualizar updated_at automáticamente en users
-- ============================================================
DELIMITER //
DROP TRIGGER IF EXISTS `trg_users_updated_at`//
CREATE TRIGGER `trg_users_updated_at`
    BEFORE UPDATE ON `users`
    FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END//
DELIMITER ;

-- ============================================================
-- Vista: Estadísticas de tenants
-- ============================================================
CREATE OR REPLACE VIEW `v_tenant_stats` AS
SELECT 
    t.id AS tenant_id,
    t.nombre AS tenant_nombre,
    t.subdominio,
    t.plan,
    t.activo,
    COUNT(DISTINCT u.id) AS total_usuarios,
    SUM(CASE WHEN u.is_active = TRUE THEN 1 ELSE 0 END) AS usuarios_activos,
    SUM(CASE WHEN u.rol = 'admin' THEN 1 ELSE 0 END) AS total_admins,
    SUM(CASE WHEN u.rol = 'therapist' THEN 1 ELSE 0 END) AS total_terapeutas
FROM tenants t
LEFT JOIN users u ON t.id = u.tenant_id AND u.deleted_at IS NULL
WHERE t.deleted_at IS NULL
GROUP BY t.id, t.nombre, t.subdominio, t.plan, t.activo;

-- ============================================================
-- Vista: Usuarios activos con datos del tenant
-- ============================================================
CREATE OR REPLACE VIEW `v_active_users` AS
SELECT 
    u.id,
    u.tenant_id,
    u.username,
    u.email,
    u.nombre,
    u.apellido,
    CONCAT(u.nombre, ' ', u.apellido) AS nombre_completo,
    u.rol,
    u.ultimo_acceso,
    u.telefono,
    u.email_verificado,
    u.created_at,
    t.nombre AS tenant_nombre,
    t.subdominio AS tenant_subdominio,
    t.plan AS tenant_plan
FROM users u
INNER JOIN tenants t ON u.tenant_id = t.id
WHERE u.is_active = TRUE 
    AND u.deleted_at IS NULL
    AND t.deleted_at IS NULL;

SET FOREIGN_KEY_CHECKS = 1;

-- Mensaje de confirmación
SELECT '✅ Esquema de base de datos creado/verificado correctamente' AS status;
