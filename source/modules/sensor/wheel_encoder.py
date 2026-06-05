from core.base_module import BaseModule
from core.event import Event
import serial


class WheelEncoder(BaseModule):

    def __init__(self, name, event_bus, shared_data, port="/dev/ttyACM0", baudrate=115200):
        super().__init__(name, event_bus)

        self.shared_data = shared_data

        self.serial = serial.Serial(port, baudrate, timeout=1)

        self.shared_data["encoders"] = {
            "left": 0,
            "right": 0,
            "dt": 0
        }

    def parse_line(self, line: str):
        try:
            if not line.startswith("ENC"):
                return None

            _, l, r, dt = line.strip().split(",")

            return int(l), int(r), float(dt)

        except Exception:
            return None

    def handle_task(self, task):
        pass  # no tasks needed yet

    def loop(self):
        if self.serial.in_waiting:
            line = self.serial.readline().decode("utf-8", errors="ignore")

            data = self.parse_line(line)

            if data is None:
                return

            l, r, dt = data

            self.shared_data["encoders"]["left"] = l
            self.shared_data["encoders"]["right"] = r
            self.shared_data["encoders"]["dt"] = dt

            self.publish_event(
                Event(
                    origin=self.name,
                    type="encoder_update",
                    data={
                        "left": l,
                        "right": r,
                        "dt": dt
                    }
                )
            )