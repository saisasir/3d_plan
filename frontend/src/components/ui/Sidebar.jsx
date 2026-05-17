import React from 'react';
import { motion } from 'framer-motion';
import { clsx } from 'clsx';

export const SidebarItem = ({ icon: Icon, label, active, onClick }) => (
  <motion.div
    whileHover={{ x: 5, backgroundColor: 'rgba(99, 102, 241, 0.05)' }}
    onClick={onClick}
    className={clsx(
      "flex items-center gap-4 p-4 cursor-pointer transition-all border-l-2",
      active ? 'text-accent border-accent bg-accent/5' : 'text-gray-500 border-transparent hover:text-gray-300'
    )}
  >
    <Icon size={18} strokeWidth={active ? 2.5 : 2} />
    <span className={clsx("font-semibold text-xs tracking-wide uppercase", active ? 'opacity-100' : 'opacity-60')}>
      {label}
    </span>
  </motion.div>
);

import { Box } from 'lucide-react';

export const AssetCard = ({ name, type = 'furniture' }) => (
  <motion.div 
    draggable
    onDragStart={(e) => {
      e.dataTransfer.setData("type", type);
      e.dataTransfer.setData("name", name);
    }}
    whileHover={{ scale: 1.02 }}
    className="aspect-square glass rounded-xl overflow-hidden group cursor-pointer border border-white/5 relative"
  >
    <div className="h-full w-full bg-white/5 flex items-center justify-center group-hover:bg-accent/10 transition-colors">
       <Box size={24} className="text-white/20 group-hover:text-accent transition-colors" />
    </div>
    <div className="absolute bottom-0 inset-x-0 p-2 bg-black/60 backdrop-blur-md opacity-0 group-hover:opacity-100 transition-opacity">
      <p className="text-[10px] font-bold text-center uppercase tracking-tighter">{name}</p>
    </div>
  </motion.div>
);
