import time
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.oled.device import sh1106

def inicialitzar_ulls():
    try:
        # - port=0, device=0 agafa els natius SCK (23) i SDA (19)
        # - gpio_DC=20 -> Pin 38 físic
        # - gpio_RST=16 -> Pin 36 físic
        # - bcm_CS=21 -> Força el Pin 40 físic com a Chip Select
        serial = spi(port=0, device=0, gpio_DC=20, gpio_RST=16, bcm_CS=21)
        
        dispositiu = sh1106(serial, width=128, height=64)
        print("👀 Ulls vius i sincronitzats amb el bloc 36-38-40!")
        return dispositiu
    except Exception as e:
        print(f"❌ Error de configuració de pins: {e}")
        return None

def dibuixar_ulls(device, posicio_pupila):
    with canvas(device) as draw:
        # Fons negre
        draw.rectangle(device.bounding_box, outline="black", fill="black")
        # Globus ocular
        draw.ellipse((24, 2, 104, 62), fill="white")
        
        # Pupi·la segons moviment
        if posicio_pupila == "centre":
            draw.ellipse((52, 22, 76, 46), fill="black")
        elif posicio_pupila == "esquerra":
            draw.ellipse((34, 22, 58, 46), fill="black")
        elif posicio_pupila == "dreta":
            draw.ellipse((70, 22, 94, 46), fill="black")

def main():
    ulls = inicialitzar_ulls()
    if not ulls: return

    try:
        while True:
            dibuixar_ulls(ulls, "centre"); time.sleep(2.0)
            dibuixar_ulls(ulls, "esquerra"); time.sleep(1.5)
            dibuixar_ulls(ulls, "centre"); time.sleep(1.0)
            dibuixar_ulls(ulls, "dreta"); time.sleep(1.5)
    except KeyboardInterrupt:
        print("\nTancant pantalles...")
    finally:
        if ulls: ulls.clear()

if __name__ == "__main__":
    main()