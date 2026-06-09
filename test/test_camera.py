import time
from pathlib import Path

# Inicialitzem la variable de la càmera a None per saber si s'ha arribat a crear
picam = None

print("--- INICI DEL TEST DE CÀMERA SENSE SERRADES ---")

# 1. PROVA DE CÀRREGA DE LLIBRERIA
try:
    print("[PAS 1/5] Intentant carregar la llibreria Picamera2...")
    from picamera2 import Picamera2
    print(" -> Llibreria carregada correctament.")
except ImportError:
    print("\n[ERROR CRÍTIC]: No es pot carregar 'picamera2'.")
    print("Això passa perquè el teu entorn virtual (.venv) està aïllat del sistema.")
    print("SOLUCIÓ: Executa el script fent servir el Python global de la Pi:")
    print("  python3 /home/marc/CartOn/test/test_camera.py")
    exit(1)

# 2. PROVA D'INICIALITZACIÓ DEL MAQUINARI
try:
    print("[PAS 2/5] Intentant connectar amb el sensor Sony IMX219...")
    picam = Picamera2()
    print(" -> Connexió amb el sensor establerta.")
except Exception as e:
    print(f"\n[ERROR CRÍTIC]: La Raspberry no s'ha pogut comunicar amb la càmera: {e}")
    print("Revisa que la cinta flex estigui ben fixada i no s'hagi mogut del connector CSI.")
    exit(1)

# 3. PROVA DE CONFIGURACIÓ I ARRENCADA
try:
    print("[PAS 3/5] Configurant paràmetres i engegant el sensor...")
    config = picam.create_preview_configuration()
    picam.configure(config)
    picam.start()
    print(" -> Sensor engegat. Esperant 2 segons per estabilitzar la llum...")
    time.sleep(2)
except Exception as e:
    print(f"\n[ERROR CRÍTIC]: Error en arrencar el mode captura de la càmera: {e}")
    if picam:
        picam.close()
    exit(1)

# 4. PROVA DE CAPTURA I DESAT DEL FITXER
try:
    ruta_foto = Path("/home/marc/CartOn/test/test_imatge.jpg")
    print(f"[PAS 4/5] Intentant fer la foto i desar-la a: {ruta_foto} ...")
    
    # Assegurem que la carpeta 'test' existeixi
    ruta_foto.parent.mkdir(parents=True, exist_ok=True)
    
    picam.capture_file(str(ruta_foto))
    print(" -> Foto capturada i guardada correctament al disc!")
except Exception as e:
    print(f"\n[ERROR CRÍTIC]: No s'ha pogut fer o desar la foto: {e}")
    print("Revisa si tens espai al disc o permisos d'escriptura en aquesta carpeta.")

# 5. PAS FINAL DE TANCAMENT SEGUR (S'executa SEMPRE si la càmera s'ha obert)
finally:
    if picam is not None:
        try:
            print("[PAS 5/5] Alliberant i tancant el port de la càmera de forma segura...")
            picam.stop()
            picam.close()
            print(" -> Port de la càmera tancat de forma neta.")
        except Exception as e:
            print(f"Avís: Error en tancar la càmera de forma controlada: {e}")

print("\n--- FINAL DEL PROGRAMA ---")