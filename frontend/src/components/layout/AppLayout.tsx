import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard, FileText, Briefcase, Send, Mail,
  MessageSquare, User, Settings, LogOut, Zap, Menu, X,
  Bell, ChevronDown,
} from 'lucide-react';
import { useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import clsx from 'clsx';

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/resumes', label: 'Resumes', icon: FileText },
  { path: '/jobs', label: 'Job Analysis', icon: Briefcase },
  { path: '/applications', label: 'Applications', icon: Send },
  { path: '/cover-letters', label: 'Cover Letters', icon: Mail },
  { path: '/coach', label: 'Career Coach', icon: MessageSquare },
];

const bottomNavItems = [
  { path: '/profile', label: 'Profile', icon: User },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export default function AppLayout() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const Sidebar = ({ mobile = false }) => (
    <aside
      className={clsx(
        'flex flex-col h-full bg-dark-800 border-r border-dark-600',
        mobile ? 'w-full' : 'w-64'
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-dark-600">
        <div className="w-8 h-8 bg-gradient-brand rounded-lg flex items-center justify-center shadow-glow-sm">
          <Zap size={16} className="text-white" />
        </div>
        <div>
          <span className="font-bold text-white text-lg tracking-tight">ResuMesh</span>
          <div className="text-[10px] text-slate-500 -mt-0.5">AI Job Copilot</div>
        </div>
      </div>

      {/* Main nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        <div className="text-[10px] text-slate-600 font-semibold uppercase tracking-widest px-3 mb-2">
          Navigation
        </div>
        {navItems.map(({ path, label, icon: Icon }) => (
          <Link
            key={path}
            to={path}
            onClick={() => mobile && setSidebarOpen(false)}
            className={clsx(
              'nav-link group',
              pathname === path && 'nav-link-active'
            )}
          >
            <Icon
              size={18}
              className={clsx(
                'transition-colors',
                pathname === path ? 'text-brand-400' : 'text-slate-500 group-hover:text-slate-300'
              )}
            />
            {label}
          </Link>
        ))}
      </nav>

      {/* Bottom nav */}
      <div className="px-3 py-3 border-t border-dark-600 space-y-1">
        {bottomNavItems.map(({ path, label, icon: Icon }) => (
          <Link
            key={path}
            to={path}
            onClick={() => mobile && setSidebarOpen(false)}
            className={clsx('nav-link group', pathname === path && 'nav-link-active')}
          >
            <Icon size={18} className={clsx(pathname === path ? 'text-brand-400' : 'text-slate-500 group-hover:text-slate-300')} />
            {label}
          </Link>
        ))}
        <button onClick={handleLogout} className="nav-link w-full text-left group">
          <LogOut size={18} className="text-slate-500 group-hover:text-red-400" />
          <span className="group-hover:text-red-400">Sign Out</span>
        </button>
      </div>

      {/* User info */}
      <div className="px-4 py-4 border-t border-dark-600">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-gradient-brand flex items-center justify-center text-white font-bold text-sm shadow-glow-sm">
            {user?.full_name?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-white truncate">{user?.full_name}</div>
            <div className="text-xs text-slate-500 truncate">{user?.email}</div>
          </div>
        </div>
      </div>
    </aside>
  );

  return (
    <div className="flex h-screen bg-dark-900 overflow-hidden">
      {/* Desktop Sidebar */}
      <div className="hidden md:flex flex-shrink-0">
        <Sidebar />
      </div>

      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 z-40 md:hidden"
              onClick={() => setSidebarOpen(false)}
            />
            <motion.div
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'tween', duration: 0.25 }}
              className="fixed left-0 top-0 bottom-0 w-72 z-50 md:hidden"
            >
              <Sidebar mobile />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-14 bg-dark-800 border-b border-dark-600 flex items-center justify-between px-4 flex-shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="md:hidden btn-ghost p-2"
          >
            <Menu size={20} />
          </button>

          <div className="hidden md:flex items-center gap-2">
            <div className="text-sm text-slate-500">
              {navItems.find((n) => n.path === pathname)?.label || 'ResuMesh'}
            </div>
          </div>

          <div className="flex items-center gap-2 ml-auto">
            <button className="btn-ghost p-2 relative">
              <Bell size={18} />
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-brand-500 rounded-full" />
            </button>
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2 btn-ghost px-3"
              >
                <div className="w-7 h-7 rounded-full bg-gradient-brand flex items-center justify-center text-white font-bold text-xs">
                  {user?.full_name?.charAt(0).toUpperCase() || 'U'}
                </div>
                <span className="hidden md:block text-sm font-medium text-slate-300">
                  {user?.full_name?.split(' ')[0]}
                </span>
                <ChevronDown size={14} className="text-slate-500" />
              </button>

              <AnimatePresence>
                {userMenuOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="absolute right-0 top-11 w-48 card shadow-card-hover z-50 overflow-hidden"
                  >
                    <Link to="/profile" onClick={() => setUserMenuOpen(false)}
                      className="flex items-center gap-2 px-4 py-3 text-sm text-slate-300 hover:bg-dark-600 hover:text-white transition-colors">
                      <User size={15} /> Profile
                    </Link>
                    <Link to="/settings" onClick={() => setUserMenuOpen(false)}
                      className="flex items-center gap-2 px-4 py-3 text-sm text-slate-300 hover:bg-dark-600 hover:text-white transition-colors">
                      <Settings size={15} /> Settings
                    </Link>
                    <hr className="border-dark-600" />
                    <button onClick={handleLogout}
                      className="flex items-center gap-2 w-full px-4 py-3 text-sm text-red-400 hover:bg-dark-600 transition-colors">
                      <LogOut size={15} /> Sign Out
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
