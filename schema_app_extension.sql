-- Tablas auxiliares requeridas por la aplicación web.
-- El resto del esquema proviene del DDL de COOVALLUNA.

CREATE TABLE IF NOT EXISTS usuario_sistema (
    id_usuario SERIAL PRIMARY KEY,
    correo VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    perfil VARCHAR(30) NOT NULL CHECK (
        perfil IN ('administrador', 'asesor', 'asociado')
    ),
    debe_cambiar_clave BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bitacora (
    id_bitacora SERIAL PRIMARY KEY,
    usuario VARCHAR(100) NOT NULL,
    operacion VARCHAR(100) NOT NULL,
    dato_afectado TEXT NOT NULL,
    fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
