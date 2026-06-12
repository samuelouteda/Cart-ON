import os
import sys

def test_diagnostic():
    print("=== DIAGNÒSTIC DE MAQUINARI (SPI OLEDS) ===")
    
    # 1. Comprovar si els dispositius SPI estan actius a Ubuntu
    print("\n1. Comprovant el sistema operatiu (Ubuntu)...")
    spi_devices = [f for f in os.listdir('/dev') if f.startswith('spidev')]
    
    if not spi_devices:
        print("❌ ERROR: No s'ha trobat cap dispositiu SPI a /dev/")
        print("   -> Revisa si has posat 'dtparam=spi=on' a /boot/firmware/config.txt i has reiniciat.")
        return
    else:
        print(f"   ✓ Correcte. Dispositius SPI trobats a /dev/: {spi_devices}")

    # 2. Comprovar si l'entorn de Python té els mòduls
    print("\n2. Comprovant llibreries de Python...")
    try:
        import spidev
        print("   ✓ 'spidev' importat correctament.")
    except ImportError:
        print("❌ ERROR: El mòdul 'spidev' no està instal·lat en aquest entorn de Python.")
        return

    try:
        from luma.core.interface.serial import spi
        from luma.oled.device import ssh1106
        print("   ✓ 'luma.oled' importat correctament.")
    except ImportError:
        print("❌ ERROR: La llibreria 'luma.oled' no està instal·lat en aquest entorn.")
        return

    # 3. Intentar connectar amb els teus pins específics (Fila exterior)
    print("\n3. Intentant obrir comunicació amb els pins...")
    print("   -> Port: 0, Device: 0, DC: GPIO 20 (Pin 38), RST: GPIO 16 (Pin 36)")
    try:
        # Intentem obrir el canal físic
        serial = spi(port=0, device=0, gpio_DC=20, gpio_RST=16)
        device = ssh1106(serial)
        
        print("\n🎉 ¡ÈXIT TOTAL! 🎉")
        print(f"   El programari ha pogut connectar amb el canal SPI.")
        print(f"   Mida de la pantalla detectada: {device.width}x{device.height} píxels.")
        print("   Si les pantalles continuen apagades, és un problema pur de cables elèctrics (VCC/GND/SCK/SDA).")
        
    except Exception as e:
        print(f"\n❌ ERROR DE CONNEXIÓ: {e}")
        print("   -> Això sol ser un problema de permisos de l'usuari a Ubuntu o pins mal configurats.")
        print("   -> Prova a executar: sudo usermod -aG gpio,dialout $USER i reinicia.")

if __name__ == "__main__":
    test_diagnostic()