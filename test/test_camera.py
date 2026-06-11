import os
import time
import subprocess  # 👈 Llibreria clau per executar comandes del sistema (com rpicam-still)
from pathlib import Path

def capturar_foto_rpicam(carpeta_desti="capturas"):
    """
    Captura una foto utilitzant la utilitat nativa rpicam-still de la Raspberry Pi.
    Crea la carpeta de destí si no existeix i desa la imatge amb un timestamp únic.
    """
    print("\n📷 [CÀMERA] Iniciant procés de captura amb rpicam-still...")
    
    # 1. Assegurem que la carpeta destí existeixi
    ruta_carpeta = Path(carpeta_desti)
    ruta_carpeta.mkdir(parents=True, exist_ok=True)
    
    # 2. Generem un nom de fitxer únic basat en la data i hora exacta
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    ruta_foto = ruta_carpeta / f"captura_{timestamp}.jpg"
    
    # 3. Preparem la comanda exacta del sistema
    # --immediate: Agilitza el tret de la foto saltant-se part del preescalfat visual si cal
    # --width i --height: Resolució de la imatge (pols ajustar-la al teu gust)
    comanda = [
        "rpicam-still",
        "-o", str(ruta_foto),
        "--immediate",
        "--width", "1280",
        "--height", "720"
    ]
    
    try:
        print(f"⏳ Executant captura del sensor... Destí: {ruta_foto}")
        
        # Executem la comanda nativa en segon pla des de Python
        # capture_output=True recull els logs del sistema per si hi ha errors
        resultat = subprocess.run(comanda, check=True, capture_output=True, text=True)
        
        if ruta_foto.exists():
            print(f"✅ [CÀMERA] Foto feta amb èxit i guardada a: {ruta_foto}")
            return str(ruta_foto)
        else:
            print("❌ [CÀMERA] Error estrany: La comanda no ha fallat, però el fitxer no s'ha creat.")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ [ERROR CRÍTIC] La comanda rpicam-still ha fallat de sistema.")
        print(f"Detall de l'error del driver:\n{e.stderr}")
        return None
    except Exception as e:
        print(f"\n❌ [ERROR] S'ha produït un error inesperat: {e}")
        return None

# --- BLOC D'EXECUCIÓ PRINCIPAL (TEST) ---
if __name__ == "__main__":
    print("--- INICI DEL TEST DE CÀMERA SENSE SERRADES (MÈTODE DIRECTE) ---")
    
    # Esperem un Enter per fer la prova
    input("Prem ENTER per fer una foto de prova...")
    
    # Cridem a la funció
    fitxer_generat = capturar_foto_rpicam("capturas")
    
    if fitxer_generat:
        print(f"\n🎉 Test superat! Pots veure la imatge a la carpeta actual a: {fitxer_generat}")
    else:
        print("\n😢 El test ha fallat. Revisa els missatges de la terminal.")
        
    print("--- FINAL DEL PROGRAMA ---")