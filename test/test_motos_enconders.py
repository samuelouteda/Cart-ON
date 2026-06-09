import serial
import time
import threading

# --- CONFIGURACIÓN (Ajustada a tu código de Arduino) ---
PUERTO_SERIE = '/dev/ttyACM0'  # Cambiar a '/dev/ttyUSB0' si da error
BAUDIOS = 115200               # Velocidad del puerto serie

try:
    print(f"Conectando al Arduino en {PUERTO_SERIE} a {BAUDIOS} baudios...")
    arduino = serial.Serial(PUERTO_SERIE, BAUDIOS, timeout=1)
    time.sleep(2)  # Espera obligatoria a que el Arduino se reinicie
    print("¡Conectado con éxito!\n")
except Exception as e:
    print(f"❌ Error de conexión: {e}")
    print("Asegúrate de que el cable USB está bien puesto.")
    exit()

# Variable para controlar el hilo de lectura
ejecutando = True

# ===== HILO PARA LEER LOS ENCODERS CONTINUAMENTE =====
def leer_arduino():
    global ejecutando
    print("✨ Hilo de escucha activado (Encoders ocultos para limpiar la terminal).")
    while ejecutando:
        try:
            if arduino.in_waiting > 0:
                linea = arduino.readline().decode('utf-8').strip()
                
                # --- AQUÍ ESTÁ EL TRUCO ---
                # Recibe los datos de los encoders, pero NO los imprime para no inundar la pantalla
                if linea.startswith("ENC,"):
                    pass 
                
                # SÍ imprimimos las confirmaciones de tus órdenes (ACK)
                elif linea.startswith("ACK,"):
                    print(f"\n✅ [ARDUINO DICE]: {linea}")
                    print("Introduce comando: ", end="", flush=True)
                
                # Cualquier otro mensaje o error que envíe el Arduino
                else:
                    print(f"\n💬 [MENSAJE ARDUINO]: {linea}")
                    print("Introduce comando: ", end="", flush=True)
        except Exception as e:
            pass

# Iniciamos el hilo en segundo plano
hilo_lectura = threading.Thread(target=leer_arduino, daemon=True)
hilo_lectura.start()

# ===== BUCLE PRINCIPAL DE CONTROL =====
print("------------------------------------------------------------")
print("SISTEMA DE CONTROL DEL ROBOT (Terminal Limpia)")
print("Comandos válidos: AVANZA, ATRAS, GIRO_DER, STOP")
print("Puedes poner velocidad opcional (ej: AVANZA,120 o GIRO_DER,90)")
print("Escribe 'SALIR' para terminar.")
print("------------------------------------------------------------\n")

try:
    while True:
        # El programa se queda aquí parado esperando pacientemente a que escribas
        entrada = input("Introduce comando: ").strip()
        
        if entrada.upper() == "SALIR":
            break
            exit()
        if entrada == "":
            continue
            
        # Comprobamos si el usuario ha puesto velocidad (separada por coma)
        if "," in entrada:
            accion, velocidad = entrada.split(',')
            accion = accion.upper().strip()
            velocidad = velocidad.strip()
        else:
            accion = entrada.upper()
            velocidad = "150" # Velocidad por defecto (segura para pruebas)
            
        # Validamos y enviamos el comando en el formato exacto del Arduino
        if accion in ["AVANZA", "ATRAS", "GIRO_DER", "STOP"]:
            comando_final = f"CMD,{accion},{velocidad}\n"
            arduino.write(comando_final.encode('utf-8'))
        else:
            print(f"❌ '{accion}' no es un comando válido. Prueba con AVANZA, ATRAS, GIRO_DER o STOP.")

except KeyboardInterrupt:
    print("\nInterrupción detectada.")

finally:
    print("\nDeteniendo robot y cerrando puertos...")
    # Por seguridad, mandamos un comando de parada antes de salir
    arduino.write("CMD,STOP,0\n".encode('utf-8'))
    time.sleep(0.1)
    ejecutando = False
    arduino.close()
    print("¡Prueba finalizada de forma segura!")