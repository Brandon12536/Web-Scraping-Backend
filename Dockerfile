# Usar una imagen base de Python 3.9
FROM python:3.9.18-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Establecer variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Crear directorio para la aplicación
WORKDIR /app

# Copiar requirements primero para aprovechar la caché de Docker
COPY requirements.txt .

# Instalar dependencias de Python
RUN apt-get update && apt-get install -y tesseract-ocr && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el resto de la aplicación
COPY . .

# Puerto expuesto (Render inyecta el puerto real en $PORT, pero Docker necesita un valor fijo)
EXPOSE 8000

# Comando para ejecutar la aplicación (usa shell para que $PORT se expanda)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}