# Usamos una imagen oficial de Python ligera
FROM python:3.10-slim

# Le decimos a Google que trabaje dentro de la carpeta /app
WORKDIR /app

# Copiamos la lista de librerías y las instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el código de tu servidor
COPY . .

# Exponemos el puerto que usa Google Cloud Run por defecto (8080)
EXPOSE 8080

# El comando que arranca FastAPI al encender el servidor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]