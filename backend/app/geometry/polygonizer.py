import numpy as np
from shapely.geometry import Polygon, LineString, mapping
from typing import List, Dict

class GeometryPolygonizer:
    @staticmethod
    def clean_room_polygon(raw_polygon: List[List[float]]):
        """
        Simplify and clean a room polygon detected by AI.
        """
        if len(raw_polygon) < 3:
            return raw_polygon
            
        # Convert to Shapely
        poly = Polygon(raw_polygon)
        
        # Simplify geometry (tolerance in pixels)
        # Increase tolerance to 15.0 to smooth out jagged neural mask edges
        simplified = poly.simplify(15.0, preserve_topology=True)
        
        # Extract coordinates
        clean_coords = list(simplified.exterior.coords)
        
        return clean_coords

    @staticmethod
    def create_scene_graph(rooms: List[Dict], walls: List[Dict], metadata: Dict):
        """
        Final assembly of the JSON scene graph for the 3D frontend.
        """
        return {
            "metadata": metadata,
            "rooms": rooms,
            "walls": walls,
            "furniture": [],  # To be filled by Optimizer
            "openings": []    # To be filled by Detector
        }
