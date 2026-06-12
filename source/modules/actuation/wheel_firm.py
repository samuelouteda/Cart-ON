import serial
import threading
import time

class WheelFirm:

    def __init__(self, port="/dev/ttyACM0", baud=115200):
        self.port = port
        self.baud = baud
        self.ser = None
        self.running = False
        self.on_encoder = None
        self.on_ack = None
        self._connect()

    def _connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            time.sleep(2)
            self.running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            print(f"[WheelFirm] Connectat a {self.port}")
        except Exception as e:
            print(f"[WheelFirm] Error connectant a {self.port}: {e}")
            self.ser = None

    def _read_loop(self):
        while self.running and self.ser:
            try:
                line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                if line.startswith("ENC,"):
                    parts = line.split(",")
                    if len(parts) == 4:
                        left  = int(parts[1])
                        right = int(parts[2])
                        dt    = int(parts[3])
                        if self.on_encoder:
                            self.on_encoder(left, right, dt)
                elif line.startswith("ACK,"):
                    if self.on_ack:
                        self.on_ack(line[4:])
                elif line.startswith("ERROR"):
                    print(f"[WheelFirm] Arduino error: {line}")
            except Exception as e:
                print(f"[WheelFirm] Error lectura: {e}")
                time.sleep(0.1)

    def set_odom_node(self, wheel_odom):
        """Connecta el WheelOdom per rebre dades d'encoders."""
        self.on_encoder = lambda l, r, dt: wheel_odom.update_encoders(l, r)

    def _send(self, cmd):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write((cmd + "\n").encode())
            except Exception as e:
                print(f"[WheelFirm] Error enviant '{cmd}': {e}")
        else:
            print(f"[WheelFirm] No connectat: {cmd}")

    def avanza(self, speed=150):
        self._send(f"CMD,AVANZA,{speed}")

    def atras(self, speed=150):
        self._send(f"CMD,ATRAS,{speed}")

    def giro_der(self, speed=150):
        self._send(f"CMD,GIRO_DER,{speed}")

    def giro_izq(self, speed=150):
        self._send(f"CMD,GIRO_IZQ,{speed}")

    def stop(self):
        self._send("CMD,STOP")

    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    def close(self):
        self.running = False
        self.stop()
        time.sleep(0.2)
        if self.ser:
            self.ser.close()
        print("[WheelFirm] Desconnectat.")