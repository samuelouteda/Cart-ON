from gpiozero import LED
from time import sleep

print("--- PROVA DE ROBÒTICA AMB LA RASPBERRY PI ---")

# Definim que tenim un component connectat al Pin GPIO 17
# (De moment no cal que tinguis res connectat, és només per comprovar el codi)
llum_test = LED(17)

try:
    print("El programa està corrent correctament al cervell de la Raspberry!")
    print("Prem 'Control + C' a la terminal per tancar el programa.")
    
    while True:
        # Això farà que el pin 17 s'encengui i s'apagui internament
        llum_test.on()
        sleep(1)
        llum_test.off()
        sleep(1)

except KeyboardInterrupt:
    print("\nPrograma tancat correctament. Tot funciona perfecte!")