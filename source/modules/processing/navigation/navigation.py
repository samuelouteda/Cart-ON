from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT
from modules.processing.navigation.path_planner import PathPlanner
from modules.processing.navigation.frontier_explorer import FrontierExplorer
from modules.actuation.motion_controller import MotionController
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

    def _init_motion(self):
        wf = self.shared_data.get("wheel_firm", None)
        if wf:
            self.wheel_firm = wf
            self.motion_controller = MotionController(self.wheel_firm)
            print(f"[{self.name}] MotionController inicialitzat.")

    def handle_task(self, task):
        if task.type == "navigate_to_item":
            self.target_item = task.data['item']
            with self._nav_lock:
                self.nav_state = "calculating"
            self.nav_start_time = time.time()
            print(f"{INDENT_OUTPUT}[{self.name}] Calculant ruta a \"{self.target_item}\"...")

        elif task.type == "start_exploration":
            print(f"{INDENT_OUTPUT}[{self.name}] Iniciant exploració autònoma...")
            self.exploring = True
            self.frontier_explorer.reset()
            self._exploration_step()

        elif task.type == "stop_exploration":
            print(f"{INDENT_OUTPUT}[{self.name}] Aturant exploració.")
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
        # Inicialitza motion controller quan wheel_firm estigui disponible
        if self.motion_controller is None:
            self._init_motion()
            return

        # Comprova tasques pendents via shared_data
        pending = self.shared_data.get("pending_task", None)
        if pending == "start_exploration":
            print(f"[{self.name}] Tasca pendent rebuda: start_exploration")
            self.shared_data["pending_task"] = None
            self.exploring = True
            self.frontier_explorer.reset()
            self._exploration_step()

        # -------------------------------------------------------------
        # PART 1: DETECCIÓ D'OBSTACLES
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
        # PART 2: MÀQUINA D'ESTATS
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
        success = self.motion_controller.follow_path(waypoints)
        if success:
            print(f"{INDENT_OUTPUT}[{self.name}] Destinació assolida!")
            self.publish_event(
                Event(type="navigation_complete", data=self.target_item, origin=self.name)
            )
        else:
            print(f"{INDENT_OUTPUT}[{self.name}] Navegació fallida.")
            self.publish_event(
                Event(type="navigation_failed", data=self.target_item, origin=self.name)
            )
        with self._nav_lock:
            self.nav_state = "idle"
        self.target_item = None

    def _exploration_step(self):
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
                    self.publish_event(
                        Event(type="exploration_complete", origin=self.name)
                    )
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