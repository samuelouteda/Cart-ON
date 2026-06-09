import time
from rplidar import RPLidar #rplidar modelo C1

PORT_NAME = '/dev/ttyUSB0' #nombre del puerto que debe aparecer
BAUDRATE = 460800 #No tocar
TEMPS_DURADA_SEGONS = 10

lidar = None

try:
    print("Inicialitzant el LiDAR RPLIDAR C1...")
    lidar = RPLidar(PORT_NAME, baudrate=BAUDRATE)
    
    print("Forçant silenci inicial al LiDAR...")
    lidar.stop() 
    time.sleep(0.5)
    
    lidar.clean_input() #clear_input es para versiones anteriores
    if hasattr(lidar, '_serial') and lidar._serial:
        lidar._serial.reset_input_buffer()
        lidar._serial.reset_output_buffer()
    
    print("Engegat el motor del LiDAR C1...")
    lidar.start_motor()
    time.sleep(2.0)
    lidar.clean_input()
    
    print(f"\nComençant a llergir dades durant {TEMPS_DURADA_SEGONS} segons...")
    hora_inici = time.time()
    
    for scan in lidar.iter_scans(max_buf_meas=500):
        hora_actual = time.time()
        temps_transcorregut = hora_actual - hora_inici
        
        if temps_transcorregut >= TEMPS_DURADA_SEGONS:
            print(f"\n[TIMER]: S'han complert els {TEMPS_DURADA_SEGONS} segons.")
            break
            
        for measurement in scan:
            qualitat, angle, distancia_mm = measurement
            if distancia_mm > 0:
                if angle < 10 or angle > 350:
                    distancia_cm = distancia_mm / 10
                    print(f"[{temps_transcorregut:.1f}s] Objecte al davant! Angle: {angle:.1f}° | Distància: {distancia_cm:.1f} cm")

except KeyboardInterrupt:
    print("\nAturant el programa per l'usuari...")

except Exception as e:
    print(f"\n[ERROR]: S'ha produït un error de comunicació: {e}")

finally:
    if lidar is not None:
        print("\n--- PROTOCOL DE NETEJA I ATURADA COMTROLADA ---")
        try:
            print("1 -- Enviant ordre de STOP al làser...")
            lidar.stop()
            time.sleep(0.3)
            
            print("2 -- Apagant el motor elèctric...")
            lidar.stop_motor()
            time.sleep(0.5)
            
            print("3 -- Buidant residus del buffer de dades (clean_input)...") #limpiar siempre, sino peta
            lidar.clean_input()
            if hasattr(lidar, '_serial') and lidar._serial:
                lidar._serial.reset_input_buffer()
                lidar._serial.reset_output_buffer()
                
            print("4 -- Tancant el port sèrie permanentment...")
            lidar.disconnect()
            print("Neteja completada amb èxit.")
        except Exception as e:
            print(f"Error durant el procés de neteja final: {e}")
            
    print("Programa finalitzat.")