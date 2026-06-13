import math

class CoordinateTransformer:
    def __init__(self, origin_lat, origin_lon, yaw_offset_rad=0.0):
        """
        :param origin_lat: Latitud GPS exacta de donde se enciende el robot (X=0, Y=0 del mapa SLAM)
        :param origin_lon: Longitud GPS exacta del origen.
        :param yaw_offset_rad: Cuántos radianes está girado el mapa SLAM respecto al Norte real de Google Maps.
        """
        self.origin_lat = math.radians(origin_lat)
        self.origin_lon = math.radians(origin_lon)
        self.yaw_offset = yaw_offset_rad
        self.R = 6371000.0  # Radio de la Tierra en metros

    def gps_to_local(self, target_lat, target_lon):
        """Convierte coordenadas GPS (Google Maps) en metros X, Y (ROS)."""
        if target_lat is None or target_lon is None:
            return None, None
            
        lat = math.radians(target_lat)
        lon = math.radians(target_lon)

        # Distancias en metros asumiendo superficie plana (válido para distancias < 5km)
        dx_meters = self.R * math.cos(self.origin_lat) * (lon - self.origin_lon)
        dy_meters = self.R * (lat - self.origin_lat)

        # Rotamos las coordenadas si tu mapa SLAM no mira al Norte exacto
        local_x = dx_meters * math.cos(self.yaw_offset) - dy_meters * math.sin(self.yaw_offset)
        local_y = dx_meters * math.sin(self.yaw_offset) + dy_meters * math.cos(self.yaw_offset)

        return local_x, local_y

    def local_to_gps(self, local_x, local_y):
        """Convierte los metros X, Y del robot (Lidar) a GPS para mandarlo a la BD."""
        # Deshacemos la rotación
        dx_meters = local_x * math.cos(-self.yaw_offset) - local_y * math.sin(-self.yaw_offset)
        dy_meters = local_x * math.sin(-self.yaw_offset) + local_y * math.cos(-self.yaw_offset)

        lon = self.origin_lon + (dx_meters / (self.R * math.cos(self.origin_lat)))
        lat = self.origin_lat + (dy_meters / self.R)

        return math.degrees(lat), math.degrees(lon)