import React, { useMemo, useRef, useEffect } from 'react';
import { Shape, Vector2, ExtrudeGeometry, Path } from 'three';
import { Edges } from '@react-three/drei';
import gsap from 'gsap';
import useSceneStore from '../../store/useSceneStore';

/**
 * Wall segment renderer with optional door/window cutouts.
 * props.points: [[x1, z1], [x2, z2]] in meters
 * props.height: wall height in meters (default 2.7)
 * props.thickness: wall thickness in meters (default 0.15)
 * props.openings: [{ position, width, height, elevation, type }]
 */
const Wall = ({ points, thickness = 0.12, height = 2.7, openings = [], viewMode = '3D' }) => {
  const meshRef = useRef();

  useEffect(() => {
    if (!meshRef.current) return;
    if (viewMode === '3D') {
      gsap.to(meshRef.current.scale, { y: 1, duration: 1.2, ease: 'power2.out' });
      gsap.to(meshRef.current.position, { y: 0, duration: 1.2, ease: 'power2.out' });
    } else {
      gsap.to(meshRef.current.scale, { y: 0.01, duration: 0.8, ease: 'power2.inOut' });
      gsap.to(meshRef.current.position, { y: 0, duration: 0.8, ease: 'power2.inOut' });
    }
  }, [viewMode]);

  const { geometry, center, rotation } = useMemo(() => {
    if (!points || points.length < 2) return { geometry: null };

    const p1 = new Vector2(points[0][0], points[0][1]);
    const p2 = new Vector2(points[1][0], points[1][1]);
    const wallLen = p1.distanceTo(p2);
    if (wallLen < 0.1) return { geometry: null };

    // Elevation Shape (Width x Height)
    const s = new Shape();
    s.moveTo(0, 0);
    s.lineTo(wallLen, 0);
    s.lineTo(wallLen, height);
    s.lineTo(0, height);
    s.closePath();

    // Cut holes for doors/windows
    openings.forEach(op => {
      // Calculate relative position on wall
      const hole = new Path();
      // Clamp width so it doesn't exceed 95% of the wall length
      const hw = Math.min(op.width || 0.9, wallLen * 0.95);
      const hh = op.height || 2.1;
      
      // Clamp position so the hole is completely inside the wall
      let hx = op.wall_pos !== undefined ? op.wall_pos : (wallLen / 2);
      hx = Math.max(hw/2 + 0.01, Math.min(wallLen - hw/2 - 0.01, hx));
      
      const hy = op.elevation || 0;

      hole.moveTo(hx - hw/2, hy);
      hole.lineTo(hx + hw/2, hy);
      hole.lineTo(hx + hw/2, hy + hh);
      hole.lineTo(hx - hw/2, hy + hh);
      hole.closePath();
      s.holes.push(hole);
    });

    const geo = new ExtrudeGeometry(s, {
      depth: thickness,
      bevelEnabled: true,
      bevelThickness: 0.01,
      bevelSize: 0.01,
      bevelSegments: 3
    });

    // Center the geometry so that its local origin is at the center of the wall segment
    geo.translate(-wallLen / 2, 0, -thickness / 2);

    // Center and rotate
    const mid = p1.clone().add(p2).multiplyScalar(0.5);
    const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x);

    return { 
      geometry: geo, 
      center: [mid.x, 0, mid.y], 
      rotation: -angle 
    };
  }, [points, thickness, height, openings]);

  if (!geometry) return null;

  return (
    <mesh
      ref={meshRef}
      geometry={geometry}
      position={center}
      rotation={[0, rotation, 0]}
      scale={[1, viewMode === '3D' ? 1 : 0.01, 1]}
      castShadow
      receiveShadow
      onClick={(e) => {
        e.stopPropagation();
        const wallId = `wall-${points[0].join(',')}-${points[1].join(',')}`;
        useSceneStore.getState().setSelection(wallId);
      }}
    >
      <meshStandardMaterial
        color={useSceneStore.getState().selectedId?.startsWith('wall') && useSceneStore.getState().selectedId.includes(points[0].join(',')) ? "#4fc3f7" : "#ffffff"}
        roughness={0.9}
        metalness={0.0}
      />
      <Edges color="#d1d5db" threshold={15} />
    </mesh>
  );
};

export default Wall;
