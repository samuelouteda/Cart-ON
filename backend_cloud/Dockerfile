# 1. Usamos una base ligera de Python optimizada para servidores
FROM python:3.11-slim

# 2. Le decimos a Google que trabaje dentro de la carpeta /app
WORKDIR /app

# 3. Copiamos la lista de la compra y descargamos las librerías
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiamos TODOS tus archivos (main.py, HRI.py, etc.) dentro de la caja
COPY . .

# 5. Exponemos el puerto oficial de Cloud Run (8080)
EXPOSE 8080

# 6. El comando que ejecutará Google al encender la máquina
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}