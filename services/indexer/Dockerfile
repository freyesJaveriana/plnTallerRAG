# Usar una imagen base de Python oficial
FROM python:3.10-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de dependencias primero
COPY requirements.txt .

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# El comando por defecto se ejecutará cuando corramos el 'docker-compose run'
# Este comando llama al script principal que orquesta la indexación.
CMD ["python", "main_indexer.py"]