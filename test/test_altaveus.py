import os
from gtts import gTTS

def fer_parlar(text):
    print(f"Generant àudio per a: '{text}'...")
    
    # Crea el fitxer de veu usant el motor de Google
    tts = gTTS(text=text, lang='es', slow=False)
    
    # Desa l'àudio temporalment
    fitxer_audio = "veu_test.mp3"
    tts.save(fitxer_audio)
    
    # Reprodueix el fitxer mitjançant el reproductor del sistema
    print("Reproduint pels altaveus...")
    os.system(f"mpg123 -q {fitxer_audio}")
    
    # Opcional: Esborra el fitxer temporal després de sonar
    os.remove(fitxer_audio)

if __name__ == "__main__":
    # La frase que tu vols!
    fer_parlar("1, 2, 3")