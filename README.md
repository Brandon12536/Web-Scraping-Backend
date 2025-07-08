# 🚀 FastAPI Email Scraper

API de alto rendimiento para extracción de correos electrónicos de sitios web, construida con FastAPI y asyncio.

## 🛠️ Tecnologías Principales

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white&style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white&style=for-the-badge)
![aiohttp](https://img.shields.io/badge/aiohttp-2C5BB4?logo=aiohttp&logoColor=white&style=for-the-badge)
![BeautifulSoup](https://img.shields.io/badge/Beautiful_Soup-FF6B6B?logo=beautifulsoup&logoColor=white&style=for-the-badge)
![Pillow](https://img.shields.io/badge/Pillow-8A2BE2?logo=pillow&logoColor=white&style=for-the-badge)
![Tesseract](https://img.shields.io/badge/Tesseract-4285F4?logo=tesseract&logoColor=white&style=for-the-badge)
![Pydantic](https://img.shields.io/badge/Pydantic-9209B3?logo=pydantic&logoColor=white&style=for-the-badge)
![Asyncio](https://img.shields.io/badge/Asyncio-00A98F?logo=asyncio&logoColor=white&style=for-the-badge)

## 🚀 Características

- Escaneo rápido y concurrente
- Documentación interactiva con Swagger UI
- Límites personalizables (páginas, correos, tiempo de espera)
- Filtrado de dominios y rutas
- Cache de resultados
- Tareas en segundo plano
- Compatible con CORS

## 🛠️ Requisitos

- Python 3.8+
- pip

## 🚀 Instalación

1. Clona el repositorio:
   ```bash
   git clone [tu-repositorio]
   cd fastapi-scraper
   ```

2. Crea y activa un entorno virtual:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Instala las dependencias:
   ```bash
   # Instala todas las dependencias listadas en requirements.txt
   pip install -r requirements.txt
   
   # Si el comando anterior falla, intenta con pip3:
   # pip3 install -r requirements.txt
   ```

   > 💡 **Nota sobre requirements.txt**
   > El archivo `requirements.txt` contiene todas las dependencias necesarias para ejecutar la aplicación. 
   > Este comando instalará automáticamente las versiones específicas de cada paquete que se especifican en el archivo.
   > 
   > Si necesitas actualizar el archivo `requirements.txt` después de instalar nuevos paquetes, usa:
   > ```bash
   > pip freeze > requirements.txt
   > ```

## 🚦 Uso

1. Inicia el servidor:
   ```bash
   uvicorn app.main:app --reload
   ```

2. Abre tu navegador en:
   ```
   http://127.0.0.1:8000/api/v1/docs
   ```

## 📚 Documentación de la API

### 1. Iniciar escaneo

**Endpoint:** `POST /api/v1/scrape`

**Cuerpo de la solicitud (JSON):**
```json
{
  "url": "https://ejemplo.com",
  "max_pages": 10,
  "max_emails": 50,
  "include_paths": ["/contacto", "/about"],
  "exclude_domains": ["google.com"],
  "timeout": 30
}
```

**Respuesta exitosa (202):**
```json
{
  "request_id": "req_1624579200_1a2b3c4d",
  "status": "processing",
  "url": "https://ejemplo.com",
  "pages_scanned": 0,
  "emails_found": 0,
  "timestamp": "2025-06-24T18:00:00.000Z",
  "message": "El escaneo ha comenzado. Utiliza el request_id para verificar el estado."
}
```

### 2. Verificar estado

**Endpoint:** `GET /api/v1/status/{request_id}`

**Respuesta exitosa (200):**
```json
{
  "request_id": "req_1624579200_1a2b3c4d",
  "status": "completed",
  "url": "https://ejemplo.com",
  "emails": ["contacto@ejemplo.com", "info@ejemplo.com"],
  "pages_scanned": 5,
  "emails_found": 2,
  "timestamp": "2025-06-24T18:00:30.000Z"
}
```

## 🌐 Despliegue

### Render.com (Recomendado)

1. Crea una nueva instancia de Web Service
2. Conecta tu repositorio de GitHub
3. Configura las variables de entorno si es necesario
4. Establece el comando de inicio:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

### Railway.app

1. Crea un nuevo proyecto
2. Selecciona "Deploy from GitHub"
3. Configura el puerto en `PORT`

## 🔒 Variables de entorno

| Variable | Descripción | Valor por defecto |
|----------|-------------|------------------|
| `PORT` | Puerto del servidor | `8000` |
| `WORKERS` | Número de workers (para producción) | `4` |
| `LOG_LEVEL` | Nivel de logs | `info` |

## 🧪 Testing

```bash
# Instalar dependencias de desarrollo
pip install pytest httpx

# Ejecutar pruebas
pytest
```

## 🌐 Páginas de Prueba

Aquí tienes algunas páginas útiles para probar el scraper, organizadas por categorías:

### 🔍 Páginas de contacto simples
- [Google Contact](https://about.google/contact-google/)
- [Python Contact](https://www.python.org/about/contact/)
- [Mozilla Contact](https://www.mozilla.org/contact/)

### 🔗 Sitios con múltiples páginas
- [IANA](https://www.iana.org/) - Sitio bien estructurado
- [Craigslist](https://www.craigslist.org/about/sites) - Muchos enlaces
- [Reddit LearnPython](https://www.reddit.com/r/learnpython/) - Contenido dinámico

### 🛡️ Sitios con protección anti-bots
- [LinkedIn Contact](https://www.linkedin.com/contact)
- [Cloudflare](https://www.cloudflare.com/)
- [Airbnb Contact](https://www.airbnb.com/contact)

### 📝 Sitios con formularios de contacto
- [Spotify Contact](https://www.spotify.com/us/contact/)
- [Twitter Forms](https://support.twitter.com/forms)
- [Netflix Contact](https://www.netflix.com/contact)

### 🏢 Sitios con información de contacto en el pie de página
- [Microsoft](https://www.microsoft.com/)
- [Apple Contact](https://www.apple.com/contact/)
- [Adobe Contact](https://www.adobe.com/contact.html)

## 📄 Licencia

![MIT License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)

---

Desarrollado por OSDEMS Digital Group - Brandon Pérez R
