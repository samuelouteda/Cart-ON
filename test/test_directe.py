import time
from rplidar import RPLidar

PORT_NAME = '/dev/ttyUSB0'
BAUDRATE = 460800
TEMPS_DURADA_SEGONS = 10
INTERVAL_IMPRESSIO = 0.5  # <--- Definim que volem mostrar dades cada 0,5 segons

lidar = None

try:
    print("Inicialitzant el LiDAR RPLIDAR C1...")
    lidar = RPLidar(PORT_NAME, baudrate=BAUDRATE)
    
    print("Forçant silenci inicial al LiDAR...")
    lidar.stop() 
    time.sleep(0.5)
    
    lidar.clean_input()
    if hasattr(lidar, '_serial') and lidar._serial:
        lidar._serial.reset_input_buffer()
        lidar._serial.reset_output_buffer()
    
    print("Engegat el motor del LiDAR C1...")
    lidar.start_motor()
    time.sleep(2.0)
    lidar.clean_input()
    
    print(f"\nComençant a llegir dades durant {TEMPS_DURADA_SEGONS} segons...")
    hora_inici = time.time()
    ultima_impressio = 0  # Controla quan s'ha imprès per última vegada
    
    for scan in lidar.iter_scans(max_buf_meas=500):
        hora_actual = time.time()
        temps_transcorregut = hora_actual - hora_inici
        
        if temps_transcorregut >= TEMPS_DURADA_SEGONS:
            print(f"\n[TIMER]: S'han complert els {TEMPS_DURADA_SEGONS} segons.")
            break
            
        # Comprovem si ha passat prou temps (0,5s) des de la darrera impressió
        if temps_transcorregut - ultima_impressio >= INTERVAL_IMPRESSIO:
            # Bandera per comprovar si hem trobat algun objecte en aquesta volta
            objecte_detectat = False
            
            for measurement in scan:
                qualitat, angle, distancia_mm = measurement
                if distancia_mm > 0:
                    if angle < 10 or angle > 350:
                        distancia_cm = distancia_mm / 10
                        print(f"[{temps_transcorregut:.1f}s] Objecte al davant! Angle: {angle:.1f}° | Distància: {distancia_cm:.1f} cm")
                        objecte_detectat = True
                        break # Sortim d'aquest scan per no repetir línies en el mateix instant
            
            # Si hem imprès o processat l'scan actual, actualitzem el temporitzador d'impressió
            if objecte_detectat:
                ultima_impressio = temps_transcorregut

except KeyboardInterrupt:
    print("\nAturant el programa per l'usuari...")

except Exception as e:
    print(f"\n[ERROR]: S'ha produït un error de comunicació: {e}")

finally:
    if lidar is not None:
        print("\n--- PROTOCOL DE NETEJA I ATURADA CONTROLADA ---")
        try:
            print("1. Enviant ordre de STOP al làser...")
            lidar.stop()
            time.sleep(0.3)
            
            print("2. Apagant el motor elèctric...")
            lidar.stop_motor()
            time.sleep(0.5)
            
            print("3. Buidant residus del buffer de dades (clean_input)...")
            lidar.clean_input()
            if hasattr(lidar, '_serial') and lidar._serial:
                lidar._serial.reset_input_buffer()
                lidar._serial.reset_output_buffer()
                
            print("4. Tancant el port sèrie permanentment...")
            lidar.disconnect()
            print("Neteja completada amb èxit.")
        except Exception as e:
            print(f"Error durant el procés de neteja final: {e}")
            
    print("Programa finalitzat.")