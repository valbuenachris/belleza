-- ============================================================
-- database/schema.sql - Esquema completo de la base de datos
-- Sistema de Gestión SPA - Arquitectura Multitenant
-- ============================================================
-- ENGINE: InnoDB
-- CHARSET: utf8mb4
-- COLLATE: utf8mb4_unicode_ci
--
-- Este archivo es la fuente de verdad SQL para instalaciones
-- nuevas (docker-entrypoint-initdb.d). Debe mantenerse ALINEADO
-- con los modelos SQLAlchemy de backend/app/models/ y con las
-- migraciones de Alembic (backend/alembic/versions/).
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
    `fecha_creacion` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Fecha de creación',
    `fecha_expiracion` DATETIME NULL DEFAULT NULL COMMENT 'Fecha de expiración de suscripción (al crear: prueba gratis 14 días; NULL = exenta vía actualización explícita)',
    `configuracion` JSON NULL DEFAULT NULL COMMENT 'Configuración específica del tenant',
    `limite_usuarios` INT NOT NULL DEFAULT 10 COMMENT 'Máximo de usuarios permitidos',
    `limite_pacientes` INT NOT NULL DEFAULT 1000 COMMENT 'Máximo de pacientes permitidos',
    `logo_url` VARCHAR(500) NULL DEFAULT NULL COMMENT 'URL del logo',
    `direccion` VARCHAR(500) NULL DEFAULT NULL COMMENT 'Dirección física',
    `telefono` VARCHAR(50) NULL DEFAULT NULL COMMENT 'Teléfono de contacto',
    `email` VARCHAR(255) NULL DEFAULT NULL COMMENT 'Email de contacto',
    `timezone` VARCHAR(50) NOT NULL DEFAULT 'America/Bogota' COMMENT 'Zona horaria',
    `moneda` VARCHAR(3) NOT NULL DEFAULT 'USD' COMMENT 'Moneda principal (ISO 4217)',
    `puntos_meta` INT NOT NULL DEFAULT 10 COMMENT 'Estrellas necesarias para obtener una sesión gratuita',
    `premio_fidelidad` VARCHAR(255) NOT NULL DEFAULT 'Sesión de Spa gratis' COMMENT 'Premio al alcanzar las estrellas meta',
    `tarjeta_color_hex` VARCHAR(9) NOT NULL DEFAULT '#0D9488' COMMENT 'Color de fondo de la tarjeta de fidelidad',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- updated_at se mantiene desde el ORM (onupdate). Sin ON UPDATE
    -- CURRENT_TIMESTAMP para que haya una única fuente de verdad.
    `updated_at` DATETIME NULL DEFAULT NULL,
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
-- El superadmin global tiene tenant_id = NULL
-- ============================================================
CREATE TABLE IF NOT EXISTS `users` (
    `id` CHAR(36) NOT NULL COMMENT 'UUID del usuario',
    `tenant_id` CHAR(36) NULL DEFAULT NULL COMMENT 'FK al tenant (NULL para superadmin global)',
    `username` VARCHAR(100) NOT NULL COMMENT 'Nombre de usuario',
    `email` VARCHAR(255) NOT NULL COMMENT 'Correo electrónico',
    `password_hash` VARCHAR(255) NOT NULL COMMENT 'Contraseña hasheada (bcrypt)',
    `nombre` VARCHAR(100) NOT NULL COMMENT 'Nombre',
    `apellido` VARCHAR(100) NOT NULL COMMENT 'Apellido',
    `rol` VARCHAR(50) NOT NULL COMMENT 'Rol: superadmin, admin, manager, receptionist, therapist',
    `ultimo_acceso` DATETIME NULL DEFAULT NULL COMMENT 'Último acceso al sistema',
    `telefono` VARCHAR(50) NULL DEFAULT NULL COMMENT 'Teléfono',
    `avatar_url` VARCHAR(500) NULL DEFAULT NULL COMMENT 'URL del avatar',
    `email_verificado` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Email verificado',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NULL DEFAULT NULL,
    `deleted_at` DATETIME NULL DEFAULT NULL COMMENT 'Soft delete timestamp',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,

    PRIMARY KEY (`id`),
    INDEX `idx_users_tenant` (`tenant_id`),
    INDEX `idx_users_email` (`email`),
    INDEX `idx_users_username` (`username`),
    INDEX `idx_users_rol` (`rol`),
    -- Índice compuesto equivalente al definido por TenantBaseModel
    INDEX `idx_tenant_active` (`tenant_id`, `is_active`),
    INDEX `idx_users_deleted` (`deleted_at`),

    CONSTRAINT `fk_users_tenant`
        FOREIGN KEY (`tenant_id`)
        REFERENCES `tenants` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tabla de usuarios del sistema';

-- ============================================================
-- Tabla: patients
-- Almacena los pacientes registrados por cada SPA
-- ============================================================
CREATE TABLE IF NOT EXISTS `patients` (
    `id` CHAR(36) NOT NULL COMMENT 'UUID del paciente',
    `tenant_id` CHAR(36) NOT NULL COMMENT 'FK al tenant',
    `nombre` VARCHAR(100) NOT NULL COMMENT 'Nombre del paciente',
    `apellido` VARCHAR(100) NOT NULL COMMENT 'Apellido del paciente',
    `email` VARCHAR(255) NULL DEFAULT NULL COMMENT 'Email de contacto',
    `telefono` VARCHAR(50) NULL DEFAULT NULL COMMENT 'Teléfono',
    `fecha_nacimiento` DATE NULL DEFAULT NULL COMMENT 'Fecha de nacimiento',
    `genero` VARCHAR(30) NULL DEFAULT NULL COMMENT 'Género',
    `direccion` VARCHAR(500) NULL DEFAULT NULL COMMENT 'Dirección',
    `notas_medicas` TEXT NULL COMMENT 'Notas médicas o alergias',
    `puntos` INT NOT NULL DEFAULT 0 COMMENT 'Estrellas/puntos de fidelidad acumulados',
    `sesiones_gratis` INT NOT NULL DEFAULT 0 COMMENT 'Sesiones gratuitas disponibles',
    `wallet_pass_id` VARCHAR(128) NULL DEFAULT NULL COMMENT 'Identificador único del pase digital (Apple Wallet / Google Wallet)',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NULL DEFAULT NULL,
    `deleted_at` DATETIME NULL DEFAULT NULL COMMENT 'Soft delete timestamp',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,

    PRIMARY KEY (`id`),
    UNIQUE KEY `ux_patients_wallet_pass` (`wallet_pass_id`),
    INDEX `idx_patients_tenant` (`tenant_id`),
    INDEX `idx_patients_email` (`email`),
    INDEX `idx_tenant_active` (`tenant_id`, `is_active`),
    INDEX `idx_patients_deleted` (`deleted_at`),

    CONSTRAINT `fk_patients_tenant`
        FOREIGN KEY (`tenant_id`)
        REFERENCES `tenants` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tabla de pacientes del SPA';

-- ============================================================
-- Tabla: services
-- Catálogo de servicios ofrecidos por cada SPA
-- ============================================================
CREATE TABLE IF NOT EXISTS `services` (
    `id` CHAR(36) NOT NULL COMMENT 'UUID del servicio',
    `tenant_id` CHAR(36) NOT NULL COMMENT 'FK al tenant',
    `nombre` VARCHAR(255) NOT NULL COMMENT 'Nombre del servicio',
    `descripcion` TEXT NULL COMMENT 'Descripción del servicio',
    `precio` DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT 'Precio del servicio',
    `duracion` INT NOT NULL DEFAULT 60 COMMENT 'Duración en minutos',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NULL DEFAULT NULL,
    `deleted_at` DATETIME NULL DEFAULT NULL COMMENT 'Soft delete timestamp',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,

    PRIMARY KEY (`id`),
    INDEX `idx_services_tenant` (`tenant_id`),
    INDEX `idx_tenant_active` (`tenant_id`, `is_active`),
    INDEX `idx_services_deleted` (`deleted_at`),

    CONSTRAINT `fk_services_tenant`
        FOREIGN KEY (`tenant_id`)
        REFERENCES `tenants` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tabla de servicios del catálogo del SPA';

-- ============================================================
-- Tabla: appointments
-- Citas agendadas: paciente + terapeuta + servicio en un horario
-- ============================================================
CREATE TABLE IF NOT EXISTS `appointments` (
    `id` CHAR(36) NOT NULL COMMENT 'UUID de la cita',
    `tenant_id` CHAR(36) NOT NULL COMMENT 'FK al tenant',
    `patient_id` CHAR(36) NOT NULL COMMENT 'FK al paciente',
    `therapist_id` CHAR(36) NOT NULL COMMENT 'FK al terapeuta (usuarios)',
    `service_id` CHAR(36) NOT NULL COMMENT 'FK al servicio',
    `date_time` DATETIME NOT NULL COMMENT 'Fecha y hora de inicio',
    `duracion` INT NOT NULL DEFAULT 60 COMMENT 'Duración en minutos',
    `estado` VARCHAR(30) NOT NULL DEFAULT 'pending' COMMENT 'pending, confirmed, cancelled, completed',
    `precio` DECIMAL(10,2) NULL DEFAULT NULL COMMENT 'Precio cobrado (si es null se usa el del servicio)',
    `notas` TEXT NULL COMMENT 'Notas adicionales',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NULL DEFAULT NULL,
    `deleted_at` DATETIME NULL DEFAULT NULL COMMENT 'Soft delete timestamp',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,

    PRIMARY KEY (`id`),
    INDEX `idx_appointments_tenant` (`tenant_id`),
    INDEX `idx_appointments_patient` (`patient_id`),
    INDEX `idx_appointments_therapist` (`therapist_id`),
    INDEX `idx_appointments_service` (`service_id`),
    INDEX `idx_appointments_date_time` (`date_time`),
    INDEX `idx_appointments_estado` (`estado`),
    INDEX `idx_tenant_active` (`tenant_id`, `is_active`),
    INDEX `idx_appointments_deleted` (`deleted_at`),

    CONSTRAINT `fk_appointments_tenant`
        FOREIGN KEY (`tenant_id`)
        REFERENCES `tenants` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT `fk_appointments_patient`
        FOREIGN KEY (`patient_id`)
        REFERENCES `patients` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT `fk_appointments_therapist`
        FOREIGN KEY (`therapist_id`)
        REFERENCES `users` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT `fk_appointments_service`
        FOREIGN KEY (`service_id`)
        REFERENCES `services` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tabla de citas agendadas en el SPA';

-- ============================================================
-- Tabla: clinical_records
-- Historia clínica / evoluciones de tratamiento por paciente
-- ============================================================
CREATE TABLE IF NOT EXISTS `clinical_records` (
    `id` CHAR(36) NOT NULL COMMENT 'UUID del registro',
    `tenant_id` CHAR(36) NOT NULL COMMENT 'FK al tenant',
    `patient_id` CHAR(36) NOT NULL COMMENT 'FK al paciente',
    `therapist_id` CHAR(36) NULL DEFAULT NULL COMMENT 'FK al terapeuta (usuarios)',
    `appointment_id` CHAR(36) NULL DEFAULT NULL COMMENT 'FK a la cita/sesión asociada',
    `fecha` DATETIME NOT NULL COMMENT 'Fecha y hora de la sesión/evolución',
    `zona_tratada` VARCHAR(255) NULL DEFAULT NULL COMMENT 'Zona tratada (ej: Rostro, Espalda)',
    `tratamiento_servicio` VARCHAR(255) NULL DEFAULT NULL COMMENT 'Tratamiento o servicio realizado',
    `productos_parametros` TEXT NULL COMMENT 'Productos aplicados / parámetros',
    `observaciones` TEXT NULL COMMENT 'Observaciones y evolución del paciente',
    `diagnostico` TEXT NULL COMMENT 'Diagnóstico o valoración clínica',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NULL DEFAULT NULL,
    `deleted_at` DATETIME NULL DEFAULT NULL COMMENT 'Soft delete timestamp',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,

    PRIMARY KEY (`id`),
    INDEX `idx_clinical_records_tenant` (`tenant_id`),
    INDEX `idx_clinical_records_patient` (`patient_id`),
    INDEX `idx_clinical_records_therapist` (`therapist_id`),
    INDEX `idx_clinical_records_appointment` (`appointment_id`),
    INDEX `idx_clinical_records_fecha` (`fecha`),
    INDEX `idx_tenant_active` (`tenant_id`, `is_active`),
    INDEX `idx_clinical_records_deleted` (`deleted_at`),

    CONSTRAINT `fk_clinical_records_tenant`
        FOREIGN KEY (`tenant_id`)
        REFERENCES `tenants` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT `fk_clinical_records_patient`
        FOREIGN KEY (`patient_id`)
        REFERENCES `patients` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT `fk_clinical_records_therapist`
        FOREIGN KEY (`therapist_id`)
        REFERENCES `users` (`id`)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    CONSTRAINT `fk_clinical_records_appointment`
        FOREIGN KEY (`appointment_id`)
        REFERENCES `appointments` (`id`)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tabla de historia clínica / evoluciones de tratamiento';

-- ============================================================
-- NOTA: Los triggers de actualización automática de updated_at
-- fueron ELIMINADOS. updated_at lo mantiene el ORM (onupdate),
-- alineado con las migraciones de Alembic y con create_all.
-- ============================================================

-- ============================================================
-- Vista: Estadísticas de tenants
-- ============================================================
CREATE OR REPLACE VIEW `v_tenant_stats` AS
SELECT
    t.id AS tenant_id,
    t.nombre AS tenant_nombre,
    t.subdominio,
    t.plan,
    t.is_active AS activo,
    COUNT(DISTINCT u.id) AS total_usuarios,
    SUM(CASE WHEN u.is_active = TRUE THEN 1 ELSE 0 END) AS usuarios_activos,
    SUM(CASE WHEN u.rol = 'admin' THEN 1 ELSE 0 END) AS total_admins,
    SUM(CASE WHEN u.rol = 'therapist' THEN 1 ELSE 0 END) AS total_terapeutas
FROM tenants t
LEFT JOIN users u ON t.id = u.tenant_id AND u.deleted_at IS NULL
WHERE t.deleted_at IS NULL
GROUP BY t.id, t.nombre, t.subdominio, t.plan, t.is_active;

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