from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT
import time


class Navigation(BaseModule):

    def __init__(self, name, event_bus, shared_sensor_stream, data_task_bus, shared_data):
        super().__init__(name, event_bus)
        self.sensor_stream = shared_sensor_stream

        self.data_task_bus = data_task_bus
        self.shared_data = shared_data
        
        self.nav_state = "idle"
        self.target_item = None
        self.nav_start_time = 0

    def handle_task(self, task):
        if task.type == "navigate_to_item":
            self.target_item = task.data['item']
            self.nav_state = "calculating"
            self.nav_start_time = time.time()
            print(f"{INDENT_OUTPUT}[{self.name}] Calculating path to \"{self.target_item}\"...")
    
    def loop(self):
        # ---------------------------------------------------------------------
        # PART 1: DETECCIÓ D'OBSTACLES EN TEMPS REAL (SEGURETAT)
        # ---------------------------------------------------------------------
        punts_laser = self.shared_data.get("scan", None)
        
        if punts_laser:
            # CAS A: Si les dades vénen de la llibreria rplidar directe (Llista de tuples)
            if isinstance(punts_laser, list):
                for qualitat, angle, distancia in punts_laser:
                    # Mirem el con frontal del robot (entre 340º i 20º)
                    if angle > 340 or angle < 20:
                        # Si hi ha obstacle a menys de 400 mm (40 cm)
                        if 0 < distancia < 400:
                            print(f"[{self.name}] ¡CRÍTICH! Obstacle detectat al davant a {distancia} mm")
                            self.publish_event(Event(type="critical_obstacle", origin=self.name))
                            break # Sortim del bucle de punts per no inundar l'EventBus
            
            # CAS B: Si les dades vénen del tòpic natiu de ROS 2 (LaserScan object)
            else:
                ranges = punts_laser.ranges
                num_punts = len(ranges)
                if num_punts > 0:
                    for i in range(num_punts):
                        # Calculem l'angle de cada índex (de 0 a 360)
                        angle = (i * 360.0) / num_punts
                        if angle > 340 or angle < 20:
                            distancia_metres = ranges[i]
                            # A ROS, si no hi ha res o està fora de rang, pot valdre 'inf' o 0.0
                            if 0.02 < distancia_metres < 0.40: # Menys de 40 cm
                                distancia_mm = distancia_metres * 1000
                                print(f"[{self.name}] ¡CRÍTICH! Obstacle detectat (via ROS) a {distancia_mm:.0f} mm")
                                self.publish_event(Event(type="critical_obstacle", origin=self.name))
                                break

        # ---------------------------------------------------------------------
        # PART 2: MÀQUINA D'ESTATS DE LA NAVEGACIÓ (Recuperada)
        # ---------------------------------------------------------------------
        if self.nav_state == "calculating":
            if time.time() - self.nav_start_time >= 0.2:
                print(f"{INDENT_OUTPUT}[{self.name}] Navigating to \"{self.target_item}\"")
                self.nav_state = "navigating"
                self.nav_start_time = time.time()
                
        elif self.nav_state == "navigating":
            if time.time() - self.nav_start_time >= 2.0:
                self.publish_event(
                    Event(
                        type="navigation_complete",
                        data=self.target_item,
                        origin=self.name
                    )
                )
                self.nav_state = "idle"
                self.target_item = None