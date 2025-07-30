import os
from dotenv import load_dotenv

# Cargar variables de entorno primero
load_dotenv(override=True)

# Ahora importar el resto de dependencias
try:
    from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Depends
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.security import OAuth2PasswordBearer
    from pydantic import BaseModel, Field, HttpUrl, EmailStr
    from typing import List, Optional, Dict, Any, Union, Set, Tuple
    import asyncio
    import aiohttp
    import re
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin, urlparse, unquote
    import time
    from datetime import datetime
    import json
    import io
    from io import BytesIO
    import base64
    from PIL import Image
    import pytesseract
    from fastapi.responses import JSONResponse
    from fastapi.openapi.docs import get_swagger_ui_html
    from fastapi.openapi.utils import get_openapi
    import logging
    logger = logging.getLogger("webscraper")
    logger.setLevel(logging.INFO)

except ImportError as e:
    print(f"Error importing dependencies: {e}")
    raise

# Import auth router
from . import auth
import aiohttp
from typing import Union

# Instancia de FastAPI
app = FastAPI(
    title="🚀 FastAPI Email Scraper with Auth",
    root_path=os.getenv("ROOT_PATH", ""),
    description="""
    API de alto rendimiento para extracción de correos electrónicos de sitios web.
    
    **Características:**
    - Escaneo rápido y concurrente
    - Documentación interactiva con Swagger UI
    - Límites personalizables (páginas, correos, tiempo de espera)
    - Filtrado de dominios y rutas
    - Limpieza automática de caché
    """,
    version="1.0.0",
    docs_url="/docs",  # Habilitar Swagger UI en /docs
    redoc_url="/redoc",  # Habilitar ReDoc en /redoc
    openapi_url="/openapi.json",  # Ruta del esquema OpenAPI
    openapi_tags=[
        {
            "name": "Autenticación",
            "description": "Operaciones de inicio/cierre de sesión y gestión de usuarios."
        },
        {
            "name": "Scraping",
            "description": "Extracción automatizada de correos electrónicos y datos de sitios web."
        },
        {
            "name": "Estado",
            "description": "Consulta el estado y funcionamiento actual del servicio de scraping."
        }
    ]
)

from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root():
    return """
    <!DOCTYPE html>
    <html lang='es'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>FastAPI Email Scraper</title>
        <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css' rel='stylesheet'>
        <link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap' rel='stylesheet'>
        <style>
            body {
                min-height: 100vh;
                background: linear-gradient(120deg,#e0e7ff 0%,#f0fdfa 100%) no-repeat;
                font-family: 'Inter', sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.6s;
            }
            .hero {
                padding: 3.5rem 2rem 2.2rem 2rem;
                text-align: center;
                max-width: 420px;
                margin: 3rem auto 0 auto;
                background: rgba(255,255,255,0.98);
                border-radius: 2.2rem;
                box-shadow: 0 8px 40px 0 #6366f120, 0 1.5px 0 #fff8;
                border: 1.5px solid #dbeafe;
                position: relative;
                overflow: hidden;
                opacity: 0;
                transform: scale(0.85) translateY(40px);
                animation: hero-in 0.9s cubic-bezier(.4,2,.6,1) 0.3s forwards;
            }
            .hero::before {
                content: "";
                position: absolute;
                z-index: 0;
                left: -40%;
                top: -30%;
                width: 180%;
                height: 80%;
                background: radial-gradient(circle at 60% 40%, #38bdf8 0%, #6366f1 70%, transparent 100%);
                opacity: 0.11;
            }
            .hero-title {
                font-size: 2.25rem;
                font-weight: 800;
                color: #2563eb;
                letter-spacing: -1px;
                margin-bottom: 0.6rem;
                background: linear-gradient(90deg,#2563eb 20%,#38bdf8 80%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .hero-desc {
                color: #64748b;
                margin-bottom: 2.1rem;
                font-size: 1.13rem;
                font-weight: 400;
            }
            .btn-custom {
                min-width: 210px;
                margin: 0.4rem 0.6rem;
                font-size: 1.11rem;
                border-radius: 1.35rem;
                font-weight: 600;
                box-shadow: 0 2px 12px #2563eb11;
                transition: transform 0.12s, box-shadow 0.15s;
                border: none;
                outline: none;
                position: relative;
                overflow: hidden;
            }
            .btn-custom:active {
                transform: scale(0.97);
                box-shadow: 0 1px 4px #2563eb22;
            }
            .btn-primary {
                background: linear-gradient(90deg,#6366f1 0,#38bdf8 100%)!important;
                color: #fff!important;
            }
            .btn-primary:hover {
                background: linear-gradient(90deg,#38bdf8 0,#6366f1 100%)!important;
            }
            .btn-outline-secondary {
                background: #fff!important;
                color: #6366f1!important;
                border: 2px solid #6366f1!important;
            }
            .btn-outline-secondary:hover {
                background: #6366f1!important;
                color: #fff!important;
            }
            .btn-success {
                background: linear-gradient(90deg,#22d3ee 0,#2563eb 100%)!important;
                border: 0;
                color: #fff!important;
            }
            .btn-success:hover {
                background: linear-gradient(90deg,#2563eb 0,#22d3ee 100%)!important;
            }
            .result-box {
                margin-top: 2.1rem;
                font-size: 1.13rem;
                min-height: 32px;
            }
            .rocket {
                margin-bottom: 1.3rem;
                filter: drop-shadow(0 2px 16px #38bdf822);
                width: 62px;
                will-change: transform;
                animation: rocket-float 2.5s ease-in-out infinite;
                transition: filter 0.5s;
            }
            .rocket:hover {
                filter: drop-shadow(0 4px 32px #6366f199) hue-rotate(30deg) saturate(1.5);
                animation: rocket-spin 1.2s cubic-bezier(.4,2,.6,1) infinite alternate;
            }
            @keyframes rocket-float {
                0%,100% { transform: translateY(0) rotate(-6deg); }
                50% { transform: translateY(-18px) rotate(8deg); }
            }
            @keyframes rocket-spin {
                0% { transform: scale(1.13) rotate(-10deg); }
                100% { transform: scale(1.13) rotate(370deg); }
            }
            @keyframes hero-in {
                to { opacity: 1; transform: scale(1) translateY(0); }
            }
        </style>
    </head>
    <body>
        <div class='hero'>
            <img class='rocket' src='https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f680.svg' alt='rocket' />
            <div class='hero-title'>FastAPI Email Scraper</div>
            <div class='hero-desc'>API profesional y minimalista para extracción de correos electrónicos.<br>Con autenticación y scraping avanzado.</div>
            <div class='d-flex flex-column align-items-center mb-2'>
                <a href='/docs' class='btn btn-primary btn-lg btn-custom mb-2'>📑 Documentación</a>
                <a href='/redoc' class='btn btn-outline-secondary btn-lg btn-custom mb-2'>📘 ReDoc</a>
                <button id='db-test-btn' class='btn btn-success btn-lg btn-custom mb-2'>🔌 Probar conexión</button>
            </div>
            <div id='db-result' class='result-box'></div>
        </div>
        <script>
            // Fondo animado exótico
            let angle = 120;
            setInterval(() => {
                angle = (angle + 0.18) % 360;
                document.body.style.background = `linear-gradient(${angle}deg,#e0e7ff 0%,#f0fdfa 100%)`;
            }, 30);
            // Botones con brillo y rebote
            document.querySelectorAll('.btn-custom').forEach(btn => {
                btn.addEventListener('mouseenter', e => {
                    btn.style.boxShadow = '0 0 0 7px #38bdf866, 0 2px 12px #2563eb22';
                    btn.style.transform = 'scale(1.09)';
                });
                btn.addEventListener('mouseleave', e => {
                    btn.style.boxShadow = '0 2px 12px #2563eb11';
                    btn.style.transform = 'scale(1)';
                });
            });
            // Test conexión
            const dbBtn = document.getElementById('db-test-btn');
            const result = document.getElementById('db-result');
            dbBtn.addEventListener('click', async () => {
                result.innerHTML = '<span class="text-secondary">Conectando a la base de datos...</span>';
                try {
                    const res = await fetch('/health');
                    if (!res.ok) throw new Error('Error de conexión');
                    const data = await res.json();
                    if (data.status === 'ok') {
                        result.innerHTML = '<span class="text-success fw-bold">✅ ¡Conexión exitosa a PostgreSQL!</span>';
                    } else {
                        result.innerHTML = '<span class="text-warning fw-bold">⚠️ La conexión responde pero no es exitosa.</span>';
                    }
                } catch (err) {
                    result.innerHTML = '<span class="text-danger fw-bold">❌ Error al conectar con la base de datos.</span>';
                }
            });
        </script>
    </body>
    </html>
    """

# Definir custom_openapi después de crear app

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["servers"] = [
        {"url": "https://web-scraping-backend-hlmu.onrender.com", "description": "Servidor de producción"},
        {"url": "http://localhost:8000", "description": "Servidor local de desarrollo"}
    ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Limpieza de entradas antiguas en caché
async def cleanup_old_entries(current_request_id: str, max_age_hours: int = 1):
    """Elimina entradas antiguas de la caché"""
    await asyncio.sleep(3600 * max_age_hours)  # Esperar el tiempo especificado
    current_time = datetime.now()
    
    for req_id in list(result_cache.keys()):
        if req_id == current_request_id:
            continue
            
        entry_time = datetime.fromisoformat(result_cache[req_id]["timestamp"])
        if (current_time - entry_time).total_seconds() > (3600 * max_age_hours):
            del result_cache[req_id]
            logger.debug(f"Eliminada entrada antigua de caché: {req_id}")


load_dotenv()


ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://web-scraping-backend-hlmu.onrender.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


result_cache: Dict[str, Dict[str, Any]] = {}

class ScrapeRequest(BaseModel):
    """Modelo para la solicitud de escaneo"""
    url: HttpUrl = Field(..., description="URL del sitio web a escanear (ej: https://ejemplo.com)")
    max_pages: int = Field(10, ge=1, le=50, description="Número máximo de páginas a escanear")
    max_emails: int = Field(50, ge=1, le=200, description="Número máximo de correos a encontrar")
    include_paths: Optional[List[str]] = Field(None, description="Rutas específicas a incluir (ej: /contacto, /about)")
    exclude_domains: Optional[List[str]] = Field(None, description="Dominios a excluir (ej: google.com, facebook.com)")
    timeout: int = Field(30, ge=5, le=120, description="Tiempo máximo de escaneo en segundos")
    max_depth: int = Field(2, ge=1, le=5, description="Profundidad máxima de navegación (niveles)")

class ScrapeResponse(BaseModel):
    """Modelo para la respuesta del escaneo"""
    request_id: str = Field(..., description="ID único de la solicitud")
    status: str = Field(..., description="Estado del escaneo (processing|completed|failed)")
    url: str = Field(..., description="URL escaneada")
    emails: Optional[List[str]] = Field(None, description="Lista de correos encontrados")
    pages_scanned: int = Field(0, description="Número de páginas escaneadas")
    emails_found: int = Field(0, description="Número de correos encontrados")
    error: Optional[str] = Field(None, description="Mensaje de error en caso de fallo")
    timestamp: str = Field(..., description="Fecha y hora de la respuesta")

class EmailScraper:
    """Clase para realizar el escaneo de correos electrónicos"""
    
    def __init__(self, max_workers: int = 5):
        self.session = None
        self.semaphore = asyncio.Semaphore(max_workers)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Inicializar atributos adicionales
        self.visited_urls = set()
        self.emails = set()
        self.queue = None
        self.max_pages = 10
        self.max_emails = 50
        self.include_paths = set()
        self.exclude_domains = set()
        self.max_depth = 3
        self.base_domain = ""
    
    async def __aenter__(self):
        # Configuración mejorada de la sesión HTTP
        timeout = aiohttp.ClientTimeout(
            total=30,  # Tiempo total de espera
            connect=10,  # Tiempo para conectar
            sock_connect=10,  # Tiempo para conectar el socket
            sock_read=10  # Tiempo para leer del socket
        )
        
        # Configuración de la sesión con soporte para compresión
        connector = aiohttp.TCPConnector(
            limit=100,  # Número máximo de conexiones
            force_close=True,
            enable_cleanup_closed=True,
            ssl=False  # Desactivar verificación SSL
        )
        
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=timeout,
            connector=connector,
            trust_env=True,  # Usar configuraciones de proxy del sistema
            auto_decompress=True  # Manejar automáticamente la compresión
        )
        
        # Añadir encabezados de aceptación de compresión
        self.session.headers.update({
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()
            
    async def extract_text_from_image(self, image_url: str) -> Optional[str]:
        """
        Extrae texto de una imagen usando OCR (Reconocimiento Óptico de Caracteres)
        """
        try:
            # Configurar la ruta exacta de Tesseract encontrada en el sistema
            import platform, os
            system_type = platform.system()
            if system_type == "Windows":
                tesseract_path = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
            else:
                tesseract_path = '/usr/bin/tesseract'
            logger.info(f"[OCR] platform.system() = {system_type}, usando tesseract_path = {tesseract_path}")
            if system_type != "Windows" and not os.path.exists(tesseract_path):
                logger.error(f"[OCR] Tesseract no está instalado en {tesseract_path}. Instálalo con 'apt-get install tesseract-ocr'")
                return None
            try:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                # Verificar que Tesseract funciona
                pytesseract.get_tesseract_version()
            except Exception as e:
                logger.error(f"Error al inicializar Tesseract en {tesseract_path}: {str(e)}")
                return None
            
            # Validar si la imagen es una ruta local y existe
            from urllib.parse import urlparse
            parsed = urlparse(image_url)
            if not parsed.scheme or parsed.scheme == 'file':
                # Es ruta local
                if not os.path.exists(image_url):
                    logger.warning(f"[OCR] Imagen local no encontrada: {image_url}")
                    return None
            # Descargar la imagen
            async with self.session.get(image_url, timeout=10) as response:
                if response.status != 200:
                    return None
                    
                image_data = await response.read()
                
                # Verificar si es una imagen
                if not image_data.startswith(b'\xff\xd8') and not image_data.startswith(b'\x89PNG'):
                    return None
                
                try:
                    # Procesar la imagen con PIL
                    image = Image.open(BytesIO(image_data))
                    
                    # Convertir a escala de grises para mejor OCR
                    if image.mode != 'L':
                        image = image.convert('L')
                    
                    # Mejorar el contraste para mejor reconocimiento
                    from PIL import ImageEnhance
                    enhancer = ImageEnhance.Contrast(image)
                    image = enhancer.enhance(2.0)  # Aumentar contraste
                    
                    # Extraer texto en inglés (cambiar a 'spa' una vez instalado el paquete de idioma español)
                    text = pytesseract.image_to_string(image, lang='eng')
                    
                    # Limpiar y devolver solo líneas con @ (posibles correos)
                    email_lines = [line.strip() for line in text.split('\n') if '@' in line]
                    
                    return '\n'.join(email_lines) if email_lines else None
                    
                except Exception as img_error:
                    logger.warning(f"Error al procesar imagen {image_url}: {str(img_error)}")
                    return None
                
        except Exception as e:
            logger.warning(f"Error al procesar imagen {image_url}: {str(e)}")
            return None
    
    def is_valid_email(self, email: str) -> bool:
        """Verifica si un correo electrónico es válido"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    async def extract_emails_from_page(self, content: str, base_url: str) -> Set[str]:
        """
        Extrae correos electrónicos de una página web, incluyendo aquellos en imágenes
        """
        emails = set()
        soup = BeautifulSoup(content, 'html.parser')
        
        # 1. Extraer correos del texto de la página
        text = soup.get_text()
        email_pattern = r'\b(?!.*\.(?:png|jpg|jpeg|gif|webp|svg|ico))[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        text_emails = re.findall(email_pattern, text, re.IGNORECASE)
        
        # 2. Extraer correos de atributos que puedan contener correos
        attr_emails = set()
        for tag in soup.find_all(True):  # Buscar en todos los tags
            for attr in ['href', 'data-email', 'data-contact', 'data-mail', 'data-email-address']:
                if attr in tag.attrs and '@' in tag[attr]:
                    # Extraer correos de atributos como mailto: o data-email
                    attr_value = tag[attr]
                    if attr == 'href' and attr_value.startswith('mailto:'):
                        email = attr_value[7:].split('?')[0]  # Eliminar 'mailto:' y parámetros
                        attr_emails.add(email.strip())
                    elif '@' in attr_value:
                        # Buscar correos en otros atributos
                        found_emails = re.findall(email_pattern, attr_value, re.IGNORECASE)
                        attr_emails.update(found_emails)
        
        # 3. Buscar correos en imágenes (solo si es necesario)
        image_emails = set()
        if len(emails) < 5:  # Solo buscar en imágenes si no encontramos suficientes correos
            for img in soup.find_all('img'):
                img_src = img.get('src')
                if img_src:
                    # Construir URL completa
                    if img_src.startswith('//'):
                        img_url = 'https:' + img_src
                    elif img_src.startswith('/'):
                        img_url = urljoin(base_url, img_src)
                    else:
                        img_url = img_src
                    
                    # Verificar si la imagen podría contener un correo (por nombre de archivo)
                    if any(term in img_src.lower() for term in ['email', 'mail', 'contact', 'correo']):
                        try:
                            img_text = await self.extract_text_from_image(img_url)
                            if img_text:
                                found_emails = re.findall(email_pattern, img_text, re.IGNORECASE)
                                image_emails.update(found_emails)
                        except Exception as e:
                            logger.warning(f"Error al procesar imagen {img_url}: {str(e)}")
        
        # Combinar todos los correos encontrados
        all_emails = set(text_emails) | attr_emails | image_emails
        
        # Filtrar y validar correos
        filtered_emails = set()
        for email in all_emails:
            email = email.lower().strip()
            if (self.is_valid_email(email) and
                len(email) > 5 and
                not email.split('@')[0].isdigit() and
                not any(ext in email.split('@')[0].lower() for ext in ['icon', 'logo', 'image', 'img', 'sprite']) and
                not any(ext in email.split('@')[1].split('.')[0].lower() for ext in ['cdn', 'static', 'assets', 'media', 'images', 'img', 'js', 'css', 'fonts']) and
                '.' in email.split('@')[1]):
                filtered_emails.add(email)
        
        return filtered_emails
    
    async def get_page_content(self, url: str) -> Optional[str]:
        """
        Obtiene el contenido de una página web de forma asíncrona con manejo mejorado de errores
        """
        if not self.session:
            logger.warning(f"Sesión no inicializada para {url}")
            return None
            
        try:
            start_time = time.time()
            logger.debug(f"Solicitando URL: {url}")
            
            async with self.semaphore:
                # Headers mejorados para parecer un navegador real
                headers = {
                    **self.headers,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0',
                    'DNT': '1',
                    'Referer': 'https://www.google.com/'
                }
                
                # Configuración de tiempo de espera
                timeout = aiohttp.ClientTimeout(total=15, connect=10, sock_connect=10, sock_read=10)
                
                try:
                    async with self.session.get(
                        url, 
                        headers=headers, 
                        allow_redirects=True, 
                        timeout=timeout,
                        ssl=False  # Desactivar verificación SSL para evitar problemas de certificado
                    ) as response:
                        # Verificar el código de estado
                        if response.status != 200:
                            logger.warning(f"Error HTTP {response.status} al obtener {url}")
                            return None
                        
                        # Verificar el tipo de contenido
                        content_type = response.headers.get('Content-Type', '').lower()
                        if 'text/html' not in content_type:
                            logger.warning(f"Tipo de contenido no soportado en {url}: {content_type}")
                            return None
                        
                        # Obtener el contenido con un timeout específico
                        try:
                            content = await asyncio.wait_for(response.text(), timeout=10)
                            load_time = time.time() - start_time
                            logger.debug(f"Página cargada: {url} en {load_time:.2f}s")
                            return content
                            
                        except asyncio.TimeoutError:
                            logger.warning(f"Timeout al leer el contenido de {url}")
                            return None
                            
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout al conectar a {url}")
                    return None
                    
                except aiohttp.ClientError as e:
                    logger.warning(f"Error de cliente al acceder a {url}: {str(e)}")
                    return None
                    
                except Exception as e:
                    logger.error(f"Error inesperado al procesar {url}: {str(e)}", exc_info=True)
                    return None
        
        except Exception as e:
            logger.error(f"Error crítico en get_page_content para {url}: {str(e)}", exc_info=True)
            
        return None
    
    async def scrape_website(self, url: str, max_pages: int = 10, max_emails: int = 50, 
                          include_paths: List[str] = None, exclude_domains: List[str] = None,
                          max_depth: int = 3, timeout: int = 300) -> Dict[str, Any]:
        """
        Función principal que coordina el scraping de un sitio web
        
        Args:
            url: URL inicial para comenzar el scraping
            max_pages: Número máximo de páginas a escanear
            max_emails: Número máximo de correos a recolectar
            include_paths: Lista de rutas a incluir (opcional)
            exclude_domains: Lista de dominios a excluir (opcional)
            max_depth: Profundidad máxima de navegación
            timeout: Tiempo máximo en segundos para el escaneo
            
        Returns:
            Dict con los resultados del scraping
        """
        start_time = time.time()
        self.visited_urls = set()
        self.emails = set()
        self.queue = asyncio.Queue()
        self.max_pages = max_pages
        self.max_emails = max_emails
        self.include_paths = set(include_paths or [])
        self.exclude_domains = set(exclude_domains or [])
        self.max_depth = max_depth
        
        try:
            # Configurar el timeout global
            async def scrape_main():
                # Asegurarse de que la URL base esté en la cola
                parsed_url = urlparse(url)
                self.base_domain = parsed_url.netloc
                await self.queue.put((url, 0))  # (url, profundidad)
                
                # Procesar la cola con múltiples workers
                workers = []
                num_workers = min(5, max_pages)  # No más workers que páginas máximas
                
                logger.info(f"Iniciando scraping de {url} con {num_workers} trabajadores")
                
                # Iniciar workers
                for _ in range(num_workers):
                    worker = asyncio.create_task(self.worker())
                    workers.append(worker)
                
                # Esperar a que se completen todas las tareas o se alcance el límite
                try:
                    await self.queue.join()
                except asyncio.CancelledError:
                    pass
                finally:
                    for w in workers:
                        w.cancel()
                    await asyncio.gather(*workers, return_exceptions=True)

                logger.info(f"Finalizado scraping de {url}. "
                            f"Páginas: {len(self.visited_urls)}, "
                            f"Correos: {len(self.emails)}")
                return {
                    "url": url,
                    "emails": list(self.emails)[:max_emails],  # Limitar al máximo solicitado
                    "pages_scanned": len(self.visited_urls),
                    "emails_found": min(len(self.emails), max_emails),
                    "execution_time_seconds": round(time.time() - start_time, 2)
                }

            result = await asyncio.wait_for(scrape_main(), timeout)
            return result

                
        except asyncio.TimeoutError:
            logger.warning(f"Tiempo de espera agotado ({timeout}s) para el escaneo de {url}")
            return {
                "url": url,
                "emails": list(self.emails)[:max_emails],
                "pages_scanned": len(self.visited_urls),
                "emails_found": min(len(self.emails), max_emails),
                "error": f"Tiempo de espera agotado ({timeout}s)",
                "execution_time_seconds": round(time.time() - start_time, 2)
            }
            
        except Exception as e:
            logger.error(f"Error en scrape_website para {url}: {str(e)}", exc_info=True)
            return {
                "url": url,
                "emails": list(self.emails)[:max_emails],
                "pages_scanned": len(self.visited_urls),
                "emails_found": min(len(self.emails), max_emails),
                "error": str(e),
                "execution_time_seconds": round(time.time() - start_time, 2)
            }
    
    async def worker(self):
        while True:
            url, depth = await self.queue.get()
            if url in self.visited_urls:
                self.queue.task_done()
                continue
            
            if depth > self.max_depth:
                self.queue.task_done()
                continue
            
            try:
                content = await self.get_page_content(url)
                if not content:
                    self.queue.task_done()
                    continue
                
                # Extraer correos de la página actual
                page_emails = await self.extract_emails_from_page(content, url)
                if page_emails:
                    logger.info(f"Encontrados {len(page_emails)} correos en {url}")
                    self.emails.update(page_emails)
                
                # Si ya alcanzamos el máximo de correos, detenemos
                if len(self.emails) >= self.max_emails:
                    self.queue.task_done()
                    continue
                
                # Procesar enlaces
                soup = BeautifulSoup(content, 'html.parser')
                links_found = 0
                
                # Buscar enlaces en elementos comunes que suelen contener información de contacto
                contact_links = []
                for link in soup.find_all(['a', 'link'], href=True):
                    href = link.get('href', '').strip()
                    if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                        continue
                        
                    # Construir URL completa
                    if href.startswith('//'):
                        full_url = 'https:' + href if url.startswith('https:') else 'http:' + href
                    elif href.startswith('/'):
                        full_url = urljoin(url, href)
                    else:
                        full_url = href
                    
                    # Priorizar enlaces de contacto
                    link_text = (link.get_text() or '').lower()
                    if any(term in link_text for term in ['contact', 'contacto', 'about', 'nosotros', 'equipo', 'team']):
                        contact_links.insert(0, full_url)  # Añadir al principio
                    else:
                        contact_links.append(full_url)
                
                # Procesar primero los enlaces de contacto
                for link_url in contact_links:
                    if len(self.visited_urls) >= self.max_pages or len(self.emails) >= self.max_emails:
                        break
                    
                    try:
                        parsed_url = urlparse(link_url)
                        
                        # Validar dominio y rutas
                        if (parsed_url.netloc == self.base_domain and 
                            link_url not in self.visited_urls and
                            not any(exclude in link_url.lower() for exclude in self.exclude_domains) and
                            not any(ext in link_url.lower() 
                                  for ext in ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', 
                                             '.mp4', '.mp3', '.css', '.js', '.svg', '.ico', '.woff', '.ttf', '.eot'])):
                            
                            links_found += 1
                            if links_found > 50:  # Límite de enlaces por página
                                break
                                
                            await self.queue.put((link_url, depth + 1))
                    except Exception as e:
                        logger.warning(f"Error al procesar enlace {link_url}: {str(e)}")
                        continue
                
                self.visited_urls.add(url)
                self.queue.task_done()
            
            except Exception as e:
                logger.error(f"Error al procesar {url}: {str(e)}", exc_info=True)
                self.queue.task_done()
    
    async def _process_page(self, url: str, base_domain: str, visited: set, emails: set, 
                          max_pages: int, max_emails: int, depth: int, max_depth: int,
                          exclude_domains: List[str] = None) -> None:
        """Procesa una página y sus enlaces de forma recursiva"""
        if (len(visited) >= max_pages or len(emails) >= max_emails or 
            url in visited or depth > max_depth or not url):
            return
        
        visited.add(url)
        logger.info(f"Analizando página: {url}")
        
        try:
            content = await self.get_page_content(url)
            if not content:
                return
            
            # Extraer correos de la página actual
            page_emails = self.extract_emails_from_text(content)
            if page_emails:
                logger.info(f"Encontrados {len(page_emails)} correos en {url}")
                emails.update(page_emails)
            
            # Si ya alcanzamos el máximo de correos, detenemos
            if len(emails) >= max_emails:
                return
            
            # Procesar enlaces
            if depth < max_depth:
                soup = BeautifulSoup(content, 'html.parser')
                tasks = []
                links_found = 0
                
                # Buscar enlaces en elementos comunes que suelen contener información de contacto
                contact_links = []
                for link in soup.find_all(['a', 'link'], href=True):
                    href = link['href'].strip()
                    if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                        continue
                        
                    # Priorizar enlaces de contacto
                    link_text = (link.get_text() or '').lower()
                    if any(term in link_text for term in ['contact', 'contacto', 'about', 'nosotros', 'equipo', 'team']):
                        contact_links.insert(0, href)  # Añadir al principio
                    else:
                        contact_links.append(href)
                
                # Procesar primero los enlaces de contacto
                for href in contact_links:
                    if len(visited) >= max_pages or len(emails) >= max_emails:
                        break
                        
                    full_url = urljoin(url, href)
                    parsed_url = urlparse(full_url)
                    
                    # Validar dominio y rutas
                    if (parsed_url.netloc == base_domain and 
                        full_url not in visited and
                        not any(exclude in full_url.lower() for exclude in (exclude_domains or [])) and
                        not any(ext in full_url.lower() 
                              for ext in ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', 
                                         '.mp4', '.mp3', '.css', '.js', '.svg'])):
                        
                        links_found += 1
                        if links_found > 50:  # Límite de enlaces por página
                            break
                            
                        tasks.append(self._process_page(
                            full_url, base_domain, visited, emails, 
                            max_pages, max_emails, depth + 1, max_depth, exclude_domains
                        ))
                
                # Procesar enlaces en paralelo en lotes
                if tasks:
                    batch_size = 5  # Procesar 5 enlaces a la vez
                    for i in range(0, len(tasks), batch_size):
                        batch = tasks[i:i + batch_size]
                        # Crear tareas y esperar a que todas terminen
                        await asyncio.gather(
                            *[asyncio.create_task(task) for task in batch],
                            return_exceptions=True
                        )
                        
                        # Verificar si debemos detener el procesamiento
                        if len(emails) >= max_emails or len(visited) >= max_pages:
                            break
                            
        except Exception as e:
            logger.error(f"Error al procesar {url}: {str(e)}", exc_info=True)

# Include auth router
app.include_router(auth.router)

# Ruta raíz

# Rutas de la API
from app.auth import get_current_active_user
from fastapi import Depends
from app.db import get_pg_pool

@app.post("/api/v1/scrape", response_model=ScrapeResponse, tags=["Scraping"])
async def scrape_website(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks
):
    """
    Inicia un nuevo trabajo de escaneo de correos electrónicos.
    
    Esta ruta inicia el proceso de escaneo en segundo plano y devuelve inmediatamente
    un ID de solicitud que puede usarse para verificar el estado.
    """
    request_id = f"req_{int(time.time())}_{os.urandom(4).hex()}"
    
    # Inicializar el resultado en caché con todos los campos necesarios
    result_cache[request_id] = {
        "status": "processing",
        "url": str(request.url),
        "emails": [],
        "pages_scanned": 0,
        "emails_found": 0,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "error": None,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Ejecutar el scraper en segundo plano usando asyncio.create_task
    asyncio.create_task(
        run_scraper(
            request_id=request_id,
            url=str(request.url),
            max_pages=request.max_pages,
            max_emails=request.max_emails,
            include_paths=request.include_paths,
            exclude_domains=request.exclude_domains,
            max_depth=request.max_depth,
            timeout=request.timeout  # Usar el timeout definido en la solicitud
        )
    )
    
    return {
        "request_id": request_id,
        "status": "processing",
        "url": str(request.url),
        "pages_scanned": 0,
        "emails_found": 0,
        "timestamp": datetime.utcnow().isoformat(),
        "message": "El escaneo ha comenzado. Utiliza el request_id para verificar el estado."
    }

@app.get("/api/v1/status/{request_id}", response_model=ScrapeResponse, tags=["Estado"])
async def check_status(request_id: str):
    """
    Verifica el estado de un trabajo de escaneo.
    
    Utiliza el request_id devuelto por la ruta /scrape para obtener
    el estado actual y los resultados si están disponibles.
    """
    if request_id not in result_cache:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    result = result_cache[request_id]
    
    response = {
        "request_id": request_id,
        "status": result["status"],
        "url": result["url"],
        "emails": result["emails"] if result["status"] == "completed" else None,
        "pages_scanned": result["pages_scanned"],
        "emails_found": result["emails_found"],
        "timestamp": result["timestamp"]
    }
    
    if result["error"]:
        response["error"] = result["error"]
    
    return response

@app.get("/api/v1/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/api/v1/openapi.json",
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://unpkg.com/swagger-ui-dist@4/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@4/swagger-ui.css",
    )

@app.get("/api/v1/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    return JSONResponse(
        get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )
    )

# Tarea en segundo plano para el escaneo
async def run_scraper(request_id: str, url: str, max_pages: int, max_emails: int, 
                     include_paths: List[str] = None, exclude_domains: List[str] = None,
                     max_depth: int = 3, timeout: int = 300, user_id: str = None):
    """
    Función para ejecutar el scraper en segundo plano con timeout
    
    Args:
        timeout: Tiempo máximo en segundos para el escaneo (5 minutos por defecto)
    """
    start_time = time.time()
    
    try:
        # Configurar el timeout usando asyncio.wait_for
        async def scrape_task():
            async with EmailScraper() as scraper:
                logger.info(f"Iniciando escaneo de {url} (timeout: {timeout}s)")
                result = await scraper.scrape_website(
                    url=url,
                    max_pages=max_pages,
                    max_emails=max_emails,
                    include_paths=include_paths or [],
                    exclude_domains=exclude_domains or [],
                    max_depth=max_depth
                )
                # Actualizar caché con resultados
                emails_list = list(result.get("emails", set()))
                exec_time = time.time() - start_time
                result_cache[request_id].update({
                    "status": "completed",
                    "emails": emails_list,
                    "pages_scanned": result.get("pages_scanned", 0),
                    "emails_found": len(emails_list),
                    "execution_time_seconds": round(exec_time, 2),
                    "completed_at": datetime.utcnow().isoformat(),
                    "timestamp": datetime.utcnow().isoformat()
                })
                logger.info(f"Finalizado scraping de {url} en {exec_time:.2f}s. "
                            f"Páginas: {result.get('pages_scanned', 0)}, "
                            f"Correos: {len(emails_list)}")

                # Guardar en la base de datos solo si hay correos encontrados
                if emails_list:
                    try:
                        pool = await get_pg_pool()
                        async with pool.acquire() as conn:
                            # Buscar los correos que ya existen
                            rows = await conn.fetch(
                                """
                                SELECT email FROM found_emails WHERE user_id IS NULL AND url = $1 AND email = ANY($2::text[])
                                """,
                                url, emails_list
                            )
                            existentes = {row['email'] for row in rows}
                            nuevos = [email for email in emails_list if email not in existentes]
                            if nuevos:
                                await conn.executemany(
                                    """
                                    INSERT INTO found_emails (user_id, email, url, found_at)
                                    VALUES (NULL, $1, $2, NOW())
                                    ON CONFLICT (email, url, user_id) DO NOTHING
                                    """,
                                    [(email, url) for email in nuevos]
                                )
                                logger.info(f"Se guardaron {len(nuevos)} correos anónimos en la base de datos.")
                                result_cache[request_id]["message"] = f"Correos almacenados exitosamente. Se insertaron los siguientes correos: {', '.join(nuevos)}"
                            else:
                                logger.info("No hay correos nuevos para insertar.")
                                result_cache[request_id]["message"] = "No hay correos nuevos para insertar."
                    except Exception as db_err:
                        logger.error(f"Error guardando correos en la base de datos: {db_err}")

        await asyncio.wait_for(scrape_task(), timeout=timeout)

    except asyncio.TimeoutError:
        error_msg = f"Tiempo de espera agotado ({timeout}s) para el escaneo de {url}"
        logger.error(error_msg)
        result_cache[request_id].update({
            "status": "error",
            "error": error_msg,
            "execution_time_seconds": time.time() - start_time,
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        error_msg = f"Error en scraper para {url}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        result_cache[request_id].update({
            "status": "error",
            "error": error_msg,
            "execution_time_seconds": time.time() - start_time,
            "timestamp": datetime.utcnow().isoformat()
        })
    finally:
        # Limpiar caché después de 1 hora
        asyncio.create_task(cleanup_old_entries(request_id))

# Ruta de verificación de estado
@app.get("/health", tags=["Estado"])
async def health_check():
    """Verifica el estado del servicio"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

# Limpiar caché de resultados antiguos periódicamente
async def cleanup_old_results():
    """Limpia resultados antiguos de la caché"""
    while True:
        await asyncio.sleep(3600)  # Cada hora
        now = time.time()
        old_keys = []
        
        for req_id, result in result_cache.items():
            completed_at = result.get("completed_at")
            if completed_at:
                completed_ts = datetime.fromisoformat(completed_at).timestamp()
                if now - completed_ts > 86400:  # 24 horas
                    old_keys.append(req_id)
        
        for req_id in old_keys:
            result_cache.pop(req_id, None)

# Iniciar tarea de limpieza al arrancar
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_old_results())

# Si se ejecuta directamente
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
