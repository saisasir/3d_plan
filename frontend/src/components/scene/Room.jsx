import React, { useMemo } from 'react';
import { Shape, RepeatWrapping, DoubleSide } from 'three';
import { useTexture } from '@react-three/drei';
import useSceneStore from '../../store/useSceneStore';

// Texture configs per material type
const TEXTURE_CONFIG = {
  wood:     { folder: 'wood',     repeat: 0.3, maps: ['diffuse', 'bump', 'roughness'] },
  tiles:    { folder: 'tiles',    repeat: 0.5, maps: ['diffuse', 'normal'] },
  concrete: { folder: 'concrete', repeat: 0.4, maps: ['diffuse', 'normal'] },
  brick:    { folder: 'brick',    repeat: 0.2, maps: ['diffuse', 'bump'] },
};

// Room type → subtle floor tint (multiplied with texture)
const ROOM_TINTS = {
  living_room:  '#faf5ee',
  bedroom:      '#f5f0e8',
  kitchen:      '#eef2f2',
  bathroom:     '#e8f0f5',
  dining_room:  '#f8f2e8',
  hallway:      '#f0f0f0',
  balcony:      '#eef5ee',
  room:         '#f5f5f5',
};

/**
 * Room floor renderer with optional ceiling.
 * polygon: [[x, z], ...] in meter space
 */
const RoomFloor = ({ polygon, texture = 'wood', id, name, center, type = 'room' }) => {
  const floorTexture = useSceneStore(s => s.floorTexture);
  const showCeiling = useSceneStore(s => s.showCeiling);
  const wallHeight = useSceneStore(s => s.wallHeight);

  const effectiveTexture = floorTexture !== 'wood' ? floorTexture : texture;
  const config = TEXTURE_CONFIG[effectiveTexture] || TEXTURE_CONFIG.wood;
  const tint = ROOM_TINTS[type] || ROOM_TINTS.room;

  const mapPaths = useMemo(() => {
    const p = {};
    if (config.maps.includes('diffuse')) p.map = `/textures/${config.folder}/diffuse.jpg`;
    if (config.maps.includes('bump')) p.bumpMap = `/textures/${config.folder}/bump.jpg`;
    if (config.maps.includes('normal')) p.normalMap = `/textures/${config.folder}/normal.jpg`;
    if (config.maps.includes('roughness')) p.roughnessMap = `/textures/${config.folder}/roughness.jpg`;
    return p;
  }, [config]);

  // Simplified texture loading to prevent suspension issues
  const textures = useTexture(mapPaths);

  useMemo(() => {
    if (!textures) return;
    Object.values(textures).forEach(tex => {
      if (tex) {
        tex.wrapS = tex.wrapT = RepeatWrapping;
        tex.repeat.set(config.repeat, config.repeat);
      }
    });
  }, [textures, config.repeat]);

  const shape = useMemo(() => {
    if (!polygon || polygon.length < 3) return null;
    const s = new Shape();
    s.moveTo(polygon[0][0], polygon[0][1]);
    for (let i = 1; i < polygon.length; i++) {
      s.lineTo(polygon[i][0], polygon[i][1]);
    }
    s.closePath();
    return s;
  }, [polygon]);

  if (!shape) return null;

  return (
    <group>
      {/* Floor */}
      <group rotation={[Math.PI / 2, 0, 0]} onClick={(e) => {
        e.stopPropagation();
        useSceneStore.getState().setSelection(id);
      }}>
        <mesh receiveShadow>
          <shapeGeometry args={[shape]} />
          <meshStandardMaterial
            {...textures}
            color={useSceneStore.getState().selectedId === id ? "#4fc3f7" : tint}
            roughness={config.folder === 'wood' ? 0.6 : 0.8}
            metalness={0.1}
            bumpScale={0.01}
            normalScale={[0.1, 0.1]}
            side={DoubleSide}
          />
        </mesh>
      </group>

      {/* Ceiling (optional, slightly translucent) */}
      {showCeiling && (
        <group rotation={[Math.PI / 2, 0, 0]} position={[0, wallHeight, 0]}>
          <mesh>
            <shapeGeometry args={[shape]} />
            <meshStandardMaterial
              color="#ffffff"
              roughness={0.95}
              metalness={0.0}
              side={DoubleSide}
              transparent
              opacity={0.85}
            />
          </mesh>
        </group>
      )}

    </group>
  );
};

export default RoomFloor;
