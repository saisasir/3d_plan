import { create } from 'zustand';

const EMPTY_SCENE = {
  rooms: [],
  walls: [],
  openings: [],
  furniture: [],
  metadata: {},
};

const useSceneStore = create((set) => ({
  sceneGraph: { ...EMPTY_SCENE },

  // Editor State
  isOrbitMode: true,
  isWalkthrough: false,
  selectedId: null,

  // Architectural Settings
  wallHeight: 2.7,
  floorTexture: 'wood',
  showCeiling: false,
  is2DView: false,
  isAutoRotating: false,

  // Actions
  setSceneGraph: (graph) => set({ sceneGraph: graph }),
  setAutoRotate: (val) => set({ isAutoRotating: val }),
  resetScene:    ()      => set({ sceneGraph: { ...EMPTY_SCENE }, selectedId: null }),
  setSelection:  (id)    => set({ selectedId: id }),
  setWallHeight: (h)     => set({ wallHeight: h }),
  setFloorTexture: (t)   => set({ floorTexture: t }),
  toggleCeiling: ()      => set((s) => ({ showCeiling: !s.showCeiling })),
  toggle2DView:  ()      => set((s) => ({ is2DView: !s.is2DView })),
  toggleViewMode: () => set((s) => ({
    isWalkthrough: !s.isWalkthrough,
    isOrbitMode: s.isWalkthrough,
  })),

  updateFurnitureTransform: (id, position, rotation) => set((s) => ({
    sceneGraph: {
      ...s.sceneGraph,
      furniture: s.sceneGraph.furniture.map(f =>
        f.id === id
          ? { ...f, position: [position.x, position.y, position.z], rotation: rotation.y }
          : f
      ),
    },
  })),

  addFurniture: (item) => set((s) => ({
    sceneGraph: {
      ...s.sceneGraph,
      furniture: [...s.sceneGraph.furniture, { ...item, id: `furn_${Date.now()}` }],
    },
  })),
}));

export default useSceneStore;
