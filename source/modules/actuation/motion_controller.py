import math
import time
from .wheel_firm import WheelFirm

DIST_THRESHOLD = 0.05
ANGLE_THRESHOLD = 0.1
SPEED_LINEAR = 150
SPEED_TURN = 120

class MotionController:

    def __init__(self, wheel_firm: WheelFirm):
        self.fw = wheel_firm
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_theta = 0.0
        self.active = False
        self.stop_requested = False

    def update_pose(self, x, y, theta):
        self.current_x = x
        self.current_y = y
        self.current_theta = theta

    def go_to(self, target_x, target_y):
        self.stop_requested = False
        self.active = True
        timeout = time.time() + 30.0

        while self.active and not self.stop_requested and time.time() < timeout:
            dx = target_x - self.current_x
            dy = target_y - self.current_y
            dist = math.sqrt(dx**2 + dy**2)

            if dist < DIST_THRESHOLD:
                print(f"[MotionController] Waypoint assolit!")
                self.fw.stop()
                return True

            target_angle = math.atan2(dy, dx)
            angle_error = self._normalize_angle(target_angle - self.current_theta)

            if abs(angle_error) > ANGLE_THRESHOLD:
                if angle_error > 0:
                    self.fw.giro_izq(SPEED_TURN)
                else:
                    self.fw.giro_der(SPEED_TURN)
            else:
                self.fw.avanza(SPEED_LINEAR)

            time.sleep(0.05)

        self.fw.stop()
        if self.stop_requested:
            print(f"[MotionController] Aturat per obstacle.")
        else:
            print(f"[MotionController] Timeout o cancel·lat.")
        return False

    def follow_path(self, waypoints):
        print(f"[MotionController] Seguint ruta de {len(waypoints)} waypoints...")
        for i, (x, y) in enumerate(waypoints):
            if self.stop_requested:
                print(f"[MotionController] Ruta interrompuda per obstacle.")
                return False
            print(f"[MotionController] Waypoint {i+1}/{len(waypoints)}: ({x:.2f}, {y:.2f})")
            success = self.go_to(x, y)
            if not success:
                return False
        print(f"[MotionController] Ruta completada!")
        return True

    def stop(self):
        self.stop_requested = True
        self.active = False
        self.fw.stop()

    def _normalize_angle(self, angle):
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle