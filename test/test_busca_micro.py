import pyaudio

p = pyaudio.PyAudio()
print("\n--- LLISTA DE MICRÒFONS DISPONIBLES EN PYAUDIO ---")
for i in range(p.get_device_count()):
    dev = p.get_device_info_by_index(i)
    # Només mostrem els dispositius que poden capturar àudio (Inputs)
    if dev.get('maxInputChannels', 0) > 0:
        print(f"Índex {i}: {dev.get('name')} (Canals: {dev.get('maxInputChannels')}, Freq: {int(dev.get('defaultSampleRate'))}Hz)")
p.terminate()