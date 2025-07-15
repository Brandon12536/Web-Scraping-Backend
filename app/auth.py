import os
import uuid
from dotenv import load_dotenv

# Cargar variables de entorno primero
load_dotenv(override=True)

# Ahora importar el resto de dependencias
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

oauth2_scheme = HTTPBearer()
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
import random
from datetime import datetime, timedelta, timezone
import jwt
import secrets
import string
from passlib.context import CryptContext
from supabase import create_client, Client

# Si quieres, puedes dejar el try/except solo para lógica específica, no para imports masivos.

# Inicializar cliente de Supabase con validación
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("Missing Supabase URL or Key in environment variables")

try:
    supabase: Client = create_client(supabase_url, supabase_key)
    # Test the connection
    supabase.table('users').select("*").limit(1).execute()
except Exception as e:
    print(f"Error initializing Supabase client: {e}")
    raise

# Configuración de seguridad
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# URL del frontend para verificación de correo
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Configuración JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
# Convert to int and handle potential None or invalid values
try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30))
except (ValueError, TypeError):
    # Default to 30 days if there's an issue with the environment variable
    ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days in minutes

# Almacenamiento en memoria para tokens revocados (en producción, usa Redis o tu base de datos)
token_blacklist = set()

# Inicializar router
router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Autenticación"],
    responses={404: {"description": "No encontrado"}}
)

# Modelos
class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class TokenData(BaseModel):
    email: Optional[str] = None

class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str = "client"
    is_active: bool = True
    is_verified: bool = False

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    company: Optional[str] = None
    website: Optional[str] = None
    
    @validator('password')
    def password_complexity(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v

class UserInDB(UserBase):
    id: str
    password_hash: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    company: Optional[str] = None
    website: Optional[str] = None
    is_super_admin: bool = False
    verification_token: Optional[str] = None
    reset_password_token: Optional[str] = None
    reset_password_token_expiry: Optional[datetime] = None

class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    company: Optional[str] = None
    website: Optional[str] = None
    is_super_admin: bool = False
    
    class Config:
        from_attributes = True

class User(UserInDB):
    """Modelo de usuario que incluye todos los datos del usuario"""
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str = "client"
    is_verified: bool = False

    class Config:
        from_attributes = True

# Modelos para las solicitudes
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class VerifyRequest(BaseModel):
    email: EmailStr
    token: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr

class NewPasswordRequest(BaseModel):
    token: str
    new_password: str

# Enviar correo con enlace de recuperación de contraseña usando SMTP

def send_reset_password_email(email: str, first_name: str, reset_link: str):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import os

    smtp_server = os.getenv("EMAIL_HOST")
    smtp_port = int(os.getenv("EMAIL_PORT", 587))
    smtp_username = os.getenv("EMAIL_USER")
    smtp_password = os.getenv("EMAIL_PASS")

    sender_email = smtp_username
    message = MIMEMultipart("alternative")
    message["Subject"] = "Recupera tu contraseña"
    message["From"] = sender_email
    message["To"] = email

    html = f"""
    <html>
      <body style='font-family:Segoe UI,Arial,sans-serif;background:#f5f7fa;'>
        <div style='max-width:480px;margin:40px auto;background:#fff;padding:32px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.04);'>
          <h2 style='color:#4f8cff;'>Hola {first_name or 'usuario'},</h2>
          <p>Recibimos una solicitud para restablecer tu contraseña. Haz clic en el siguiente botón:</p>
          <div style='text-align:center;margin:32px 0;'>
            <a href=\"{reset_link}\" style='background:#4f8cff;color:#fff;padding:16px 32px;border-radius:6px;text-decoration:none;font-size:18px;'>Restablecer contraseña</a>
          </div>
          <p>Si no solicitaste este cambio, puedes ignorar este correo.</p>
          <p style='color:#888;font-size:12px;'>El enlace expirará en 1 hora.</p>
        </div>
      </body>
    </html>
    """

    part = MIMEText(html, "html")
    message.attach(part)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, email, message.as_string())
        print(f"[OK] Correo de recuperación enviado a {email}")
    except Exception as e:
        print(f"[ERROR] Fallo al enviar correo de recuperación a {email}: {str(e)}")

# Funciones de utilidad
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verificar si el token está en la lista negra
    if token in token_blacklist:
        raise credentials_exception
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
        
    # Obtener usuario de la base de datos
    response = supabase.table('users').select('*').eq('email', email).execute()
    
    if not response.data:
        raise credentials_exception
        
    user = response.data[0]
    user = UserInDB(**user)
    
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user

def send_verification_email(email: str, first_name: str, verification_code: str):
    """Enviar correo con el código de verificación usando SMTP"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import logging
    
    # Obtener el dominio del correo del usuario
    user_domain = email.split('@')[-1] if '@' in email else 'app.com'
    
    # Configuración del correo desde variables de entorno (adaptado a tu .env)
    smtp_server = os.getenv("EMAIL_HOST")
    smtp_port = int(os.getenv("EMAIL_PORT", 587))
    smtp_username = os.getenv("EMAIL_USER")
    smtp_password = os.getenv("EMAIL_PASS")
    
    # Configuración dinámica del remitente
    email_from_name = f"{first_name} desde {user_domain}" if first_name else f"Soporte de {user_domain}"
    sender_email = f"noreply@{user_domain}"
    
    # Crear el mensaje
    message = MIMEMultipart("alternative")
    message["Subject"] = f"{email_from_name} - Código de verificación"
    message["From"] = f"{email_from_name} <{sender_email}>"
    message["To"] = email
    message["Reply-To"] = email  # Permitir responder al usuario
    
    # Crear el contenido HTML del correo
    html = f"""
    <html>
      <body style='margin:0;padding:0;background:#f5f7fa;font-family:Segoe UI,Arial,sans-serif;'>
        <table width='100%' cellpadding='0' cellspacing='0' border='0' style='background:#f5f7fa;'>
          <tr>
            <td align='center'>
              <table width='480' cellpadding='0' cellspacing='0' border='0' style='background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.04);margin:40px 0;'>
                <tr>
                  <td style='background:#4f8cff;padding:24px 0;border-radius:8px 8px 0 0;text-align:center;'>
                    <span style='font-size:24px;color:#fff;font-weight:600;letter-spacing:1px;'>Bienvenido a la Plataforma</span>
                  </td>
                </tr>
                <tr>
                  <td style='padding:32px 32px 12px 32px;'>
                    <h2 style='margin:0 0 8px 0;font-size:22px;font-weight:500;color:#222;'>Hola {first_name},</h2>
                    <p style='margin:0 0 20px 0;font-size:16px;color:#444;'>¡Gracias por registrarte! Para completar tu registro, verifica tu correo electrónico usando el siguiente código:</p>
                    <div style='text-align:center;margin:32px 0;'>
                      <span style='display:inline-block;background:#eaf1fb;color:#214f8c;font-size:32px;font-weight:bold;letter-spacing:8px;padding:18px 32px;border-radius:8px;border:1px solid #d7e3fa;'>{verification_code}</span>
                    </div>
                    <p style='margin:18px 0 0 0;font-size:15px;color:#666;'>Este código expirará en 24 horas.</p>
                    <p style='margin:0;font-size:13px;color:#888;'>Si no solicitaste este código, puedes ignorar este correo.</p>
                  </td>
                </tr>
                <tr>
                  <td style='padding:24px 32px 32px 32px;'>
                    <p style='margin:0;font-size:15px;color:#4f8cff;font-weight:500;'>El equipo de Soporte</p>
                  </td>
                </tr>
                <tr>
                  <td style='background:#f5f7fa;padding:18px 0 8px 0;border-radius:0 0 8px 8px;text-align:center;'>
                    <span style='font-size:12px;color:#b0b0b0;'>© 2025 Tu Empresa. Todos los derechos reservados.</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
    
    # Adjuntar el HTML al mensaje
    part = MIMEText(html, "html")
    message.attach(part)
    
    try:
        # Enviar el correo usando SMTP con STARTTLS (TLS seguro, puerto 587)
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, email, message.as_string())
        print(f"[OK] Correo de verificación enviado a {email}")
    except Exception as e:
        logging.error(f"[ERROR] Fallo al enviar correo a {email}: {str(e)}")
        print(f"\n{'='*50}\n"
              f"Código de verificación para {first_name} ({email}):\n"
              f"{verification_code}\n"
              f"Este código expirará en 24 horas.\n"
              f"{'='*50}\n")

# Endpoints de la API
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: RegisterRequest, background_tasks: BackgroundTasks):
    """
    Registrar un nuevo usuario
    """
    try:
        # Verificar si el correo ya está registrado
        existing_user = supabase.table('users').select('*').eq('email', user.email).execute()
        if existing_user.data and len(existing_user.data) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está registrado"
            )

        # Verificar si ya existe un administrador
        admin_check = supabase.table('users').select('*').eq('role', 'admin').execute()
        
        # Asignar rol: admin si no hay administradores, cliente en caso contrario
        role = 'admin' if not admin_check.data or len(admin_check.data) == 0 else 'client'
        
        # Generar un id único para el usuario (puedes usar uuid4 si quieres)
        import uuid
        user_id = str(uuid.uuid4())
        # Generar código de verificación de 6 dígitos
        verification_code = str(random.randint(100000, 999999))
        verification_expiry = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        
        # Insertar usuario en public.users según el esquema de la base de datos
        user_record = {
            'id_users': user_id,
            'email': user.email,
            'first_name': user.first_name or None,
            'last_name': user.last_name or None,
            'role': role,
            'is_active': True,
            'password_hash': get_password_hash(user.password),
            'is_verified': False,
            'verification_token': verification_code,  # Guardar el código de 6 dígitos
            'verification_token_expiry': verification_expiry
        }
        
        try:
            # Intentar insertar el usuario
            insert_response = supabase.table('users').insert(user_record).execute()
            
            if not insert_response.data:
                raise Exception("No se recibieron datos en la respuesta de inserción")
                
        except Exception as e:
            # Limpiar usuario de auth si falla la inserción en la base de datos
            try:
                supabase.auth.admin.delete_user(user_id)
            except Exception as cleanup_e:
                print(f"Error al limpiar el usuario de autenticación: {cleanup_e}")
            
            print(f"Error al insertar usuario: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al crear el registro de usuario: {str(e)}"
            )
    
        # Enviar correo con el código de verificación
        background_tasks.add_task(
            send_verification_email,
            email=user.email,
            first_name=user.first_name or 'Usuario',
            verification_code=verification_code  # Enviar el código en lugar del enlace
        )
        
        # Devolver datos del usuario sin información sensible
        return {
            'id': user_id,
            'email': user.email,
            'first_name': user.first_name or '',
            'last_name': user.last_name or '',
            'role': role,  # Usar el rol asignado (admin o client)
            'is_active': True,
            'is_verified': False,
            'is_super_admin': False,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'last_login': None
        }
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error en el registro: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en el servidor: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest):
    """
    Autenticar usuario y devolver token JWT
    """
    try:
        # Buscar usuario por email en tu tabla
        user_response = supabase.table('users').select('*').eq('email', login_data.email).single().execute()
        user = user_response.data
        if not user:
            raise HTTPException(status_code=401, detail="Correo electrónico o contraseña incorrectos")
        # Verifica el hash de la contraseña
        if not verify_password(login_data.password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Correo electrónico o contraseña incorrectos")
        # Verifica que esté verificado
        if not user.get('is_verified'):
            raise HTTPException(status_code=401, detail="Debes verificar tu correo electrónico antes de iniciar sesión")
        # Genera el token JWT y responde
        
        # Crear token JWT
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["email"]}, 
            expires_delta=access_token_expires
        )
        
        # Preparar respuesta del usuario
        user_response = {
            'id_users': user['id_users'],
            'email': user['email'],
            'first_name': user.get('first_name'),
            'last_name': user.get('last_name'),
            'role': user.get('role', 'client'),
            'is_active': user.get('is_active', True),
            'is_verified': user.get('is_verified', False),
            'company': user.get('company'),
            'website': user.get('website'),
            'is_super_admin': user.get('is_super_admin', False),
            'created_at': user.get('created_at'),
            'updated_at': user.get('updated_at'),
                    }
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_response
        }
        
    except Exception as e:
        print(f"Error en el inicio de sesión: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/verify-email")
async def verify_email(verify_data: VerifyRequest):
    """
    Verificar el correo electrónico del usuario usando el código de verificación
    """
    import logging
    try:
        # Buscar usuario por email y código de verificación
        user = supabase.table('users').select('*')\
            .eq('email', verify_data.email)\
            .eq('verification_token', verify_data.token)\
            .execute()
        
        if not user.data or len(user.data) == 0:
            logging.warning(f"No se encontró usuario con email={verify_data.email} y token={verify_data.token}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Código de verificación inválido o expirado"
            )
        user = user.data[0]
        # Si ya está verificado
        if user.get('is_verified'):
            return {"message": "El correo electrónico ya está verificado"}
        # Si el token o la expiración es None
        if not user.get('verification_token') or not user.get('verification_token_expiry'):
            logging.error(f"Token o expiración nulos para usuario {verify_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El código de verificación no está disponible o ya fue usado"
            )
        # Verificar si el código ha expirado
        try:
            expiry_date = user['verification_token_expiry']
            if isinstance(expiry_date, str):
                expiry_date = datetime.fromisoformat(expiry_date).replace(tzinfo=timezone.utc)
            elif hasattr(expiry_date, 'tzinfo') and expiry_date.tzinfo is None:
                expiry_date = expiry_date.replace(tzinfo=timezone.utc)
        except Exception as dt_err:
            logging.error(f"Error al convertir la fecha de expiración: {dt_err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error en la fecha de expiración: {dt_err}"
            )
        if datetime.now(timezone.utc) > expiry_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El código de verificación ha expirado"
            )
        # Marcar como verificado y limpiar token
        supabase.table('users').update({
            'is_verified': True,
            'verification_token': None,
            'verification_token_expiry': None
        }).eq('id_users', user['id_users']).execute()
        return {"message": "Correo verificado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error inesperado en la verificación: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al verificar el correo electrónico"
        )

@router.post("/forgot-password")
async def forgot_password(reset_data: ResetPasswordRequest, background_tasks: BackgroundTasks):
    """
    Enviar correo electrónico para restablecer la contraseña
    """
    try:
        # Verificar si el usuario existe
        response = supabase.table('users')\
            .select('id_users,email,first_name')\
            .eq('email', reset_data.email)\
            .single()\
            .execute()
        
        if not response.data:
            # No revelar que el correo no existe
            return {"message": "Si tu correo está registrado, recibirás un enlace para restablecer la contraseña"}
        
        user = response.data
        reset_token = str(uuid.uuid4())
        reset_expiry = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        
        # Almacenar token de restablecimiento en la base de datos
        supabase.table('users')\
            .update({
                'reset_password_token': reset_token,
                'reset_password_token_expiry': reset_expiry,
                'updated_at': datetime.utcnow().isoformat()
            })\
            .eq('id_users', user['id_users'])\
            .execute()
        
        # En una aplicación real, aquí enviarías un correo con el enlace
        reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"
        print(f"Enlace de restablecimiento de contraseña para {user['email']}: {reset_link}")
        
        # Enviar el correo real de recuperación
        background_tasks.add_task(
            send_reset_password_email,
            email=user['email'],
            first_name=user.get('first_name', 'Usuario'),
            reset_link=reset_link
        )
        
        return {"message": "Si tu correo está registrado, recibirás un enlace para restablecer la contraseña"}
        
    except Exception as e:
        print(f"Error al solicitar restablecimiento de contraseña: {str(e)}")
        # No revelar el error real al usuario
        return {"message": "Si tu correo está registrado, recibirás un enlace para restablecer la contraseña"}

@router.post("/reset-password")
async def reset_password(reset_data: NewPasswordRequest):
    """
    Restablecer la contraseña usando el token de restablecimiento
    """
    try:
        # Buscar usuario por token de restablecimiento
        response = supabase.table('users')\
            .select('*')\
            .eq('reset_password_token', reset_data.token)\
            .single()\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de restablecimiento inválido o expirado"
            )
        
        user = response.data
        
        # Verificar si el token ha expirado
        expiry_date = datetime.fromisoformat(user['reset_password_token_expiry'])
        now = datetime.now(expiry_date.tzinfo) if expiry_date.tzinfo else datetime.utcnow()
        if now > expiry_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El enlace de restablecimiento ha expirado"
            )
        
        # Actualizar hash de contraseña en la base de datos
        supabase.table('users')\
            .update({
                'password_hash': get_password_hash(reset_data.new_password),
                'reset_password_token': None,
                'reset_password_token_expiry': None,
                'updated_at': datetime.utcnow().isoformat()
            })\
            .eq('id_users', user['id_users'])\
            .execute()
        
        return {"message": "Contraseña restablecida exitosamente"}
        
    except Exception as e:
        print(f"Error al restablecer la contraseña: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo restablecer la contraseña"
        )

# Inicializa el blacklist al inicio del archivo si no existe
token_blacklist = set()

@router.post("/logout")
async def logout(token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    """
    Cerrar sesión del usuario actual e invalidar el token
    """
    token_str = token.credentials  # Extrae el Bearer token
    print(f"[DEBUG] Token recibido en logout: {token_str}")
    try:
        payload = jwt.decode(token_str, SECRET_KEY, algorithms=[ALGORITHM])
        # Agregar el token a la blacklist
        token_blacklist.add(token_str)
        return {"message": "Sesión cerrada correctamente"}
    except jwt.ExpiredSignatureError:
        return {"message": "El token ya ha expirado"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    return {"message": "Sesión cerrada exitosamente"}
