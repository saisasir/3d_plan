import React, { Suspense, useRef, useEffect } from 'react';
import {
  SoftShadows, ContactShadows, Environment,
  TransformControls, Text, Grid, Sky, Bvh
} from '@react-three/drei';
// import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing';
import { useThree } from '@react-three/fiber';
import gsap from 'gsap';
import useSceneStore from '../store/useSceneStore';

import Wall      from '../components/scene/Wall';
import RoomFloor from '../components/scene/Room';
import Furniture from '../components/scene/Furniture';
import Door      from '../components/scene/Door';
import Window    from '../components/scene/Window';

/** Auto-frame the camera to fit the scene extents */
const AutoCamera = ({ metadata, viewMode }) => {
  const { camera, controls } = useThree();

  useEffect(() => {
    if (!metadata?.width_m) return;
    const w = metadata.width_m || 10;
    const d = metadata.depth_m || 10;
    const maxDim = Math.max(w, d);
    const dist = maxDim * 0.9;
    
    if (viewMode === '2D') {
      // Fly to top-down view
      gsap.to(camera.position, {
        x: 0, y: dist * 1.5, z: 0,
        duration: 1.2,
        ease: 'power2.inOut',
        onUpdate: () => {
          camera.lookAt(0, 0, 0);
        }
      });
      if (controls) {
        gsap.to(controls.target, { x: 0, y: 0, z: 0, duration: 1.2 });
      }
    } else {
      // Fly to perspective view
      gsap.to(camera.position, {
        x: dist * 0.8, y: dist * 0.7, z: dist * 0.8,
        duration: 1.5,
        ease: 'power3.inOut',
        onUpdate: () => {
          camera.lookAt(0, 0, 0);
        }
      });
      if (controls) {
        gsap.to(controls.target, { x: 0, y: 0, z: 0, duration: 1.5 });
      }
    }
    
    camera.near = 0.1;
    camera.far = dist * 10;
    camera.updateProjectionMatrix();
  }, [metadata, camera, viewMode, controls]);

  return null;
};

/** Room label floating above floor centroid */
const RoomLabel = ({ center, name, area_m2, type }) => {
  if (!center || !name) return null;
  return (
    <group position={[center[0], 0.08, center[1]]}>
      <Text
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.22}
        color="#333"
        anchorX="center"
        anchorY="middle"
        font={undefined}
        outlineWidth={0.01}
        outlineColor="#fff"
      >
        {name}
      </Text>
      {area_m2 && (
        <Text
          position={[0, 0, 0.3]}
          rotation={[-Math.PI / 2, 0, 0]}
          fontSize={0.14}
          color="#666"
          anchorX="center"
          anchorY="middle"
          font={undefined}
          outlineWidth={0.005}
          outlineColor="#fff"
        >
          {`${area_m2} m²`}
        </Text>
      )}
    </group>
  );
};

const SceneEngine = ({ viewMode }) => {
  const { sceneGraph, selectedId, updateFurnitureTransform, setSelection, wallHeight } = useSceneStore();
  const groupRef = useRef();
  const targetRef = useRef();

  useEffect(() => {
    if (groupRef.current) window.sceneGroup = groupRef.current;
  }, []);

  const hasContent = sceneGraph.rooms.length > 0 || sceneGraph.walls.length > 0;

  return (
    <group ref={groupRef}>
      <AutoCamera metadata={sceneGraph.metadata} viewMode={viewMode} />
      
      {viewMode === '3D' && <Sky sunPosition={[100, 20, 100]} />}
      
      <SoftShadows size={viewMode === '2D' ? 0 : 40} samples={16} focus={0.5} />
      
      {/* Primary Light (Sun) */}
      <directionalLight
        position={[15, 25, 15]}
        intensity={viewMode === '2D' ? 0.8 : 1.5}
        color="#fffaf0"
        castShadow={viewMode === '3D'}
        shadow-mapSize={[2048, 2048]}
        shadow-camera-near={0.5}
        shadow-camera-far={100}
        shadow-camera-left={-40}
        shadow-camera-right={40}
        shadow-camera-top={40}
        shadow-camera-bottom={-40}
        shadow-bias={-0.0005}
      />
      
      {/* Soft Ambient / Fill */}
      <ambientLight intensity={viewMode === '2D' ? 0.9 : 0.4} />
      <hemisphereLight intensity={0.5} color="#ffffff" groundColor="#b9d5ff" />
      
      {/* Secondary Fill Light */}
      <directionalLight
        position={[-15, 15, -5]}
        intensity={viewMode === '2D' ? 0 : 0.6}
        color="#e6f2ff"
      />

      {viewMode === '3D' && <Environment preset="apartment" />}

      {/* Ground grid (only when no content or in 2D mode) */}
      {(!hasContent || viewMode === '2D') && (
        <Grid
          position={[0, -0.01, 0]}
          args={[50, 50]}
          cellSize={1}
          cellThickness={0.5}
          cellColor={viewMode === '2D' ? "#e2e8f0" : "#334155"}
          sectionSize={5}
          sectionThickness={1.5}
          sectionColor={viewMode === '2D' ? "#cbd5e1" : "#475569"}
          fadeDistance={100}
          infiniteGrid
        />
      )}

      {/* Ground plane when content exists (Premium Studio Floor) */}
      {hasContent && viewMode === '3D' && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, 0]} receiveShadow>
          <planeGeometry args={[150, 150]} />
          <meshStandardMaterial 
            color="#f1f5f9" 
            roughness={0.9} 
            metalness={0.0}
          />
        </mesh>
      )}
      {hasContent && viewMode === '2D' && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, 0]}>
          <planeGeometry args={[1000, 1000]} />
          <meshStandardMaterial color="#f8fafc" />
        </mesh>
      )}

      {/* ── Rooms (floors + ceilings) ── */}
      <Suspense fallback={null}>
        {sceneGraph.rooms.map((room) => (
          <React.Fragment key={room.id}>
            <RoomFloor {...room} viewMode={viewMode} />
            <RoomLabel
              center={room.center}
              name={room.name}
              area_m2={room.area_m2}
              type={room.type}
              viewMode={viewMode}
            />
          </React.Fragment>
        ))}
      </Suspense>

      {/* ── Walls ── */}
      {sceneGraph.walls.map((wall, i) => (
        <Wall
          key={`wall-${i}`}
          points={wall.points}
          thickness={wall.thickness ?? 0.15}
          height={wall.height ?? wallHeight}
          openings={wall.openings ?? []}
          viewMode={viewMode}
        />
      ))}

      {/* ── Openings (Doors & Windows) ── */}
      {sceneGraph.openings.map((opening, i) => {
        if (opening.type === 'door') {
          return (
            <Door
              key={`door-${i}`}
              position={opening.position}
              width={opening.width || 0.9}
              height={opening.height || 2.1}
              rotation={opening.rotation || 0}
              viewMode={viewMode}
            />
          );
        }
        if (opening.type === 'window') {
          return (
            <Window
              key={`window-${i}`}
              position={opening.position}
              width={opening.width || 1.0}
              height={opening.height || 1.2}
              rotation={opening.rotation || 0}
            />
          );
        }
        return null;
      })}

      {/* ── Furniture ── */}
      <Suspense fallback={null}>
        {sceneGraph.furniture.map((item) => (
          <Furniture
            key={item.id}
            id={item.id}
            type={item.type}
            position={item.position}
            rotation={item.rotation}
            scale={item.scale}
            onSelect={(obj) => { targetRef.current = obj; }}
          />
        ))}
      </Suspense>

      {/* ── Transform Gizmo ── */}
      {selectedId && targetRef.current && (
        <TransformControls
          object={targetRef.current}
          mode="translate"
          onMouseUp={() => {
            if (targetRef.current) {
              updateFurnitureTransform(
                selectedId,
                targetRef.current.position,
                targetRef.current.rotation
              );
            }
          }}
        />
      )}

      <ContactShadows
        position={[0, -0.005, 0]}
        opacity={0.4}
        scale={40}
        blur={2}
        far={5}
      />

      {/* Postprocessing disabled temporarily to resolve version-specific crash */}
      {/* 
      {viewMode === '3D' && (
        <EffectComposer multisampling={4}>
          <Bloom 
            intensity={0.4} 
            luminanceThreshold={0.9} 
          />
          <Vignette 
            offset={0.3} 
            darkness={0.5} 
          />
        </EffectComposer>
      )} 
      */}
    </group>
  );
};

export default SceneEngine;
