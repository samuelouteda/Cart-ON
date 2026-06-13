import heapq
import math
import threading
import numpy as np

from core.constants import INDENT_OUTPUT

class PathPlanner:

    OBSTACLE_THRESHOLD = 50
    INFLATION_RADIUS = 1

    def __init__(self):
        self.map_data = None
        self.width = 0
        self.height = 0
        self.resolution = 0.05
        self.origin_x = 0.0
        self.origin_y = 0.0
        self.grid = None
        self._map_lock = threading.Lock()

    def update_map(self, occupancy_grid_msg):
        with self._map_lock:
            info = occupancy_grid_msg.info
            self.width = info.width
            self.height = info.height
            self.resolution = info.resolution
            self.origin_x = info.origin.position.x
            self.origin_y = info.origin.position.y

            raw = np.array(occupancy_grid_msg.data, dtype=np.int8)
            self.grid = raw.reshape((self.height, self.width))
            self._inflate_obstacles()
            print(f"{INDENT_OUTPUT}[PathPlanner] Mapa actualitzat: {self.width}x{self.height}, res={self.resolution}m")

    def _inflate_obstacles(self):
        inflated = self.grid.copy()
        r = self.INFLATION_RADIUS
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y, x] > self.OBSTACLE_THRESHOLD:
                    for dy in range(-r, r+1):
                        for dx in range(-r, r+1):
                            ny, nx = y+dy, x+dx
                            if 0 <= ny < self.height and 0 <= nx < self.width:
                                inflated[ny, nx] = 100
        self.grid = inflated

    def world_to_cell(self, wx, wy):
        cx = int((wx - self.origin_x) / self.resolution)
        cy = int((wy - self.origin_y) / self.resolution)
        return cx, cy

    def cell_to_world(self, cx, cy):
        wx = cx * self.resolution + self.origin_x + self.resolution / 2
        wy = cy * self.resolution + self.origin_y + self.resolution / 2
        return wx, wy
    
    def get_nearest_free_cell(self, cx, cy, max_search_radius=10):
        """Busca la celda libre más cercana si el objetivo original está bloqueado."""
        if self.grid[cy, cx] >= 0 and self.grid[cy, cx] <= self.OBSTACLE_THRESHOLD:
            return (cx, cy) # Ya está libre

        # Búsqueda en espiral (BFS) para encontrar una celda libre cercana
        for r in range(1, max_search_radius):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        val = self.grid[ny, nx]
                        if val >= 0 and val <= self.OBSTACLE_THRESHOLD:
                            return (nx, ny)
        return None # No hay celdas libres cerca

    def plan(self, start_wx, start_wy, goal_wx, goal_wy):
        with self._map_lock:
            if self.grid is None:
                print(f"{INDENT_OUTPUT}[PathPlanner] No hi ha mapa disponible.")
                return None

            start = self.world_to_cell(start_wx, start_wy)
            goal  = self.world_to_cell(goal_wx, goal_wy)
            print(f"{INDENT_OUTPUT}[PathPlanner] Planificant: {start} → {goal}")

            valid_goal = self.get_nearest_free_cell(goal[0], goal[1])
            if valid_goal is None:
                print(f"{INDENT_OUTPUT}[PathPlanner] Destino y alrededores totalmente bloqueados.")
                return None
            goal = valid_goal

            path_cells = self._astar(start, goal)
            if path_cells is None:
                print(f"{INDENT_OUTPUT}[PathPlanner] No s'ha trobat ruta.")
                return None

            waypoints = [self.cell_to_world(cx, cy) for cx, cy in path_cells]
            waypoints = self._simplify_path(waypoints)
            print(f"{INDENT_OUTPUT}[PathPlanner] Ruta trobada: {len(waypoints)} waypoints.")
            return waypoints

    def _astar(self, start, goal):
        def heuristic(a, b):
            return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

        def is_free(cx, cy):
            if cx < 0 or cx >= self.width or cy < 0 or cy >= self.height:
                return False
            val = self.grid[cy, cx]
            return val >= 0 and val <= self.OBSTACLE_THRESHOLD

        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}

        neighbors = [
            (1,0),(-1,0),(0,1),(0,-1),
            (1,1),(1,-1),(-1,1),(-1,-1)
        ]

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == goal:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.reverse()
                return path

            for dx, dy in neighbors:
                nx, ny = current[0]+dx, current[1]+dy
                neighbor = (nx, ny)
                if not is_free(nx, ny):
                    continue
                move_cost = 1.414 if dx != 0 and dy != 0 else 1.0
                tentative_g = g_score[current] + move_cost
                if tentative_g < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f = tentative_g + heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f, neighbor))

        return None

    def _simplify_path(self, waypoints, tolerance=0.2):
        if len(waypoints) <= 2:
            return waypoints
        simplified = [waypoints[0]]
        for i in range(1, len(waypoints)-1):
            dx = waypoints[i][0] - simplified[-1][0]
            dy = waypoints[i][1] - simplified[-1][1]
            if math.sqrt(dx**2 + dy**2) >= tolerance:
                simplified.append(waypoints[i])
        simplified.append(waypoints[-1])
        return simplified