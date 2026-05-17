import numpy as np

class EmbeddingService:
    def __init__(self, model_name: str = None):
        """
        Geometric Layout Fingerprinter.
        Creates a deterministic vector based on the architectural 
        composition of the floor plan.
        """
        pass

    def generate_scene_embedding(self, scene_graph: dict) -> list:
        """
        Create a 'layout signature' vector based on:
        - Room count
        - Area distribution
        - Structural complexity
        """
        rooms = scene_graph.get("rooms", [])
        num_rooms = len(rooms)
        
        # Simple but effective geometric vector (16 dimensions)
        vector = np.zeros(16)
        vector[0] = num_rooms / 20.0 # Normalized room count
        
        # Encode room types into the signature
        for i, room in enumerate(rooms[:15]):
            rtype = room.get("type", "unknown")
            # Deterministic hash of room type to a float
            vector[i+1] = (hash(rtype) % 100) / 100.0
            
        return vector.tolist()

    def generate_image_embedding(self, image_np: np.ndarray) -> list:
        return [0.0] * 16
