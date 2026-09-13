-- ============================================================
-- database/init.sql - Script de inicialización de la base de datos
-- Se ejecuta automáticamente al levantar el contenedor MySQL
-- ============================================================

-- Crear la base de datos si no existe
CREATE DATABASE IF NOT EXISTS `spa_management`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Seleccionar la base de datos
USE `spa_management`;

-- ============================================================
-- Crear usuario de aplicación (si no existe)
-- Nota: En Docker, el usuario ya se crea con las variables de entorno
-- Este script es un respaldo por si se ejecuta manualmente
-- ============================================================

-- Otorgar todos los privilegios al usuario de la aplicación
-- (El usuario ya fue creado por Docker con MYSQL_USER y MYSQL_PASSWORD)
GRANT ALL PRIVILEGES ON `spa_management`.* TO 'spa_user'@'%';

-- Recargar privilegios
FLUSH PRIVILEGES;

-- ============================================================
-- Mensaje de confirmación
-- ============================================================
SELECT '✅ Base de datos spa_management inicializada correctamente' AS status;
