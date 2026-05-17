import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Shield, 
  Store, 
  Home, 
  TrendingUp, 
  Box,
  MoreVertical,
  Activity,
  CheckCircle,
  AlertCircle
} from 'lucide-react';

const AdminDashboard = () => {
  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState({
    totalProjects: 124,
    activeVendors: 12,
    totalCustomers: 450,
    aiAccuracy: 98.4
  });

  useEffect(() => {
    // Fetch real user profiles from the backend
    fetch('http://localhost:8000/api/v1/admin/users')
      .then(res => res.json())
      .then(data => setUsers(data))
      .catch(err => console.error("Admin Fetch Error:", err));
  }, []);

  const getRoleIcon = (role) => {
    switch(role) {
      case 'admin': return <Shield size={14} className="text-magenta-500" />;
      case 'vendor': return <Store size={14} className="text-accent" />;
      default: return <Users size={14} className="text-blue-500" />;
    }
  };

  return (
    <div className="p-8 h-full overflow-y-auto custom-scrollbar bg-[#050505]">
      {/* Header */}
      <div className="flex justify-between items-end mb-10">
        <div>
          <h1 className="text-3xl font-black tracking-tight">Command Center</h1>
          <p className="text-gray-500 text-xs font-bold uppercase tracking-widest mt-1">Platform-wide Oversight</p>
        </div>
        <div className="flex gap-4">
          <div className="px-4 py-2 glass-dark border border-white/5 rounded-xl">
             <p className="text-[10px] text-gray-500 font-bold uppercase">System Status</p>
             <div className="flex items-center gap-2 mt-1">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-[10px] font-black uppercase text-white">Neural Engines Optimal</span>
             </div>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-6 mb-10">
        {[
          { label: 'Total 3D Scenes', value: stats.totalProjects, icon: Box, color: 'text-accent' },
          { label: 'Pro Vendors', value: stats.activeVendors, icon: Store, color: 'text-magenta-500' },
          { label: 'Active Customers', value: stats.totalCustomers, icon: Users, color: 'text-blue-500' },
          { label: 'AI Confidence', value: `${stats.aiAccuracy}%`, icon: Activity, color: 'text-green-500' }
        ].map((s, i) => (
          <div key={i} className="p-6 glass-dark border border-white/5 rounded-2xl relative overflow-hidden group hover:border-white/20 transition-all">
            <div className="absolute -right-4 -bottom-4 opacity-5 group-hover:scale-110 transition-transform">
              <s.icon size={80} />
            </div>
            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">{s.label}</p>
            <h3 className={`text-3xl font-black mt-2 ${s.color}`}>{s.value}</h3>
          </div>
        ))}
      </div>

      {/* User Management Table */}
      <div className="glass-dark border border-white/5 rounded-3xl overflow-hidden shadow-2xl">
        <div className="p-6 border-b border-white/5 flex justify-between items-center bg-white/5">
          <h3 className="font-black text-sm uppercase tracking-widest">Active Identities</h3>
          <div className="flex gap-2">
             <button className="px-4 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-[10px] font-bold uppercase">Filter</button>
             <button className="px-4 py-1.5 bg-accent text-black rounded-lg text-[10px] font-black uppercase">Export CSV</button>
          </div>
        </div>
        
        <table className="w-full text-left">
          <thead>
            <tr className="bg-black/40 text-gray-500 text-[10px] uppercase font-black tracking-widest border-b border-white/5">
              <th className="p-6">User / Identity</th>
              <th className="p-6">Role</th>
              <th className="p-6">Profile Details</th>
              <th className="p-6">Project Count</th>
              <th className="p-6 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {users.map((u, i) => (
              <tr key={i} className="hover:bg-white/5 transition-colors group">
                <td className="p-6">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-accent to-purple-500 flex items-center justify-center font-black">
                      {u.email[0].toUpperCase()}
                    </div>
                    <div>
                      <p className="text-sm font-bold text-white">{u.email}</p>
                      <p className="text-[10px] text-gray-500">ID: {u.id}</p>
                    </div>
                  </div>
                </td>
                <td className="p-6">
                  <div className="flex items-center gap-2 px-3 py-1 bg-white/5 border border-white/10 rounded-full w-fit">
                    {getRoleIcon(u.role)}
                    <span className="text-[10px] font-black uppercase tracking-widest">{u.role}</span>
                  </div>
                </td>
                <td className="p-6">
                  <div className="text-[10px] text-gray-400 space-y-1">
                    {u.role === 'vendor' && <p>🏢 {u.vendor_profile?.company_name || 'N/A'} • {u.vendor_profile?.tier}</p>}
                    {u.role === 'customer' && <p>📱 {u.customer_profile?.phone || 'N/A'}</p>}
                    {u.role === 'admin' && <p className="text-accent italic font-bold">System Overlord</p>}
                  </div>
                </td>
                <td className="p-6 text-sm font-mono text-gray-400">
                  {Math.floor(Math.random() * 15)}
                </td>
                <td className="p-6 text-right">
                  <button className="p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-500 hover:text-white">
                    <MoreVertical size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AdminDashboard;
