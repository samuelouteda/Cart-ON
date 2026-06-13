from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT
from modules.processing.navigation.path_planner import PathPlanner
from modules.processing.navigation.frontier_explorer import FrontierExplorer
from modules.actuation.motion_controller import MotionController

# IMPORTAMOS EL TRADUCTOR DE COORDENADAS
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

        # VARIABLES DE "RETURN TO HOME"
        self.home_x = 0.0
        self.home_y = 0.0
        self.returning_home = False
        
        self.destinations_queue = [] #cola paradas super

        # VARIABLES DE ESCANEO DE ESTANTERÍAS (OPCIÓN B)
        self.is_scanning_shelf = False
        self.last_scan_time = 0.0

        # CONFIGURACIÓN DEL ORIGEN GPS (Ej: Puerta principal del edificio)
        self.gps_transformer = CoordinateTransformer(origin_lat=41.502, origin_lon=2.104, yaw_offset_rad=0.0)

    def _init_motion(self):
        wf = self.shared_data.get("wheel_firm", None)
        if wf:
            self.wheel_firm = wf
            self.motion_controller = MotionController(self.wheel_firm)
            print(f"{INDENT_OUTPUT}[{self.name}] MotionController inicialitzat.")

    def handle_task(self, task):
        # ========================================================
        # 1. ÓRDENES FÍSICAS PROVENIENTES DEL HRI/NUBE
        # ========================================================
        if task.type == "START_DRIVING":
            if self.exploring:
                print(f"{INDENT_OUTPUT}[{self.name}] Deactivating exploration phase to start commercial route.")
                self.exploring = False
                if self.motion_controller:
                    self.motion_controller.stop()
                time.sleep(0.5)
            
            datos_destino = task.data
            aula = datos_destino.get("aula")
            lat_gps = datos_destino.get("lat")
            lng_gps = datos_destino.get("lng")
            ruta_supermercado = datos_destino.get("ruta_supermercado", [])

            self._update_pose_from_odom()
            if self.motion_controller:
                self.home_x = self.motion_controller.current_x
                self.home_y = self.motion_controller.current_y

            self.destinations_queue = [] # Limpiamos viajes anteriores
            self.returning_home = False

            if "item_locations" not in self.shared_data:
                self.shared_data["item_locations"] = {}

            # OPCIÓN A: MODO UNIVERSITARIO (Un solo destino)
            if aula and lat_gps and lng_gps:
                local_x, local_y = self.gps_transformer.gps_to_local(lat_gps, lng_gps)
                self.destinations_queue.append((aula, local_x, local_y))
                
            # OPCIÓN B: MODO SUPERMERCADO (Múltiples destinos)
            elif ruta_supermercado:
                print(f"{INDENT_OUTPUT}[{self.name}] Calculando ruta óptima para {len(ruta_supermercado)} productos...")
                curr_x, curr_y = self.home_x, self.home_y
                pendientes = ruta_supermercado.copy()
                
                # Algoritmo de Vecino Más Cercano (Nearest Neighbor)
                while pendientes:
                    mas_cercano = min(pendientes, key=lambda p: math.hypot(p['x'] - curr_x, p['y'] - curr_y))
                    self.destinations_queue.append((mas_cercano['producto'], mas_cercano['x'], mas_cercano['y']))
                    curr_x, curr_y = mas_cercano['x'], mas_cercano['y']
                    pendientes.remove(mas_cercano)

            # ARRANCAMOS LA PRIMERA PARADA
            if self.destinations_queue:
                siguiente_parada, sx, sy = self.destinations_queue.pop(0)
                self.target_item = siguiente_parada
                self.shared_data["item_locations"][siguiente_parada] = (sx, sy)
                
                with self._nav_lock:
                    self.nav_state = "calculating"
                self.nav_start_time = time.time()
                print(f"{INDENT_OUTPUT}[{self.name}] Próxima parada: \"{self.target_item}\" (X={sx:.2f}, Y={sy:.2f})")
            else:
                print(f"{INDENT_OUTPUT}[{self.name}] START_DRIVING sin destinos válidos encontrados en la BD.")

        elif task.type == "START_MAPPING":
            print(f"{INDENT_OUTPUT}[{self.name}] IA autoritza mapeig. Iniciant explorador de fronteres...")
            self.exploring = True
            self.frontier_explorer.reset()
            self._exploration_step()
            
        elif task.type == "EMERGENCY_STOP":
            print(f"{INDENT_OUTPUT}[{self.name}] ¡FRENADA D'EMERGÈNCIA! Ordre del HRI.")
            if self.motion_controller:
                self.motion_controller.stop()
            with self._nav_lock:
                self.nav_state = "idle"
            self.exploring = False
            self.returning_home = False
            self.is_scanning_shelf = False

        # ========================================================
        # 2. ÓRDENES DEL PLANNER PARA REANUDAR ESCANEO
        # ========================================================
        elif task.type == "RESUME_AFTER_PHOTO":
            if self.is_scanning_shelf:
                print(f"{INDENT_OUTPUT}[{self.name}] El Planner ordena reanudar. Retomando ruta...")
                threading.Thread(target=self._resume_after_scan, daemon=True).start()

        # ========================================================
        # 3. ÓRDENES INTERNAS ANTIGUAS
        # ========================================================
        elif task.type == "navigate_to_item":
            self.target_item = task.data['item']
            with self._nav_lock:
                self.nav_state = "calculating"
            self.nav_start_time = time.time()
            self.returning_home = False
            print(f"{INDENT_OUTPUT}[{self.name}] Calculant ruta a \"{self.target_item}\"...")

        elif task.type == "start_exploration":
            self.exploring = True
            self.frontier_explorer.reset()
            self._exploration_step()

        elif task.type == "stop_exploration":
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
            self.shared_data["pending_task"] = None
            self.exploring = True
            self.frontier_explorer.reset()
            self._exploration_step()

        # -------------------------------------------------------------
        # PART 1: DETECCIÓ D'OBSTACLES I ESTANTERÍES (LASER)
        # -------------------------------------------------------------
        punts_laser = self.shared_data.get("scan", None)
        if punts_laser:
            # A) DETECCIÓN DE ESTANTERÍA (Solo si exploramos, no estamos escaneando y ha pasado el cooldown de 20s)
            if self.exploring and not self.is_scanning_shelf and (time.time() - self.last_scan_time > 20.0):
                puntos_derecha = []
                # El flanco derecho está aprox entre 260º y 280º
                if isinstance(punts_laser, list):
                    for qualitat, angle, distancia in punts_laser:
                        if 260 <= angle <= 280 and 300 < distancia < 1500: # Entre 30cm y 1.5m
                            puntos_derecha.append(distancia)
                else:
                    ranges = punts_laser.ranges
                    num_punts = len(ranges)
                    if num_punts > 0:
                        for i in range(num_punts):
                            angle = (i * 360.0) / num_punts
                            if 260 <= angle <= 280:
                                dist = ranges[i] * 1000
                                if 300 < dist < 1500:
                                    puntos_derecha.append(dist)
                
                # Geometría Plana: Si hay más de 10 puntos en ese sector y la diferencia entre ellos es menor a 150mm
                if len(puntos_derecha) > 10:
                    varianza = max(puntos_derecha) - min(puntos_derecha)
                    if varianza < 150: 
                        print(f"{INDENT_OUTPUT}[{self.name}] ¡Geometría de ESTANTERÍA detectada a la derecha!")
                        threading.Thread(target=self._execute_shelf_scan_maneuver, daemon=True).start()

            # B) ANTI-CHOQUES DE SEGURIDAD FRONTALES
            if not self.is_scanning_shelf:
                if isinstance(punts_laser, list):
                    for qualitat, angle, distancia in punts_laser:
                        if angle > 340 or angle < 20:
                            if 0 < distancia < 400:
                                print(f"{INDENT_OUTPUT}[{self.name}] ¡CRÍTICH! Obstacle a {distancia} mm")
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
                                    print(f"{INDENT_OUTPUT}[{self.name}] ¡CRÍTICH! Obstacle a {distancia_mm:.0f} mm")
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

        if current_state == "calculating" and not self.is_scanning_shelf:
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

    # ========================================================
    # LA COREOGRAFÍA DE ESCANEO ("EL BAILE")
    # ========================================================
    def _execute_shelf_scan_maneuver(self):
        self.is_scanning_shelf = True
        
        # 1. Clavar Frenos (interrumpe la exploración)
        if self.motion_controller:
            self.motion_controller.stop() 
        
        time.sleep(1) # Dejar que la inercia pare
        
        # 2. Girar 90º a la Derecha para encarar la estantería
        print(f"{INDENT_OUTPUT}[{self.name}] Turning towards the shelf...")
        if self.motion_controller and self.motion_controller.fw:
            # TUNEA ESTE SLEEP: Es el tiempo que tu Arduino tarda en girar 90º exactos a velocidad 120
            self.motion_controller.fw.giro_der(120)
            time.sleep(1.8) 
            self.motion_controller.fw.stop()
        
        time.sleep(0.5)
        
        # 3. Disparar evento para que vision.py haga la foto
        # 3. Disparar evento PARA EL PLANNER
        print(f"{INDENT_OUTPUT}[{self.name}] Notifying Planner that the shelf is ready...")
        self.publish_event(Event(origin=self.name, type="SHELF_DETECTED"))
        # Nos quedamos en modo is_scanning_shelf = True hasta que vision.py grite "PHOTO_DONE"

    def _resume_after_scan(self):
        # 4. Deshacer el giro (-90º) para volver a mirar al frente
        print(f"{INDENT_OUTPUT}[{self.name}] Recovering original orientation...")
        if self.motion_controller and self.motion_controller.fw:
            # TUNEA ESTE SLEEP: Mismo tiempo que el giro anterior
            self.motion_controller.fw.giro_izq(120)
            time.sleep(1.8) 
            self.motion_controller.fw.stop()

        self.last_scan_time = time.time() # Reseteamos el cooldown de 20s
        self.is_scanning_shelf = False
        
        # 5. La función _exploration_step, que estaba pausada, continuará sola.

    def _execute_path(self, waypoints):
        success = self.motion_controller.follow_path(waypoints)
        
        if success and not self.is_scanning_shelf:
            if self.destinations_queue:
                # ¡QUEDAN PARADAS EN LA LISTA!
                print(f"{INDENT_OUTPUT}[{self.name}] Arrived at {self.target_item}. Waiting 5s for item pickup...")
                time.sleep(5) # Tiempo para coger el paquete de arroz
                
                # Cargar el siguiente de la cola
                siguiente_parada, sx, sy = self.destinations_queue.pop(0)
                self.target_item = siguiente_parada
                self.shared_data["item_locations"][siguiente_parada] = (sx, sy)
                
                print(f"{INDENT_OUTPUT}[{self.name}] Moving to the next stop: {self.target_item}...")
                with self._nav_lock:
                    self.nav_state = "calculating"
                    
            elif not self.returning_home:
                # LISTA TERMINADA. VOLVEMOS A CASA
                print(f"{INDENT_OUTPUT}[{self.name}] Final destination reached. Waiting 5s before returning to Base...")
                time.sleep(5) 
                
                self.returning_home = True
                self.target_item = "HOME_BASE"
                if "item_locations" not in self.shared_data:
                    self.shared_data["item_locations"] = {}
                self.shared_data["item_locations"]["HOME_BASE"] = (self.home_x, self.home_y)
                
                print(f"{INDENT_OUTPUT}[{self.name}] Calculating return path...")
                with self._nav_lock:
                    self.nav_state = "calculating"
                    
            else:
                # LLEGAMOS A CASA
                print(f"{INDENT_OUTPUT}[{self.name}] Returned to Base! Mission completed.")
                self.publish_event(Event(type="PHYSICAL_ACTION_DONE", origin=self.name))
                with self._nav_lock:
                    self.nav_state = "idle"
                self.target_item = None
                self.returning_home = False
        else:
            if not self.is_scanning_shelf:
                print(f"{INDENT_OUTPUT}[{self.name}] Navigation failed or interrupted.")
                self.publish_event(Event(type="PHYSICAL_ACTION_DONE", origin=self.name))
                with self._nav_lock:
                    self.nav_state = "idle"
                self.target_item = None
                self.returning_home = False
                self.destinations_queue.clear() # Vaciamos la cola por si hay un error crítico

    def _exploration_step(self):
        def _step():
            while self.exploring:
                # Si estamos en medio del baile de la foto, pausar el explorador
                if self.is_scanning_shelf:
                    time.sleep(0.5)
                    continue

                mapa = self.shared_data.get("map", None)
                if mapa:
                    self.path_planner.update_map(mapa)
                else:
                    print(f"{INDENT_OUTPUT}[{self.name}] Esperant mapa...")
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

                if not success and not self.is_scanning_shelf:
                    print(f"{INDENT_OUTPUT}[{self.name}] Frontier no assolit, provant el següent...")

                time.sleep(0.5)

        threading.Thread(target=_step, daemon=True).start()