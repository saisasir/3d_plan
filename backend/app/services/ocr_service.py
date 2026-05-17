import easyocr
import numpy as np
from typing import List, Dict
from shapely.geometry import Point, Polygon

class OCRService:
    def __init__(self):
        # Initialize EasyOCR with English
        self.reader = easyocr.Reader(['en'])

    def extract_room_labels(self, image: np.ndarray, rooms: List[Dict]) -> List[Dict]:
        """
        Reads text from the floor plan and assigns it to the corresponding room polygon.
        """
        results = self.reader.readtext(image)
        labeled_rooms = []

        for room in rooms:
            poly_points = room.get("polygon", [])
            if len(poly_points) < 3:
                continue
            
            room_poly = Polygon(poly_points)
            room_label = "Unnamed Room"
            
            # Find if any detected text falls inside this room's polygon
            for (bbox, text, prob) in results:
                # Calculate center of text bbox
                center_x = sum([p[0] for p in bbox]) / 4
                center_y = sum([p[1] for p in bbox]) / 4
                
                if room_poly.contains(Point(center_x, center_y)):
                    room_label = text
                    break # Take the first match for now
            
            room["name"] = room_label
            labeled_rooms.append(room)
            
        return labeled_rooms
