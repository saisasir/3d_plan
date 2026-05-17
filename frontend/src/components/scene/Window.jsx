import React from 'react';

/**
 * Window component — renders a glass pane with frame.
 * Props:
 *   position: [x, y, z] world coords
 *   width: window width in meters
 *   height: window height (default 1.2)
 *   rotation: y-axis rotation
 */
const Window = ({ position = [0, 0, 0], width = 1.0, height = 1.2, rotation = 0 }) => {
  const frameThickness = 0.04;
  const frameDepth = 0.12;
  const glassThickness = 0.01;

  const elevation = 0.9; // 90cm from floor

  return (
    <group position={[position[0], elevation, position[2]]} rotation={[0, rotation, 0]}>
      {/* Window frame - outer */}
      {/* Top */}
      <mesh position={[0, height - frameThickness / 2, 0]}>
        <boxGeometry args={[width + frameThickness * 2, frameThickness, frameDepth]} />
        <meshStandardMaterial color="#c0c0c0" roughness={0.3} metalness={0.6} />
      </mesh>
      {/* Bottom */}
      <mesh position={[0, frameThickness / 2, 0]}>
        <boxGeometry args={[width + frameThickness * 2, frameThickness, frameDepth]} />
        <meshStandardMaterial color="#c0c0c0" roughness={0.3} metalness={0.6} />
      </mesh>
      {/* Left */}
      <mesh position={[-width / 2 - frameThickness / 2, height / 2, 0]}>
        <boxGeometry args={[frameThickness, height, frameDepth]} />
        <meshStandardMaterial color="#c0c0c0" roughness={0.3} metalness={0.6} />
      </mesh>
      {/* Right */}
      <mesh position={[width / 2 + frameThickness / 2, height / 2, 0]}>
        <boxGeometry args={[frameThickness, height, frameDepth]} />
        <meshStandardMaterial color="#c0c0c0" roughness={0.3} metalness={0.6} />
      </mesh>

      {/* Center divider (vertical) */}
      <mesh position={[0, height / 2, 0]}>
        <boxGeometry args={[frameThickness * 0.6, height - frameThickness * 2, frameDepth * 0.8]} />
        <meshStandardMaterial color="#c0c0c0" roughness={0.3} metalness={0.6} />
      </mesh>

      {/* Center divider (horizontal) */}
      <mesh position={[0, height / 2, 0]}>
        <boxGeometry args={[width - frameThickness, frameThickness * 0.6, frameDepth * 0.8]} />
        <meshStandardMaterial color="#c0c0c0" roughness={0.3} metalness={0.6} />
      </mesh>

      {/* Glass panes */}
      <mesh position={[0, height / 2, 0]}>
        <boxGeometry args={[width - frameThickness, height - frameThickness * 2, glassThickness]} />
        <meshPhysicalMaterial
          color="#87CEEB"
          transparent
          opacity={0.25}
          roughness={0.0}
          metalness={0.1}
          transmission={0.8}
          thickness={0.1}
        />
      </mesh>
    </group>
  );
};

export default Window;
