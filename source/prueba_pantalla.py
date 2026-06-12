import serial
import time
import json
import cv2
import numpy as np

PUERTO = 'COM3' 
BAUD_RATE = 2000000  # 🚀 Misma velocidad turbo que en C++

# ==========================================
# 1. CREAR UNA IMAGEN DE PRUEBA CON OPENCV
# ==========================================
print("🎨 Generando imagen OpenCV simulada...")

# Lienzo blanco de exactamente 960x540 píxeles
img = np.ones((540, 960), dtype=np.uint8) * 255 

# Simulamos un mapa de Cart-ON dibujando algunas formas geométricas
cv2.rectangle(img, (20, 20), (940, 520), 0, 10)         # Marco negro
cv2.circle(img, (480, 270), 150, 100, -1)               # Círculo gris oscuro
cv2.putText(img, "MAPA DE AULAS", (250, 150), cv2.FONT_HERSHEY_SIMPLEX, 2, 0, 5)
cv2.putText(img, "[ SIMULACION QR ]", (600, 450), cv2.FONT_HERSHEY_SIMPLEX, 1, 50, 3)

# ==========================================
# 2. TRANSFORMACIÓN MATEMÁTICA A 4-BIT
# ==========================================
# OpenCV va de 0 a 255. La LilyGO va de 0 a 15. Lo dividimos entre 16.
img_16_tonos = (img // 16).astype(np.uint8)

# Cortamos la imagen en columnas pares e impares
pixeles_izquierdos = img_16_tonos[:, 0::2]
pixeles_derechos = img_16_tonos[:, 1::2]

# Aplastamos dos píxeles en un solo byte (Bitwise Left Shift)
imagen_empaquetada = (pixeles_izquierdos << 4) | pixeles_derechos

# Lo convertimos a un bloque binario crudo
datos_binarios = imagen_empaquetada.tobytes()

# ==========================================
# 3. ENVÍO POR EL CABLE (PROTOCOLO PING-PONG)
# ==========================================
try:
    print(f"🔌 Conectando a {PUERTO} a {BAUD_RATE} baudios...")
    conexion = serial.Serial()
    conexion.port = PUERTO
    conexion.baudrate = BAUD_RATE
    conexion.timeout = 8
    conexion.setDTR(False)
    conexion.setRTS(False)
    conexion.open()
    
    # 🧹 LA MAGIA: Limpiamos la tubería de basura anterior
    conexion.reset_input_buffer()
    conexion.reset_output_buffer()
    
    time.sleep(1)

    print("📢 Avisando a la LilyGO...")
    cabecera_json = json.dumps({"type": "image"}) + "\n"
    conexion.write(cabecera_json.encode('utf-8'))
    
    # Leemos la respuesta limpia
    respuesta = conexion.readline().decode('utf-8').strip()
    
    if "READY" in respuesta:
        print(f"🚀 Pantalla lista. Inyectando {len(datos_binarios) // 1024} KB...")
        
        tamano_bloque = 4096
        
        for i in range(0, len(datos_binarios), tamano_bloque):
            bloque = datos_binarios[i : i + tamano_bloque]
            conexion.write(bloque)
            
            # 🛑 ESPERAMOS LA SEÑAL "NEXT"
            respuesta_placa = conexion.readline().decode('utf-8').strip()
            if respuesta_placa != "NEXT":
                print(f"⚠️ Error: La placa respondió: {respuesta_placa}")
                break
            
        print("✅ Todos los bloques confirmados. Esperando renderizado final...")
        
        resultado_final = conexion.readline().decode('utf-8').strip()
        print(f"🤖 [LILYGO]: {resultado_final}")
        
    else:
        print(f"🔴 La placa no dio luz verde. Respondió: {respuesta}")

    conexion.close()

except Exception as e:
    print(f"🔴 Error de conexión: {e}")