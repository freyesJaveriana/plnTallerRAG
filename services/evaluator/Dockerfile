# Usamos la misma base de Python que los otros servicios
FROM python:3.10-slim

# Establecemos el directorio de trabajo
WORKDIR /app

# Copiamos primero los requirements e instalamos las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto de los archivos (evaluate.py)
COPY . .

# Comando por defecto (que será ejecutado por 'docker-compose run')
CMD ["python", "evaluate.py"]