-- Extensiones necesarias para PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Crear un tipo enumerado para los roles de usuario
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
        CREATE TYPE user_role AS ENUM ('admin', 'client');
    END IF;
END$$;

-- Crear la tabla de usuarios
CREATE TABLE IF NOT EXISTS public.users (
    id_users UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role user_role NOT NULL DEFAULT 'client',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Campos para restablecimiento de contraseña
    reset_password_token VARCHAR(255),
    reset_password_token_expiry TIMESTAMP WITH TIME ZONE,
    -- Campos para verificación de email
    is_verified BOOLEAN DEFAULT false,
    verification_token VARCHAR(255),
    verification_token_expiry TIMESTAMP WITH TIME ZONE
);

-- Crear índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);
CREATE INDEX IF NOT EXISTS idx_users_reset_token ON public.users(reset_password_token);
CREATE INDEX IF NOT EXISTS idx_users_verification_token ON public.users(verification_token);

-- Función para actualizar automáticamente la fecha de modificación
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para actualizar automáticamente la columna updated_at
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_users_modified') THEN
        CREATE TRIGGER update_users_modified
        BEFORE UPDATE ON public.users
        FOR EACH ROW
        EXECUTE FUNCTION update_modified_column();
    END IF;
END$$;
