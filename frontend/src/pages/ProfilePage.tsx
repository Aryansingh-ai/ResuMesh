// Stub pages for Profile and Settings
import { useAuthStore } from '@/store/authStore';
import { User, Settings } from 'lucide-react';

export function ProfilePage() {
  const { user } = useAuthStore();
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title flex items-center gap-2"><User size={22} className="text-brand-400" /> Profile</h1>
        <p className="page-subtitle">Manage your personal information.</p>
      </div>
      <div className="card p-6 max-w-xl">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-16 h-16 bg-gradient-brand rounded-2xl flex items-center justify-center text-white text-2xl font-bold shadow-glow">
            {user?.full_name?.charAt(0)}
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">{user?.full_name}</h2>
            <p className="text-slate-400 text-sm">{user?.email}</p>
            <span className="badge-purple text-[10px] mt-1">{user?.role}</span>
          </div>
        </div>
        <p className="text-slate-400 text-sm">Full profile editing coming soon. Use the API to update your profile for now.</p>
      </div>
    </div>
  );
}

export default ProfilePage;
