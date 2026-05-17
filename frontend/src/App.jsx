import React, { useState, useCallback } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera } from '@react-three/drei';
import {
  Upload, Box, Layers, Settings, Play, Download,
  Sparkles, ShieldCheck, CheckCircle2, Zap, AlertCircle,
  Home, Ruler, Eye, RotateCcw, Cuboid, EyeOff
} from 'lucide-react';
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js';
import { MeshStandardMaterial } from 'three';
import { motion, AnimatePresence } from 'framer-motion';

import SceneEngine from './engine/SceneEngine';
import { SidebarItem, AssetCard } from './components/ui/Sidebar';
import useSceneStore from './store/useSceneStore';
import useKeyboardControls from './hooks/useKeyboardControls';
import AdminDashboard from './components/admin/AdminDashboard';

const BACKEND = 'http://localhost:8002';

const STEPS = [
  { label: 'Preprocessing',    icon: Layers,  detail: 'Deskewing and normalizing floor plan image...' },
  { label: 'Room Detection',   icon: Home,    detail: 'Extracting room polygons and boundaries...' },
  { label: 'Wall Extraction',  icon: Ruler,   detail: 'Detecting walls, doors & windows...' },
  { label: 'Scene Building',   icon: Box,     detail: 'Building meter-scale 3D scene graph...' },
  { label: '3D Ready',         icon: Eye,     detail: 'Rendering interactive 3D model...' },
];

const App = () => {
  useKeyboardControls();
  const {
    setSceneGraph, isWalkthrough, sceneGraph, wallHeight,
    setWallHeight, setFloorTexture, showCeiling, toggleCeiling,
    selectedId, updateFurnitureTransform, setSelection,
    isAutoRotating
  } = useSceneStore();

  const [activeTab,    setActiveTab]    = useState('assets');
  const [viewMode,     setViewMode]     = useState('3D');
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStep,  setCurrentStep]  = useState(0);
  const [error,        setError]        = useState(null);
  const [isDragging,   setIsDragging]   = useState(false);
  const [isAdminView,  setIsAdminView]  = useState(false);

  const processFile = useCallback(async (file) => {
    if (!file) return;
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['jpg', 'jpeg', 'png', 'pdf'].includes(ext)) {
      setError('Unsupported format. Use JPG, PNG, or PDF.');
      return;
    }

    setIsProcessing(true);
    setCurrentStep(0);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    let step = 0;
    const tick = setInterval(() => {
      step = Math.min(step + 1, STEPS.length - 2);
      setCurrentStep(step);
    }, 1800);

    try {
      const res = await fetch(`${BACKEND}/api/v1/upload`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(tick);

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error ${res.status}`);
      }

      const result = await res.json();
      setCurrentStep(STEPS.length - 1);
      setSceneGraph(result.scene_graph);

      setTimeout(() => setIsProcessing(false), 800);
    } catch (err) {
      clearInterval(tick);
      setIsProcessing(false);
      setError(err.message || 'AI pipeline failed. Is the backend running?');
    }
  }, [setSceneGraph]);

  const handleFileInput = (e) => processFile(e.target.files[0]);
  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);

    const assetType = e.dataTransfer.getData("type");
    if (assetType) {
      const assetName = e.dataTransfer.getData("name");
      // Map name to model type (basic fallback logic)
      let modelType = "chair";
      if (assetName.toLowerCase().includes("sofa")) modelType = "sofa";
      if (assetName.toLowerCase().includes("bed")) modelType = "bed";
      if (assetName.toLowerCase().includes("table")) modelType = "coffee_table";

      useSceneStore.getState().addFurniture({
        type: modelType,
        position: [0, 0, 0], // Drop exactly at center for now
        rotation: 0,
        scale: [1, 1, 1]
      });
      return;
    }

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFile(e.dataTransfer.files[0]);
    }
  }, [processFile]);

  const handleExport = () => {
    try {
      const scene = window.sceneGroup;
      if (!scene) {
        setError("3D scene not ready yet. Please upload a floor plan first.");
        return;
      }

      // Safe recursive clone that skips cameras, lights, text, and handles weird materials
      const safeClone = (obj) => {
        if (!obj) return null;
        if (obj.isLight || obj.isCamera || obj.isHelper) return null;
        
        // Skip Troika/drei Text components (room labels, etc.)
        if (
          obj.text !== undefined || 
          obj.isText || 
          obj.constructor.name === 'Text' || 
          obj.name?.toLowerCase().includes('text')
        ) {
          return null;
        }
        
        let cloned;
        if (obj.isMesh) {
          let clonedMat;
          if (obj.material) {
            if (Array.isArray(obj.material)) {
              clonedMat = obj.material.map(m => {
                try {
                  return m.clone();
                } catch (e) {
                  console.warn("Failed to clone material, falling back to MeshStandardMaterial:", e);
                  return new MeshStandardMaterial({ color: m.color || 0xcccccc, roughness: 0.8 });
                }
              });
            } else {
              try {
                clonedMat = obj.material.clone();
              } catch (e) {
                console.warn("Failed to clone material, falling back to MeshStandardMaterial:", e);
                clonedMat = new MeshStandardMaterial({ color: obj.material.color || 0xcccccc, roughness: 0.8 });
              }
            }

            // Clean up empty/invalid texture maps to prevent GLTFExporter failure
            const materials = Array.isArray(clonedMat) ? clonedMat : [clonedMat];
            materials.forEach(mat => {
              ['map', 'normalMap', 'roughnessMap', 'metalnessMap', 'emissiveMap', 'aoMap'].forEach(k => {
                if (mat[k]) {
                  const img = mat[k].image;
                  
                  // Strictly verify that the image is a valid, fully loaded canvas-drawable source
                  const isValid = img && (
                    (typeof HTMLImageElement !== 'undefined' && img instanceof HTMLImageElement && img.complete && img.naturalWidth > 0) ||
                    (typeof HTMLCanvasElement !== 'undefined' && img instanceof HTMLCanvasElement) ||
                    (typeof ImageBitmap !== 'undefined' && img instanceof ImageBitmap) ||
                    (typeof OffscreenCanvas !== 'undefined' && img instanceof OffscreenCanvas)
                  );

                  if (!isValid) {
                    mat[k] = null;
                  }
                }
              });
            });
          }
          cloned = new obj.constructor(obj.geometry, clonedMat);
        } else {
          cloned = new obj.constructor();
        }

        // Copy transform properties
        cloned.name = obj.name;
        cloned.position.copy(obj.position);
        cloned.rotation.copy(obj.rotation);
        cloned.scale.copy(obj.scale);
        cloned.up.copy(obj.up);
        cloned.visible = obj.visible;
        cloned.castShadow = obj.castShadow;
        cloned.receiveShadow = obj.receiveShadow;
        cloned.matrix.copy(obj.matrix);
        cloned.matrixWorld.copy(obj.matrixWorld);
        cloned.matrixAutoUpdate = obj.matrixAutoUpdate;
        
        if (obj.userData) {
          try {
            cloned.userData = JSON.parse(JSON.stringify(obj.userData));
          } catch (e) {
            cloned.userData = {};
          }
        }

        // Recursively clone children
        if (obj.children && obj.children.length > 0) {
          obj.children.forEach(child => {
            const childClone = safeClone(child);
            if (childClone) {
              cloned.add(childClone);
            }
          });
        }

        return cloned;
      };

      const exporter = new GLTFExporter();
      const clone = safeClone(scene);

      if (!clone) {
        setError("Failed to process 3D scene for export.");
        return;
      }

      exporter.parse(
        clone,
        (result) => {
          try {
            const output = result instanceof ArrayBuffer ? result : JSON.stringify(result);
            const blob = new Blob([output], { type: 'application/octet-stream' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `floor3d_${Date.now()}.glb`;
            a.click();
            URL.revokeObjectURL(a.href);
          } catch (blobErr) {
            console.error("Error creating download blob:", blobErr);
            setError("Failed to generate GLB download link.");
          }
        },
        (error) => {
          console.error("GLTFExporter parsing error:", error);
          setError("Failed to parse 3D scene to GLB format.");
        },
        { binary: true }
      );
    } catch (err) {
      console.error("Export handler error:", err);
      setError("An unexpected error occurred during export.");
    }
  };

  const meta = sceneGraph?.metadata || {};
  const hasScene = sceneGraph?.rooms?.length > 0;

  return (
    <div className="app-container">
      <div className="shimmer-top-bar" />

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1 className="logo">FLUX<span>3D</span></h1>
          <p className="logo-sub">Intelligence Engine</p>
        </div>

        <nav className="sidebar-nav">
          <SidebarItem icon={Layers}   label="Floor Plans"  active={activeTab === 'plans'}     onClick={() => setActiveTab('plans')} />
          <SidebarItem icon={Sparkles} label="AI Discovery" active={activeTab === 'discovery'} onClick={() => setActiveTab('discovery')} />
          <SidebarItem icon={Box}      label="Asset Library" active={activeTab === 'assets'}   onClick={() => setActiveTab('assets')} />
          <SidebarItem icon={Settings} label="Settings" />
        </nav>

        <div className="sidebar-catalog-area">
          {activeTab === 'assets' && (
            <div className="catalog-content">
              <span className="label-small">Catalog</span>
              <div className="catalog-grid">
                <AssetCard name="Modern Sofa" />
                <AssetCard name="Lounge Chair" />
                <AssetCard name="King Bed" />
                <AssetCard name="Single Bed" />
                <AssetCard name="Oak Coffee Table" />
                <AssetCard name="Dining Table" />
                <AssetCard name="Office Chair" />
                <AssetCard name="Side Table" />
              </div>
            </div>
          )}
          {activeTab === 'discovery' && (
            <div className="discovery-content">
              <span className="label-small accent-text">Similar Layouts</span>
              <div className="discovery-list">
                {[1,2,3].map(i => (
                  <div key={i} className="discovery-item glass-card">
                    <div className="discovery-header">
                      <span className="label-tiny">MATCH #{i}</span>
                      <span className="match-badge">94%</span>
                    </div>
                    <p className="discovery-desc">3BR / 2BA · Modern Minimalist</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="sidebar-footer">
          <button onClick={() => setIsAdminView(!isAdminView)}
            className={`admin-toggle ${isAdminView ? 'active' : ''}`}>
            <ShieldCheck size={16} />
            <span>{isAdminView ? 'EXIT COMMAND CENTER' : 'COMMAND CENTER'}</span>
          </button>
          <div className="user-profile">
            <div className="user-avatar" />
            <div className="user-info">
              <p className="user-tier">PRO ACCOUNT</p>
              <p className="user-role">Vendor Access</p>
            </div>
          </div>
        </div>
      </aside>

      {isAdminView ? (
        <main className="main-content admin-view"><AdminDashboard /></main>
      ) : (
        <main className="main-content">
          {/* Toolbar */}
          <div className="floating-toolbar">
            <button onClick={() => document.getElementById('upload-input').click()} className="btn-primary">
              <Upload size={14} /> IMPORT PLAN
            </button>
            <input id="upload-input" type="file" accept=".jpg,.jpeg,.png,.pdf"
              style={{ display: 'none' }} onChange={handleFileInput} />

            <div className="toolbar-divider" />

            {hasScene && (
              <>
                <button className="btn-ghost" onClick={() => { setSceneGraph({ rooms:[], walls:[], openings:[], furniture:[], metadata:{} }); }}>
                  <RotateCcw size={14} /> RESET
                </button>
                <div className="toolbar-divider" />
              </>
            )}

            <div className="view-toggle">
              <button 
                className={`view-btn ${viewMode === '3D' ? 'active' : ''}`}
                onClick={() => setViewMode('3D')}
              >
                3D VIEW
              </button>
              <button 
                className={`view-btn ${viewMode === '2D' ? 'active' : ''}`}
                onClick={() => setViewMode('2D')}
              >
                2D PLAN
              </button>
            </div>
            <div className="divider-h" />
            <button 
              className={`play-btn ${isAutoRotating ? 'active' : ''}`}
              onClick={() => useSceneStore.getState().setAutoRotate(!isAutoRotating)}
              title="Auto-Rotate View"
            >
              <Play size={16} fill={isAutoRotating ? "currentColor" : "none"} />
            </button>
          </div>

          {/* Viewport */}
          <div
            className="viewport"
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
          >
            {/* Drop overlay */}
            <AnimatePresence>
              {isDragging && (
                <motion.div
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  style={{
                    position: 'absolute', inset: 0, zIndex: 50,
                    background: 'rgba(0,212,255,0.08)',
                    border: '2px dashed #00d4ff',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    borderRadius: 12, pointerEvents: 'none',
                  }}
                >
                  <p style={{ color: '#00d4ff', fontSize: 18, fontWeight: 600 }}>
                    Drop your floor plan here
                  </p>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Empty state */}
            {!hasScene && !isProcessing && (
              <div style={{
                position: 'absolute', inset: 0, display: 'flex',
                flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                pointerEvents: 'none', gap: 12,
              }}>
                <Upload size={40} color="#555" />
                <p style={{ color: '#666', fontSize: 14 }}>
                  Upload a floor plan (JPG, PNG, PDF) to generate a 3D model
                </p>
                <p style={{ color: '#444', fontSize: 12 }}>
                  or drag & drop here
                </p>
              </div>
            )}

            <Canvas shadows dpr={[1, 2]}>
              <PerspectiveCamera makeDefault position={[0, 20, 0]} fov={50} />
              <OrbitControls
                makeDefault
                minPolarAngle={0}
                maxPolarAngle={viewMode === '2D' ? 0 : Math.PI / 2.05}
                enableRotate={viewMode === '3D'}
                enableDamping
                dampingFactor={0.05}
                autoRotate={isAutoRotating}
                autoRotateSpeed={1.0}
              />
              <SceneEngine viewMode={viewMode} />
            </Canvas>
          </div>

          {/* Error banner */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
                style={{
                  position: 'absolute', bottom: 20, left: '50%', transform: 'translateX(-50%)',
                  background: '#1a0a0a', border: '1px solid #c0392b', borderRadius: 8,
                  padding: '12px 20px', display: 'flex', alignItems: 'center', gap: 10,
                  color: '#e74c3c', fontSize: 13, zIndex: 100, maxWidth: 480,
                }}
              >
                <AlertCircle size={16} />
                {error}
                <button onClick={() => setError(null)} style={{ marginLeft: 8, color: '#999', background: 'none', border: 'none', cursor: 'pointer' }}>✕</button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Processing overlay */}
          <AnimatePresence>
            {isProcessing && (
              <motion.div
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="mission-control-overlay"
              >
                <div className="mission-control-panel glass-card">
                  <div className="panel-glow" />
                  <div className="panel-header">
                    <div className="header-icon"><Zap className="accent-text" /></div>
                    <div>
                      <h2 className="panel-title">AI Pipeline</h2>
                      <span className="label-small">Analyzing floor plan...</span>
                    </div>
                  </div>
                  <div className="steps-container">
                    {STEPS.map((step, idx) => {
                      const Icon = step.icon;
                      const isComplete = idx < currentStep;
                      const isActive = idx === currentStep;
                      return (
                        <div key={idx} className={`step-item ${isActive ? 'active' : isComplete ? 'complete' : 'pending'}`}>
                          <div className="step-icon">
                            {isComplete ? <CheckCircle2 size={16} /> : <Icon size={16} />}
                          </div>
                          <div className="step-details">
                            <p className="step-label">{step.label}</p>
                            {isActive && <p className="step-sub">{idx === 2 ? 'Snapping walls and joining rooms...' : step.detail}</p>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <div className="terminal-logs">
                    <p className="log-line pulse">{'>'} [SYSTEM] PIPELINE ACTIVE...</p>
                    {currentStep > 0 && <p className="log-line ok">{'>'} [OK] PREPROCESSING COMPLETE</p>}
                    {currentStep > 1 && <p className="log-line ok">{'>'} [OK] ROOMS: {sceneGraph?.rooms?.length ?? '...'} DETECTED</p>}
                    {currentStep > 2 && <p className="log-line ok">{'>'} [OK] WALLS: {sceneGraph?.walls?.length ?? '...'} SEGMENTS</p>}
                    {currentStep > 3 && <p className="log-line info">{'>'} [INFO] BUILDING 3D SCENE...</p>}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      )}

      {/* Right property panel */}
      {!isAdminView && (
        <aside className="property-panel">
          <span className="label-small">Properties</span>

          {/* Selected Item Panel */}
          {selectedId && (
            <div className="glass-card property-item" style={{ marginBottom: 12, border: '1px solid #00d4ff' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="label-tiny" style={{ color: '#00d4ff' }}>Selected Item</span>
                <button onClick={() => setSelection(null)} style={{ background: 'none', border: 'none', color: '#666', cursor: 'pointer', fontSize: 10 }}>CLEAR</button>
              </div>
              {(() => {
                const item = sceneGraph.furniture?.find(f => f.id === selectedId);
                const room = sceneGraph.rooms?.find(r => r.id === selectedId);
                
                if (item) {
                  return (
                    <div style={{ marginTop: 8 }}>
                      <p style={{ fontSize: 14, fontWeight: 600, color: '#fff', textTransform: 'capitalize', marginBottom: 8 }}>{item.type.replace('_', ' ')}</p>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                        <div>
                          <span className="label-tiny" style={{ fontSize: 8 }}>POSITION X</span>
                          <input type="number" step="0.1" value={item.position[0].toFixed(2)} 
                            onChange={(e) => updateFurnitureTransform(item.id, { x: parseFloat(e.target.value), y: item.position[1], z: item.position[2] }, { y: item.rotation })}
                            style={{ width: '100%', background: 'rgba(0,0,0,0.5)', border: '1px solid #333', color: '#fff', padding: '4px', borderRadius: 4, fontSize: 12 }} />
                        </div>
                        <div>
                          <span className="label-tiny" style={{ fontSize: 8 }}>POSITION Z</span>
                          <input type="number" step="0.1" value={item.position[2].toFixed(2)} 
                            onChange={(e) => updateFurnitureTransform(item.id, { x: item.position[0], y: item.position[1], z: parseFloat(e.target.value) }, { y: item.rotation })}
                            style={{ width: '100%', background: 'rgba(0,0,0,0.5)', border: '1px solid #333', color: '#fff', padding: '4px', borderRadius: 4, fontSize: 12 }} />
                        </div>
                        <div>
                          <span className="label-tiny" style={{ fontSize: 8 }}>ROTATION (DEG)</span>
                          <input type="number" step="1" value={Math.round(item.rotation * 180 / Math.PI)} 
                            onChange={(e) => updateFurnitureTransform(item.id, { x: item.position[0], y: item.position[1], z: item.position[2] }, { y: (parseFloat(e.target.value) * Math.PI / 180) })}
                            style={{ width: '100%', background: 'rgba(0,0,0,0.5)', border: '1px solid #333', color: '#fff', padding: '4px', borderRadius: 4, fontSize: 12 }} />
                        </div>
                        <div>
                          <span className="label-tiny" style={{ fontSize: 8 }}>SCALE</span>
                          <input type="number" step="0.1" min="0.1" value={item.scale[0]} 
                            onChange={(e) => {
                              const s = parseFloat(e.target.value);
                              useSceneStore.getState().setSceneGraph({
                                ...sceneGraph,
                                furniture: sceneGraph.furniture.map(f => f.id === item.id ? { ...f, scale: [s, s, s] } : f)
                              });
                            }}
                            style={{ width: '100%', background: 'rgba(0,0,0,0.5)', border: '1px solid #333', color: '#fff', padding: '4px', borderRadius: 4, fontSize: 12 }} />
                        </div>
                      </div>
                      <button 
                        onClick={() => {
                          useSceneStore.getState().setSceneGraph({
                            ...sceneGraph,
                            furniture: sceneGraph.furniture.filter(f => f.id !== item.id)
                          });
                          setSelection(null);
                        }}
                        style={{ marginTop: 8, width: '100%', padding: 6, background: '#e74c3c20', color: '#e74c3c', border: '1px solid #e74c3c80', borderRadius: 4, cursor: 'pointer', fontSize: 10, fontWeight: 'bold' }}
                      >
                        DELETE ITEM
                      </button>
                    </div>
                  );
                }

                if (room) {
                  return (
                    <div style={{ marginTop: 8 }}>
                      <p style={{ fontSize: 14, fontWeight: 600, color: '#fff', textTransform: 'capitalize', marginBottom: 8 }}>{room.name}</p>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 8 }}>
                        <div>
                          <span className="label-tiny" style={{ fontSize: 8 }}>ROOM NAME</span>
                          <input type="text" value={room.name} 
                            onChange={(e) => {
                              useSceneStore.getState().setSceneGraph({
                                ...sceneGraph,
                                rooms: sceneGraph.rooms.map(r => r.id === room.id ? { ...r, name: e.target.value } : r)
                              });
                            }}
                            style={{ width: '100%', background: 'rgba(0,0,0,0.5)', border: '1px solid #333', color: '#fff', padding: '4px', borderRadius: 4, fontSize: 12 }} />
                        </div>
                        <div>
                          <span className="label-tiny" style={{ fontSize: 8 }}>MATERIAL</span>
                          <select value={room.texture || 'wood'} 
                            onChange={(e) => {
                              useSceneStore.getState().setSceneGraph({
                                ...sceneGraph,
                                rooms: sceneGraph.rooms.map(r => r.id === room.id ? { ...r, texture: e.target.value } : r)
                              });
                            }}
                            style={{ width: '100%', background: 'rgba(0,0,0,0.5)', border: '1px solid #333', color: '#fff', padding: '4px', borderRadius: 4, fontSize: 12 }}>
                            <option value="wood">Wood Planks</option>
                            <option value="tiles">White Tiles</option>
                            <option value="concrete">Polished Concrete</option>
                            <option value="brick">Red Brick</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  );
                }

                return <p style={{ fontSize: 12, color: '#666', marginTop: 4 }}>Selection: {selectedId}</p>;
              })()}
            </div>
          )}

          {/* Scene metadata */}
          {hasScene && (
            <div className="glass-card property-item" style={{ marginBottom: 12 }}>
              <span className="label-tiny">Scene Info</span>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 8 }}>
                {[
                  ['Rooms',    sceneGraph.rooms.length],
                  ['Walls',    sceneGraph.walls.length],
                  ['Width',    meta.width_m ? `${meta.width_m}m` : '—'],
                  ['Depth',    meta.depth_m ? `${meta.depth_m}m` : '—'],
                ].map(([label, val]) => (
                  <div key={label} style={{ textAlign: 'center' }}>
                    <p style={{ color: '#00d4ff', fontSize: 16, fontWeight: 700 }}>{val}</p>
                    <p style={{ color: '#666', fontSize: 10, textTransform: 'uppercase' }}>{label}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="glass-card property-item">
            <span className="label-tiny">Wall Height ({wallHeight}m)</span>
            <input type="range" min="2" max="5" step="0.1"
              value={wallHeight}
              onChange={(e) => setWallHeight(parseFloat(e.target.value))}
              className="range-input"
            />
          </div>

          {/* Ceiling toggle */}
          <div className="glass-card property-item">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="label-tiny" style={{ marginBottom: 0 }}>Ceiling</span>
              <button
                onClick={toggleCeiling}
                style={{
                  background: showCeiling ? 'rgba(0,242,255,0.2)' : 'rgba(255,255,255,0.05)',
                  border: showCeiling ? '1px solid rgba(0,242,255,0.4)' : '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 8, padding: '4px 12px', cursor: 'pointer',
                  color: showCeiling ? '#00f2ff' : '#888', fontSize: 10, fontWeight: 700,
                }}
              >
                {showCeiling ? 'ON' : 'OFF'}
              </button>
            </div>
          </div>

          <div className="glass-card property-item">
            <span className="label-tiny">Floor Material</span>
            <div className="material-grid">
              {['wood', 'tiles', 'concrete'].map(t => (
                <button key={t} onClick={() => setFloorTexture(t)}
                  className={`mat-btn ${t}`}
                  title={t.charAt(0).toUpperCase() + t.slice(1)}
                />
              ))}
            </div>
          </div>

          {hasScene && (
            <div className="glass-card property-item">
              <span className="label-tiny">Rooms</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6, maxHeight: 180, overflowY: 'auto' }}>
                {sceneGraph.rooms.map(r => (
                  <div key={r.id} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '6px 10px', background: 'rgba(255,255,255,0.04)',
                    borderRadius: 6, fontSize: 11, cursor: 'pointer',
                    borderLeft: `3px solid ${r.color || '#555'}`,
                    transition: 'background 0.15s',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(0,242,255,0.08)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.04)'}
                  >
                    <span style={{ color: '#ccc', fontWeight: 600 }}>{r.name}</span>
                    <span style={{ color: '#666', fontSize: 10 }}>
                      {r.area_m2 ? `${r.area_m2}m²` : r.type}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Openings info */}
          {hasScene && sceneGraph.openings.length > 0 && (
            <div className="glass-card property-item">
              <span className="label-tiny">Openings</span>
              <div style={{ display: 'flex', gap: 12, marginTop: 6 }}>
                <div style={{ textAlign: 'center' }}>
                  <p style={{ color: '#00d4ff', fontSize: 14, fontWeight: 700 }}>
                    {sceneGraph.openings.filter(o => o.type === 'door').length}
                  </p>
                  <p style={{ color: '#666', fontSize: 9, textTransform: 'uppercase' }}>Doors</p>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <p style={{ color: '#00d4ff', fontSize: 14, fontWeight: 700 }}>
                    {sceneGraph.openings.filter(o => o.type === 'window').length}
                  </p>
                  <p style={{ color: '#666', fontSize: 9, textTransform: 'uppercase' }}>Windows</p>
                </div>
              </div>
            </div>
          )}

          <div className="glass-card-accent export-area">
            <span className="label-small accent-text">Studio Export</span>
            <button onClick={handleExport} className="btn-primary full-width">
              <Download size={14} /> Download .GLB
            </button>
            <p className="help-text">Compatible with Blender, Unity & Revit</p>
          </div>
        </aside>
      )}
    </div>
  );
};

export default App;
