import math
import numpy as np
from collections import deque

class FrontierExplorer:

    UNKNOWN = -1
    FREE = 0
    OBSTACLE_THRESHOLD = 50

    def __init__(self, path_planner):
        self.path_planner = path_planner
        self.visited_frontiers = set()

    def find_frontiers(self, grid, width, height):
        frontiers = []
        for y in range(1, height-1):
            for x in range(1, width-1):
                if grid[y, x] != self.FREE:
                    continue
                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    if grid[y+dy, x+dx] == self.UNKNOWN:
                        frontiers.append((x, y))
                        break
        return frontiers

    def cluster_frontiers(self, frontiers, min_size=5):
        if not frontiers:
            return []

        frontier_set = set(frontiers)
        visited = set()
        clusters = []

        for start in frontiers:
            if start in visited:
                continue
            cluster = []
            queue = deque([start])
            while queue:
                cell = queue.popleft()
                if cell in visited:
                    continue
                visited.add(cell)
                cluster.append(cell)
                cx, cy = cell
                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),
                                (-1,-1),(-1,1),(1,-1),(1,1)]:
                    neighbor = (cx+dx, cy+dy)
                    if neighbor in frontier_set and neighbor not in visited:
                        queue.append(neighbor)

            if len(cluster) >= min_size:
                mean_x = sum(c[0] for c in cluster) // len(cluster)
                mean_y = sum(c[1] for c in cluster) // len(cluster)
                clusters.append((mean_x, mean_y))

        return clusters

    def get_best_frontier(self, robot_cx, robot_cy, grid, width, height):
        frontiers = self.find_frontiers(grid, width, height)
        if not frontiers:
            print("[FrontierExplorer] No queden frontiers. Mapa complet!")
            return None

        clusters = self.cluster_frontiers(frontiers)
        if not clusters:
            print("[FrontierExplorer] No hi ha clusters prou grans.")
            return None

        candidates = [c for c in clusters if c not in self.visited_frontiers]
        if not candidates:
            print("[FrontierExplorer] Tots els frontiers visitats.")
            return None

        best = min(candidates, key=lambda c: math.sqrt(
            (c[0]-robot_cx)**2 + (c[1]-robot_cy)**2
        ))
        return best

    def explore_step(self, robot_wx, robot_wy):
        # Fa una còpia thread-safe del grid
        with self.path_planner._map_lock:
            if self.path_planner.grid is None:
                print("[FrontierExplorer] No hi ha mapa disponible.")
                return None
            grid_copy = self.path_planner.grid.copy()
            width  = self.path_planner.width
            height = self.path_planner.height

        robot_cx, robot_cy = self.path_planner.world_to_cell(robot_wx, robot_wy)

        best = self.get_best_frontier(robot_cx, robot_cy, grid_copy, width, height)

        if best is None:
            return None

        # Marca com a visitat sempre, tant si hi ha ruta com si no
        self.visited_frontiers.add(best)

        goal_wx, goal_wy = self.path_planner.cell_to_world(best[0], best[1])
        print(f"[FrontierExplorer] Frontier objectiu: cel·la {best} → món ({goal_wx:.2f}, {goal_wy:.2f})")

        waypoints = self.path_planner.plan(robot_wx, robot_wy, goal_wx, goal_wy)

        if waypoints is None:
            print(f"[FrontierExplorer] No hi ha ruta a aquest frontier, buscant el següent...")
            return "no_route"

        return waypoints

    def reset(self):
        self.visited_frontiers.clear()
        print("[FrontierExplorer] Exploració reiniciada.")