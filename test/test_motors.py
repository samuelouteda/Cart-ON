import time
from gpiozero import PWMOutputDevice, DigitalOutputDevice, RotaryEncoder

# --- CONFIGURACIÓ DE PINS ---
PIN_R_EN_L_EN = 17
PIN_RPWM = 12
PIN_LPWM = 13

PIN_ENC_A = 22
PIN_ENC_B = 23

try:
    print("Inicialitzant components del BTS7960 i Encoder...")
    
    # 1. Configurem el driver de potència
    # El pin d'Enable ha d'estar actiu (True) perquè el motor respongui
    driver_enable = DigitalOutputDevice(PIN_R_EN_L_EN, initial_value=True)
    
    # Els pins PWM controlen el sentit i velocitat (0.0 a 1.0)
    motor_endavant = PWMOutputDevice(PIN_RPWM, frequency=1000)
    motor_enrere = PWMOutputDevice(PIN_LPWM, frequency=1000)
    
    # 2. Configurem l'encoder per llegir la posició
    encoder = RotaryEncoder(PIN_ENC_A, PIN_ENC_B, max_steps=0) # max_steps=0 fa que no tingui límit de comptatge
    
    print(" -> Maquinari configurat correctament.")
    print("\n--- INICI DE LA PROVA DEL MOTOR 12V ---")
    
    # Funció interna per assegurar que el motor està parat
    def aturar_motor():
        motor_endavant.value = 0
        motor_enrere.value = 0

    # --- FASE 1: MOURE ENDAVANT ---
    print("\n[PAS 1] Movent cap endavant al 30% de potència...")
    encoder.steps = 0 # Reiniciem el comptador de l'encoder
    motor_endavant.value = 0.3 # 30% de velocitat
    motor_enrere.value = 0.0
    
    # Durant 3 segons, llegim què diu l'encoder
    for _ in range(30):
        print(f"Posició de l'encoder: {encoder.steps} polsos")
        time.sleep(0.1)
        
    aturar_motor()
    print(" -> Motor aturat. Esperant 1 segon...")
    time.sleep(1)
    
    # --- FASE 2: MOURE ENRERE ---
    print("\n[PAS 2] Movent cap enrere al 40% de potència...")
    motor_endavant.value = 0.0
    motor_enrere.value = 0.4 # 40% de velocitat
    
    for _ in range(30):
        print(f"Posició de l'encoder: {encoder.steps} polsos")
        time.sleep(0.1)
        
    aturar_motor()
    print("\n--- PROVA FINALITZADA AMB ÈXIT ---")
    print(f"Posició final de l'encoder: {encoder.steps} polsos.")

except Exception as e:
    print(f"\n[ERROR CRÍTIC]: S'ha produït un error en el test: {e}")

finally:
    # Seguretat absoluta: Si el programa peta, matem el corrent al motor
    try:
        motor_endavant.value = 0
        motor_enrere.value = 0
        driver_enable.value = False
        print("Seguretat: Motors completament desconnectats.")
    except:
        pass