import { useEffect } from 'react';
import useSceneStore from '../store/useSceneStore';

const useKeyboardControls = () => {
  const { selectedId, setSelection, updateFurnitureTransform } = useSceneStore();

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!selectedId) return;

      switch (e.key.toLowerCase()) {
        case 'delete':
        case 'backspace':
          // Logic to remove from sceneGraph
          break;
        case 'escape':
          setSelection(null);
          break;
        case 'r':
          // Potential toggle to rotation mode for Gizmo
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedId, setSelection]);
};

export default useKeyboardControls;
