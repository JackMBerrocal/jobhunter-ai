# ==============================================================================
# JobHunter AI - Contenedor 24/7 para Ejecución Continua en la Nube
# Permite correr el agente en Railway, Render, Fly.io, Oracle Cloud o VPS
# sin necesidad de tener tu ordenador encendido.
# ==============================================================================

FROM python:3.12-slim-bookworm

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV HEADLESS=true

# Instalar dependencias del sistema requeridas por Chromium / Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    ca-certificates \
    git \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    fonts-liberation \
    libappindicator3-1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requerimientos e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar navegador Chromium para Playwright
RUN playwright install chromium

# Copiar el código fuente completo
COPY . .

# Crear carpeta de datos persistente
RUN mkdir -p /app/data

# Puerto del servidor
EXPOSE 8000

# Comando de inicio: Uvicorn con el agente autónomo habilitado
CMD ["python", "web_ui/app.py"]
