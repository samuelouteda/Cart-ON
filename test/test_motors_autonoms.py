import serial
import time
import threading
from datetime import datetime

# --- CONFIGURACIÓN DEL PUERTO SERIE ---
PUERTO_SERIE = '/dev/ttyACM0'
BAUDIOS = 115200

# Función para guardar en el archivo de texto con la hora exacta
def guardar_log(texto):
    ahora = datetime.now().strftime("%H:%M:%S")
    linea_log = f"[{ahora}] {texto}\n"
    print(linea_log.strip()) # Lo saca por la terminal si estás conectado por SSH
    try:
        # Ruta ajustada a tu carpeta de usuario real 'CartOn'
        with open("/home/CartOn/test/registro_robot.txt", "a") as f: 
            f.write(linea_log)
    except:
        pass

try:
    guardar_log(f"Conectando al Arduino en {PUERTO_SERIE}...")
    arduino = serial.Serial(PUERTO_SERIE, BAUDIOS, timeout=1)
    time.sleep(3)
    guardar_log("¡Arduino conectado con éxito!")
except Exception as e:
    guardar_log(f"❌ Error de conexión: {e}")
    exit()

ejecutando = True

# ===== HILO EN SEGUNDO PLANO: PROCESA LOS ENCODERS =====
def leer_arduino():
    global ejecutando
    while ejecutando:
        try:
            if arduino.in_waiting > 0:
                linea = arduino.readline().decode('utf-8').strip()
                
                # Captura los encoders y los guarda de forma bonita
                if linea.startswith("ENC,"):
                    partes = linea.split(',')
                    if len(partes) == 4:
                        guardar_log(f"📊 [ENCODERS] Izq: {partes[1]} | Der: {partes[2]} (Delta: {partes[3]}ms)")
                
                # Guarda las confirmaciones de comandos del Arduino
                elif linea.startswith("ACK,") or linea.startswith("RECIBIDO:"):
                    guardar_log(f"📩 [ARDUINO]: {linea}")
                
                # Captura posibles errores de formato o comandos desconocidos
                elif "ERROR" in linea:
                    guardar_log(f"⚠️ [ALERTA ARDUINO]: {linea}")
        except:
            pass

hilo_lectura = threading.Thread(target=leer_arduino, daemon=True)
hilo_lectura.start()

def enviar_comando(accion, velocidad=150):
    comando = f"CMD,{accion},{velocidad}\n"
    arduino.write(comando.encode('utf-8'))
    guardar_log(f"🚀 [PI ENVIADO]: {comando.strip()}")

# ===== SECUENCIA AUTOMÁTICA EN BUCLE INFINITO =====
try:
    guardar_log("--- INICIANDO SECUENCIA EN BUCLE EN 3 SEGUNDOS ---")
    time.sleep(3)
    
    contador_vueltas = 1
    
    while True: # <--- Aquí empieza el bucle infinito
        guardar_log(f"\n🔄 === INICIANDO CICLO NÚMERO {contador_vueltas} ===")
        
        guardar_log("Etapa 1: Avanzar")
        enviar_comando("AVANZA", 250)
        time.sleep(2)
        
        # guardar_log("Etapa 2: Girar")
        # enviar_comando("GIRO_DER", 250) 
        # time.sleep(2)
        
        guardar_log("Etapa 3: Atrás")
        enviar_comando("ATRAS", 250)
        time.sleep(2)
        
        guardar_log("Etapa 4: Parar y esperar")
        enviar_comando("STOP", 0)
        time.sleep(2) # <--- Espera de 2 segundos quieto antes de reiniciar la secuencia
        
        contador_vueltas += 1

except KeyboardInterrupt:
    guardar_log("⚠️ Secuencia interrumpida por el usuario.")

finally:
    # Código de seguridad: si detienes el servicio, el robot se frena en seco
    guardar_log("Finalizando bucle de manera segura...")
    enviar_comando("STOP", 0)
    time.sleep(0.5) 
    ejecutando = False
    arduino.close()
    guardar_log("--- FIN DE LA SECUENCIA AUTÓNOMA ---")