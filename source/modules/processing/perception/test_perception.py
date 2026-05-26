# source/modules/processing/perception/test_perception.py
import cv2
import time
import sys
from pathlib import Path

# --- LA MAGIA DE LAS RUTAS ---
# Esto sube 4 niveles desde este archivo para encontrar la carpeta 'source'
# y la añade al "PATH" de Python para que los imports funcionen.
current_dir = Path(__file__).resolve().parent
source_dir = current_dir.parent.parent.parent
sys.path.append(str(source_dir))
# ------------------------------

# Ahora importamos tu clase (fíjate que ahora importamos desde el módulo local)
from perception import PerceptionSystem 
# (Nota: Si tu perception.py importaba BaseModule como 'from core.base_module...', ahora funcionará)

def run_test():
    # ... (el resto del código que te di se queda exactamente igual) ...
    print("========================================")
    print(" INICIANDO TEST DEL SISTEMA DE PERCEPCIÓN ")
# ...
    print("========================================")
    
    # 1. Inicializar el sistema (Esto cargará el modelo .pt)
    print("\n[1] Cargando cerebro (YOLOv8)...")
    try:
        vision = PerceptionSystem()
        print("  -> Modelo cargado correctamente.")
    except Exception as e:
        print(f"  -> [ERROR] Falló la carga del modelo: {e}")
        return

    # 2. Conectar la cámara (Usamos OpenCV directamente para el test rápido)
    print("\n[2] Conectando cámara web...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("  -> [ERROR] No se detecta ninguna cámara conectada (ID: 0)")
        return
    print("  -> Cámara conectada.")

    print("\n[3] Prueba de Inferencia en vivo iniciada.")
    print("    -> Presiona 'q' en la ventana de video para salir.")
    
    # Variables para calcular los FPS
    frame_count = 0
    start_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("  -> [ERROR] Se perdió la señal de la cámara.")
                break

            # --- LA LLAMADA IMPORTANTE A TU MÓDULO ---
            objects = vision.analyze_scene(frame)
            # -----------------------------------------
            
            frame_count += 1
            
            # Dibujar los resultados en la pantalla para ver que funciona
            for obj in objects:
                # Extraer coordenadas
                x1, y1, x2, y2 = map(int, obj["bbox"])
                label = f"{obj['label']} {obj['confidence']:.2f}"
                
                # Dibujar rectángulo verde
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                # Poner el texto arriba
                cv2.putText(frame, label, (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Mostrar ventana
            cv2.imshow("Test Percepcion - Robot", frame)

            # Salir con la tecla 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    finally:
        # Calcular los FPS finales
        elapsed_time = time.time() - start_time
        fps = frame_count / elapsed_time
        
        cap.release()
        cv2.destroyAllWindows()
        print("\n========================================")
        print(f" TEST FINALIZADO.")
        print(f" Rendimiento medio: {fps:.1f} FPS (Frames por segundo)")
        print("========================================")

if __name__ == "__main__":
    run_test()