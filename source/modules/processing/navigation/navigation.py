from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT
from modules.processing.navigation.path_planner import PathPlanner
from modules.processing.navigation.frontier_explorer import FrontierExplorer
from modules.actuation.motion_controller import MotionController

# 🌍 IMPORTAMOS EL TRADUCTOR DE COORDENADAS
from modules.processing.navigation.coordinate_transformer import CoordinateTransformer

import threading
import time
import math

class Navigation(BaseModule):

    def __init__(self, name, event_bus, shared_sensor_stream, data_task_bus, shared_data):
        super().__init__(name, event_bus)
        self.sensor_stream = shared_sensor_stream
        self.data_task_bus = data_task_bus
        self.shared_data = shared_data

        self.nav_state = "idle"
        self._nav_lock = threading.Lock()
        self.target_item = None
        self.nav_start_time = 0

        self.path_planner = PathPlanner()
        self.frontier_explorer = FrontierExplorer(self.path_planner)
        self.exploring = False
        self.wheel_firm = None
        self.motion_controller = None

        # 🏠 VARIABLES DE "RETURN TO HOME"
        self.home_x = 0.0
        self.home_y = 0.0
        self.returning_home = False

        # 🗺️ CONFIGURACIÓN DEL ORIGEN GPS (Ej: Puerta principal del edificio)
        # ⚠️ Cambia estos valores por las coordenadas exactas de donde arranca tu SLAM
        self.gps_transformer = CoordinateTransformer(origin_lat=41.502, origin_lon=2.104, yaw_offset_rad=0.0)

    def _init_motion(self):
        wf = self.shared_data.get("wheel_firm", None)
        if wf:
            self.wheel_firm = wf
            self.motion_controller = MotionController(self.wheel_firm)
            print(f"[{self.name}] MotionController inicialitzat.")

    def handle_task(self, task):
        # ========================================================
        # 🚀 1. ÓRDENES FÍSICAS PROVENIENTES DEL HRI/NUBE
        # ========================================================
        if task.type == "START_DRIVING":
            datos_destino = task.data
            aula = datos_destino.get("aula")
            lat_gps = datos_destino.get("lat")
            lng_gps = datos_destino.get("lng")
            
            if aula and lat_gps and lng_gps:
                # 🌍 1. TRADUCIR COORDENADAS (GPS -> Metros del LiDAR)
                local_x, local_y = self.gps_transformer.gps_to_local(lat_gps, lng_gps)
                
                # 🏠 2. GUARDAR "HOME BASE"
                self._update_pose_from_odom()
                if self.motion_controller:
                    self.home_x = self.motion_controller.current_x
                    self.home_y = self.motion_controller.current_y

                # 🎯 3. INYECTAR DESTINO EN EL SISTEMA
                self.target_item = aula
                if "item_locations" not in self.shared_data:
                    self.shared_data["item_locations"] = {}
                self.shared_data["item_locations"][aula] = (local_x, local_y)

                # 🏎️ 4. ARRANCAR NAVEGACIÓN
                with self._nav_lock:
                    self.nav_state = "calculating"
                self.nav_start_time = time.time()
                self.returning_home = False
                print(f"{INDENT_OUTPUT}[{self.name}] 🚗 IA ordena ir a \"{self.target_item}\" (Local: X={local_x:.2f}, Y={local_y:.2f})...")
            else:
                print(f"{INDENT_OUTPUT}[{self.name}] ⚠️ START_DRIVING sense coordenades clares.")

        elif task.type == "START_MAPPING":
            print(f"{INDENT_OUTPUT}[{self.name}] 🧭 IA autoritza mapeig. Iniciant explorador de fronteres...")
            self.exploring = True
            self.frontier_explorer.reset()
            self._exploration_step()
            
        elif task.type == "EMERGENCY_STOP":
            print(f"{INDENT_OUTPUT}[{self.name}] 🛑 ¡FRENADA D'EMERGÈNCIA! Ordre del HRI.")
            if self.motion_controller:
                self.motion_controller.stop()
            with self._nav_lock:
                self.nav_state = "idle"
            self.exploring = False
            self.returning_home = False

        # ========================================================
        # ⚙️ 2. ÓRDENES INTERNAS ANTIGUAS
        # ========================================================
        elif task.type == "navigate_to_item":
            self.target_item = task.data['item']
            with self._nav_lock:
                self.nav_state = "calculating"
            self.nav_start_time = time.time()
            self.returning_home = False
            print(f"{INDENT_OUTPUT}[{self.name}] Calculant ruta a \"{self.target_item}\"...")

        elif task.type == "start_exploration":
            print(f"{INDENT_OUTPUT}[{self.name}] Iniciant exploració autònoma (Interna)...")
            self.exploring = True
            self.frontier_explorer.reset()
            self._exploration_step()

        elif task.type == "stop_exploration":
            print(f"{INDENT_OUTPUT}[{self.name}] Aturant exploració (Interna).")
            self.exploring = False
            if self.motion_controller:
                self.motion_controller.stop()

    def _update_pose_from_odom(self):
        odom = self.shared_data.get("odom", None)
        if odom and self.motion_controller:
            x     = odom.pose.pose.position.x
            y     = odom.pose.pose.position.y
            qz    = odom.pose.pose.orientation.z
            qw    = odom.pose.pose.orientation.w
            theta = 2 * math.atan2(qz, qw)
            self.motion_controller.update_pose(x, y, theta)

    def loop(self):
        if self.motion_controller is None:
            self._init_motion()
            return

        pending = self.shared_data.get("pending_task", None)
        if pending == "start_exploration":
            print(f"[{self.name}] Tasca pendent rebuda: start_exploration")
            self.shared_data["pending_task"] = None
            self.exploring = True
            self.frontier_explorer.reset()
            self._exploration_step()

        # -------------------------------------------------------------
        # PART 1: DETECCIÓ D'OBSTACLES (LASER)
        # -------------------------------------------------------------
        punts_laser = self.shared_data.get("scan", None)
        if punts_laser:
            if isinstance(punts_laser, list):
                for qualitat, angle, distancia in punts_laser:
                    if angle > 340 or angle < 20:
                        if 0 < distancia < 400:
                            print(f"[{self.name}] ¡CRÍTICH! Obstacle a {distancia} mm")
                            self.publish_event(Event(type="critical_obstacle", origin=self.name))
                            if self.motion_controller:
                                with self._nav_lock:
                                    if self.nav_state == "navigating":
                                        self.motion_controller.stop()
                                        self.nav_state = "idle"
                            break
            else:
                ranges = punts_laser.ranges
                num_punts = len(ranges)
                if num_punts > 0:
                    for i in range(num_punts):
                        angle = (i * 360.0) / num_punts
                        if angle > 340 or angle < 20:
                            distancia_metres = ranges[i]
                            if 0.05 < distancia_metres < 0.20:
                                distancia_mm = distancia_metres * 1000
                                print(f"[{self.name}] ¡CRÍTICH! Obstacle (ROS) a {distancia_mm:.0f} mm")
                                self.publish_event(Event(type="critical_obstacle", origin=self.name))
                                if self.motion_controller:
                                    with self._nav_lock:
                                        if self.nav_state == "navigating":
                                            self.motion_controller.stop()
                                            self.nav_state = "idle"
                                break

        # -------------------------------------------------------------
        # PART 2: MÀQUINA D'ESTATS (RUTAS)
        # -------------------------------------------------------------
        with self._nav_lock:
            current_state = self.nav_state

        if current_state == "calculating":
            mapa = self.shared_data.get("map", None)
            if mapa:
                self.path_planner.update_map(mapa)

            self._update_pose_from_odom()
            cx = self.motion_controller.current_x
            cy = self.motion_controller.current_y

            destins = self.shared_data.get("item_locations", {})
            if self.target_item in destins:
                gx, gy = destins[self.target_item]
            else:
                print(f"{INDENT_OUTPUT}[{self.name}] No conec la ubicació de \"{self.target_item}\"")
                with self._nav_lock:
                    self.nav_state = "idle"
                return

            waypoints = self.path_planner.plan(cx, cy, gx, gy)
            if waypoints is None:
                print(f"{INDENT_OUTPUT}[{self.name}] No s'ha trobat ruta.")
                with self._nav_lock:
                    self.nav_state = "idle"
                return

            self.shared_data["current_path"] = waypoints
            with self._nav_lock:
                self.nav_state = "navigating"
            threading.Thread(
                target=self._execute_path,
                args=(waypoints,),
                daemon=True
            ).start()

        elif current_state == "navigating":
            self._update_pose_from_odom()

    def _execute_path(self, waypoints):
        # El MotionController arranca los motores hasta terminar los waypoints
        success = self.motion_controller.follow_path(waypoints)
        
        if success:
            if not self.returning_home:
                # LLEGAMOS AL AULA
                print(f"{INDENT_OUTPUT}[{self.name}] Destinació assolida! Esperant 5 segons abans de tornar a casa...")
                time.sleep(5) # Tiempo para que la persona vea la pantalla / escanee QR
                
                # PREPARAMOS EL RETORNO
                self.returning_home = True
                self.target_item = "HOME_BASE"
                if "item_locations" not in self.shared_data:
                    self.shared_data["item_locations"] = {}
                self.shared_data["item_locations"]["HOME_BASE"] = (self.home_x, self.home_y)
                
                with self._nav_lock:
                    self.nav_state = "calculating"
            else:
                # LLEGAMOS A CASA
                print(f"{INDENT_OUTPUT}[{self.name}] 🏠 He tornat a la Base! Missió completada.")
                self.publish_event(Event(type="PHYSICAL_ACTION_DONE", origin=self.name)) # HRI VUELVE A HABLAR
                with self._nav_lock:
                    self.nav_state = "idle"
                self.target_item = None
                self.returning_home = False
        else:
            # FALLO EN RUTA (Obstáculo, emergency stop, etc.)
            print(f"{INDENT_OUTPUT}[{self.name}] Navegació fallida o interrompuda.")
            self.publish_event(Event(type="PHYSICAL_ACTION_DONE", origin=self.name)) # HRI VUELVE A HABLAR (Para avisar)
            with self._nav_lock:
                self.nav_state = "idle"
            self.target_item = None
            self.returning_home = False

    def _exploration_step(self):
        # (Se queda exactamente igual que tu código original)
        def _step():
            while self.exploring:
                mapa = self.shared_data.get("map", None)
                if mapa:
                    self.path_planner.update_map(mapa)
                else:
                    print(f"[{self.name}] Esperant mapa...")
                    time.sleep(1)
                    continue

                self._update_pose_from_odom()
                cx = self.motion_controller.current_x
                cy = self.motion_controller.current_y

                waypoints = self.frontier_explorer.explore_step(cx, cy)

                if waypoints is None:
                    print(f"{INDENT_OUTPUT}[{self.name}] Exploració completada!")
                    self.exploring = False
                    self.publish_event(Event(type="exploration_complete", origin=self.name))
                    break

                elif waypoints == "no_route":
                    print(f"{INDENT_OUTPUT}[{self.name}] Frontier inaccessible, provant el següent...")
                    time.sleep(0.2)
                    continue

                print(f"{INDENT_OUTPUT}[{self.name}] Anant al proper frontier...")
                with self._nav_lock:
                    self.nav_state = "navigating"

                success = self.motion_controller.follow_path(waypoints)

                with self._nav_lock:
                    self.nav_state = "idle"

                if not success:
                    print(f"{INDENT_OUTPUT}[{self.name}] Frontier no assolit, provant el següent...")

                time.sleep(0.5)

        threading.Thread(target=_step, daemon=True).start()