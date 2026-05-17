import React from 'react';

/**
 * Door component — simple door frame indicator.
 * Kept minimal to avoid visual clutter.
 */
const Door = ({ position = [0, 0, 0], width = 0.9, height = 2.1, rotation = 0 }) => {
  const frameThickness = 0.04;
  const frameDepth = 0.15;

  return (
    <group position={position} rotation={[0, rotation, 0]}>
      {/* Door frame - top */}
      <mesh position={[0, height - frameThickness / 2, 0]}>
        <boxGeometry args={[width, frameThickness, frameDepth]} />
        <meshStandardMaterial color="#6B4226" roughness={0.6} />
      </mesh>

      {/* Door frame - left */}
      <mesh position={[-width / 2, height / 2, 0]}>
        <boxGeometry args={[frameThickness, height, frameDepth]} />
        <meshStandardMaterial color="#6B4226" roughness={0.6} />
      </mesh>

      {/* Door frame - right */}
      <mesh position={[width / 2, height / 2, 0]}>
        <boxGeometry args={[frameThickness, height, frameDepth]} />
        <meshStandardMaterial color="#6B4226" roughness={0.6} />
      </mesh>
    </group>
  );
};

export default Door;
