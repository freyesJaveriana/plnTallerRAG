# Usar una imagen base de Python oficial
FROM python:3.10-slim

# Instala 'curl' para que el healthcheck de Docker pueda funcionar
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*
	
# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de dependencias primero
# Esto aprovecha la caché de capas de Docker
COPY requirements.txt .

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código de la aplicación
COPY . .

# (El CMD se proporciona en el docker-compose.yml)