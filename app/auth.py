import os
import uuid
from dotenv import load_dotenv

# Cargar variables de entorno primero
load_dotenv(override=True)

# Ahora importar el resto de dependencias
try:
    from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
    from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
    from pydantic import BaseModel, EmailStr, Field, validator
    from typing import Optional, List, Dict, Any
    import random
    from datetime import datetime, timedelta
    from pytz import timezone
    import jwt
    import secrets
    import string
    from passlib.context import CryptContext
    from supabase import create_client, Client

except ImportError as e:
    print(f"Error importing dependencies: {e}")
    raise

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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

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
    tags=["Authentication"],
    responses={404: {"description": "Not found"}},
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
    token: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr

class NewPasswordRequest(BaseModel):
    token: str
    new_password: str

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
        
    user_data = response.data[0]
    user = UserInDB(**user_data)
    
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
    
    # Obtener el dominio del correo del usuario
    user_domain = email.split('@')[-1] if '@' in email else 'app.com'
    
    # Configuración del correo desde variables de entorno
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 465))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
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
      <body>
        <h2>Hola {first_name},</h2>
        <p>Gracias por registrarte. Usa el siguiente código para verificar tu correo electrónico:</p>
        <h1 style="text-align: center; font-size: 36px; letter-spacing: 5px; margin: 20px 0; padding: 20px; background: #f4f4f4; border-radius: 5px;">
            {verification_code}
        </h1>
        <p>Este código expirará en 24 horas.</p>
        <p>Si no solicitaste este código, puedes ignorar este mensaje.</p>
        <p>Saludos,<br>El equipo de Soporte</p>
      </body>
    </html>
    """
    
    # Adjuntar el HTML al mensaje
    part = MIMEText(html, "html")
    message.attach(part)
    
    try:
        # Enviar el correo usando SMTP
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            # Usar las credenciales SMTP para autenticación
            server.login(smtp_username, smtp_password)
            # Enviar con el remitente dinámico
            server.sendmail(sender_email, email, message.as_string())
        print(f"Correo de verificación enviado a {email}")
        
    except Exception as e:
        # Si falla el envío, mostrar el código en consola para desarrollo
        print(f"Error al enviar correo: {str(e)}")
        print(f"\n{'='*50}\n"
              f"Código de verificación para {first_name} ({email}):\n"
              f"{verification_code}\n"
              f"Este código expirará en 24 horas.\n"
              f"{'='*50}\n")

# Endpoints de la API
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: RegisterRequest, background_tasks: BackgroundTasks):
    """
    Registrar un nuevo usuario
    """
    try:
        # Verificar si el correo ya está registrado
        existing_user = supabase.table('users').select('*').eq('email', user_data.email).execute()
        if existing_user.data and len(existing_user.data) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está registrado"
            )

        # Verificar si ya existe un administrador
        admin_check = supabase.table('users').select('*').eq('role', 'admin').execute()
        
        # Asignar rol: admin si no hay administradores, cliente en caso contrario
        role = 'admin' if not admin_check.data or len(admin_check.data) == 0 else 'client'
        
        # Crear usuario en Auth
        auth_response = supabase.auth.sign_up({
            'email': user_data.email,
            'password': user_data.password,
            'options': {
                'data': {
                    'first_name': user_data.first_name or '',
                    'last_name': user_data.last_name or '',
                    'role': role
                }
            }
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error al crear el usuario en el servicio de autenticación"
            )
            
        # Crear usuario en la tabla public.users
        user_id = str(auth_response.user.id)
        # Generar código de verificación de 6 dígitos
        verification_code = str(random.randint(100000, 999999))
        verification_expiry = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        
        # Insertar usuario en public.users según el esquema de la base de datos
        user_record = {
            'id_users': user_id,
            'email': user_data.email,
            'first_name': user_data.first_name or None,
            'last_name': user_data.last_name or None,
            'role': role,
            'is_active': True,
            'password_hash': get_password_hash(user_data.password),
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
            email=user_data.email,
            first_name=user_data.first_name or 'Usuario',
            verification_code=verification_code  # Enviar el código en lugar del enlace
        )
        
        # Devolver datos del usuario sin información sensible
        return {
            'id': user_id,
            'email': user_data.email,
            'first_name': user_data.first_name or '',
            'last_name': user_data.last_name or '',
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
        # Autenticar con Supabase
        auth_response = supabase.auth.sign_in_with_password({
            'email': login_data.email,
            'password': login_data.password
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo electrónico o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Obtener usuario de la tabla public.users
        response = supabase.table('users')\
            .select('*')\
            .eq('email', login_data.email)\
            .single()\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        user_data = response.data
        
        # Verificar si el usuario está activo
        if not user_data.get('is_active', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La cuenta está desactivada"
            )
        
        # Verificar si el correo está verificado
        if not user_data.get('is_verified', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Por favor verifica tu correo electrónico antes de iniciar sesión"
            )
        
        # Actualizar último inicio de sesión
        now = datetime.utcnow().isoformat()
        supabase.table('users')\
            .update({'last_login': now})\
            .eq('id', user_data['id'])\
            .execute()
        
        # Crear token JWT
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_data["email"]}, 
            expires_delta=access_token_expires
        )
        
        # Preparar respuesta del usuario
        user_response = {
            'id': user_data['id'],
            'email': user_data['email'],
            'first_name': user_data.get('first_name'),
            'last_name': user_data.get('last_name'),
            'role': user_data.get('role', 'client'),
            'is_active': user_data.get('is_active', True),
            'is_verified': user_data.get('is_verified', False),
            'company': user_data.get('company'),
            'website': user_data.get('website'),
            'is_super_admin': user_data.get('is_super_admin', False),
            'created_at': user_data.get('created_at'),
            'updated_at': user_data.get('updated_at'),
            'last_login': now
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
    try:
        # Buscar usuario por código de verificación
        user_data = supabase.table('users').select('*').eq('verification_token', verify_data.token).execute()
        
        if not user_data.data or len(user_data.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Código de verificación inválido o expirado"
            )
            
        user = user_data.data[0]
        
        # Verificar si el código ha expirado
        expiry_date = datetime.fromisoformat(user['verification_token_expiry']).replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expiry_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El código de verificación ha expirado"
            )
            
        # Actualizar usuario como verificado
        update_data = {
            'is_verified': True,
            'verification_token': None,
            'verification_token_expiry': None,
            'updated_at': datetime.utcnow().isoformat(),
            'email_verified_at': datetime.utcnow().isoformat()
        }
        
        supabase.table('users').update(update_data).eq('id_users', user['id_users']).execute()
        
        return {"message": "Correo electrónico verificado exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en la verificación de correo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al verificar el correo electrónico"
        )

@router.post("/forgot-password")
async def forgot_password(reset_data: ResetPasswordRequest):
    """
    Enviar correo electrónico para restablecer la contraseña
    """
    try:
        # Verificar si el usuario existe
        response = supabase.table('users')\
            .select('id,email,first_name')\
            .eq('email', reset_data.email)\
            .single()\
            .execute()
        
        if not response.data:
            # No revelar que el correo no existe
            return {"message": "Si tu correo está registrado, recibirás un enlace para restablecer la contraseña"}
        
        user_data = response.data
        reset_token = str(uuid.uuid4())
        reset_expiry = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        
        # Almacenar token de restablecimiento en la base de datos
        supabase.table('users')\
            .update({
                'reset_password_token': reset_token,
                'reset_password_token_expiry': reset_expiry,
                'updated_at': datetime.utcnow().isoformat()
            })\
            .eq('id', user_data['id'])\
            .execute()
        
        # En una aplicación real, aquí enviarías un correo con el enlace
        reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"
        print(f"Enlace de restablecimiento de contraseña para {user_data['email']}: {reset_link}")
        
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
        
        user_data = response.data
        
        # Verificar si el token ha expirado
        expiry_date = datetime.fromisoformat(user_data['reset_password_token_expiry'])
        if datetime.utcnow() > expiry_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El enlace de restablecimiento ha expirado"
            )
        
        # Actualizar contraseña
        supabase.auth.admin.update_user_by_id(
            user_data['id'],
            {'password': reset_data.new_password}
        )
        
        # Actualizar hash de contraseña en la base de datos
        supabase.table('users')\
            .update({
                'password_hash': get_password_hash(reset_data.new_password),
                'reset_password_token': None,
                'reset_password_token_expiry': None,
                'updated_at': datetime.utcnow().isoformat()
            })\
            .eq('id', user_data['id'])\
            .execute()
        
        return {"message": "Contraseña restablecida exitosamente"}
        
    except Exception as e:
        print(f"Error al restablecer la contraseña: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo restablecer la contraseña"
        )

@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    """
    Cerrar sesión del usuario actual e invalidar el token
    """
    try:
        # Decodificar el token para obtener su expiración
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Agregar el token a la lista negra hasta que expire
        token_blacklist.add(token)
        
        # Programar la eliminación del token de la lista negra después de su expiración
        expire_timestamp = payload.get("exp")
        if expire_timestamp:
            from datetime import datetime
            expire_datetime = datetime.fromtimestamp(expire_timestamp)
            current_time = datetime.utcnow()
            time_until_expire = (expire_datetime - current_time).total_seconds()
            
            # Si el token ya expiró, no es necesario hacer nada más
            if time_until_expire > 0:
                # Programar la eliminación del token después de que expire
                import asyncio
                
                async def remove_expired_token():
                    await asyncio.sleep(time_until_expire)
                    token_blacklist.discard(token)
                
                asyncio.create_task(remove_expired_token())
        
        # Cerrar sesión en Supabase Auth
        try:
            supabase.auth.sign_out()
        except Exception as e:
            print(f"Error al cerrar sesión en Supabase: {e}")
        
        return {"message": "Sesión cerrada exitosamente"}
        
    except JWTError as e:
        # Si hay un error al decodificar el token, no es necesario hacer nada
        # ya que el token ya es inválido
        pass
    
    return {"message": "Sesión cerrada exitosamente"}
