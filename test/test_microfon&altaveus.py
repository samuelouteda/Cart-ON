import os
import time
import sounddevice as sd
from scipy.io import wavfile
from gtts import gTTS
import speech_recognition as sr  # 🟢 Nova llibreria per passar de veu a text

# --- CONFIGURACIÓ ---
FREQ_MOSTREIG = 48000  # Freqüència nativa del teu micro USB
SEGONS_GRAVACIO = 3    # Durada del que tu parlis
ID_DISPOSITIU_USB = 1  # La teva Card 1 de l'arecord

# RUTES ABSOLUTES
FITXER_GRAVAT = "/home/marc/CartOn/test/gravacio_usuari.wav"

# Forcem el micro a la Card 1
sd.default.device = [ID_DISPOSITIU_USB, ID_DISPOSITIU_USB]

# ===== FUNCIÓ A: EL ROBOT PARLA =====
def fer_parlar(text):
    print(f"🤖 [ROBOT DIU]: '{text}'...")
    tts = gTTS(text=text, lang='es', slow=False)
    fitxer_audio = "/home/marc/CartOn/test/veu_temp.mp3"
    tts.save(fitxer_audio)
    os.system(f"mpg123 -q {fitxer_audio}")
    if os.path.exists(fitxer_audio):
        os.remove(fitxer_audio)

# ===== MAIN PROGRAM =====
print("--------------------------------------------------")
print("PROVA D'ÀUDIO AMB RECONEIXEMENT (CartOn Escolta, Parla i Entén)")
print("--------------------------------------------------")

try:
    # 1. El robot t'avisa usant el teu sistema d'altaveus
    fer_parlar("Hola Marc. Di algo después de la señal.")
    time.sleep(0.5)
    
    # 2. El micròfon comença a gravar
    print("\n🎤 [MICRO]: Gravant ara mateix...")
    gravacio = sd.rec(int(SEGONS_GRAVACIO * FREQ_MOSTREIG), 
                      samplerate=FREQ_MOSTREIG, 
                      channels=1, 
                      dtype='int16')
    sd.wait()
    print("🛑 [MICRO]: Gravació finalitzada.")
    
    # 3. Desem el que has dit a la ruta absoluta fixa
    wavfile.write(FITXER_GRAVAT, FREQ_MOSTREIG, gravacio)
    
    # 🟢 4. RECONEIXEMENT DE VEU (Passar l'àudio a text)
    print("\n🧠 [PROCESSANT]: Traduint la teva veu a text...")
    reconeixedor = sr.Recognizer()
    
    with sr.AudioFile(FITXER_GRAVAT) as font:
        audio_dades = reconeixedor.record(font)
        try:
            # Enviem l'àudio a Google (configurat en castellà 'es-ES' o 'ca-ES' si parles en català)
            text_reconegut = reconeixedor.recognize_google(audio_dades, language='es-ES')
            
            # Mostrem per pantalla el que has dit
            print(f"📝 [TEXT DETECTAT]: \"{text_reconegut}\"")
            
            # El robot diu "¡Recibido!"
            fer_parlar("¡Recibido!")
            
        except sr.UnknownValueError:
            print("📝 [TEXT DETECTAT]: No s'ha entès el que has dit (soroll o silenci).")
            fer_parlar("No te he entendido.")
        except sr.RequestError:
            print("❌ Error: No s'ha pogut connectar al servei de reconeixement de Google.")
            fer_parlar("Error de conexión.")

    # 5. REPRODUCCIÓ REIAL: L'eco de la teva veu original
    print("\n🔊 [ALTAUEU]: Repetint la teva veu original...")
    os.system(f"aplay -q -D plughw:{ID_DISPOSITIU_USB},0 {FITXER_GRAVAT}")
    
    # Neteja del fitxer provisional
    if os.path.exists(FITXER_GRAVAT):
        os.remove(FITXER_GRAVAT)
        
    print("\n¡Prova rodona completada amb èxit total!")

except Exception as e:
    print(f"\n❌ Error al sistema d'àudio: {e}")