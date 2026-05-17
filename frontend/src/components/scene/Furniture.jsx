import React, { useRef, useEffect } from 'react';
import { useGLTF } from '@react-three/drei';
import gsap from 'gsap';
import useSceneStore from '../../store/useSceneStore';

const MODEL_PATHS = {
  sofa:         '/models/sofa.glb',
  bed:          '/models/bed.glb',
  chair:        '/models/chair.glb',
  coffee_table: '/models/chair.glb',
  default:      '/models/chair.glb',
};

const FurnitureMesh = ({ id, type, position, rotation = 0, scale = [1,1,1], onSelect, viewMode }) => {
  const ref = useRef();
  const { selectedId, setSelection } = useSceneStore();
  const isSelected = selectedId === id;
  const modelPath = MODEL_PATHS[type] || MODEL_PATHS.default;

  useEffect(() => {
    if (!ref.current) return;
    if (viewMode === '3D') {
      gsap.to(ref.current.position, { y: position[1], duration: 1.0, delay: 0.2, ease: 'back.out(1.7)' });
      gsap.to(ref.current.scale, { x: scale[0], y: scale[1], z: scale[2], duration: 1.0, delay: 0.2 });
    } else {
      gsap.to(ref.current.position, { y: -0.5, duration: 0.5 });
      gsap.to(ref.current.scale, { x: 0, y: 0, z: 0, duration: 0.5 });
    }
  }, [viewMode, position, scale]);

  let scene = null;
  try {
    const gltf = useGLTF(modelPath);
    scene = gltf.scene;
  } catch {
    return null;
  }

  return (
    <primitive
      ref={ref}
      object={scene.clone()}
      position={[position[0], viewMode === '3D' ? position[1] : -0.5, position[2]]}
      rotation={[0, rotation, 0]}
      scale={viewMode === '3D' ? scale : [0,0,0]}
      onClick={(e) => {
        e.stopPropagation();
        setSelection(id);
        onSelect && onSelect(ref.current);
      }}
    >
      {isSelected && (
        <group position={[0, 0.01, 0]} rotation={[-Math.PI/2, 0, 0]}>
          <mesh>
            <ringGeometry args={[0.8, 0.85, 32]} />
            <meshBasicMaterial color="#00d4ff" transparent opacity={0.8} />
          </mesh>
          <mesh>
            <circleGeometry args={[0.8, 32]} />
            <meshBasicMaterial color="#00d4ff" transparent opacity={0.1} />
          </mesh>
        </group>
      )}
    </primitive>
  );
};

const Furniture = (props) => {
  return <FurnitureMesh {...props} />;
};

export default Furniture;
