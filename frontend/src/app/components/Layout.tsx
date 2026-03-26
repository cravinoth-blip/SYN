import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router';
import {
  LayoutDashboard, MessageSquare, History,
  BookOpen, Upload, Settings, Bell,
  Search, ChevronLeft, ChevronRight,
  Shield, LogOut, HelpCircle, Menu, X,
} from 'lucide-react';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { path: '/chat', label: 'Chat', icon: MessageSquare },
  { path: '/history', label: 'History', icon: History },
  { path: '/documents', label: 'Documents', icon: BookOpen },
  { path: '/upload', label: 'Upload', icon: Upload },
];

export function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:relative inset-y-0 left-0 z-50
          flex flex-col bg-[#0A1628] text-white transition-all duration-300
          ${collapsed ? 'w-[72px]' : 'w-64'}
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        {/* Logo */}
        <div className={`flex items-center gap-3 px-4 py-5 border-b border-white/10 ${collapsed ? 'justify-center' : ''}`}>
          <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-blue-500 flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          {!collapsed && (
            <div>
              <div className="text-white" style={{ fontSize: '13px', fontWeight: 700, letterSpacing: '0.02em', lineHeight: 1.2 }}>ASUNDEXIAN KNOWLEDGE</div>
              <div className="text-slate-400" style={{ fontSize: '11px' }}>Powered by SYN10X</div>
            </div>
          )}
        </div>

        {/* Collapse button */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="hidden lg:flex absolute -right-3 top-[68px] w-6 h-6 rounded-full bg-[#0A1628] border border-white/20 items-center justify-center text-slate-300 hover:text-white z-10"
        >
          {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
        </button>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map(({ path, label, icon: Icon, end }) => (
            <NavLink
              key={path}
              to={path}
              end={end}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 group relative
                ${isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-white/8'
                }
                ${collapsed ? 'justify-center' : ''}`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-white' : ''}`} />
                  {!collapsed && <span style={{ fontSize: '14px', fontWeight: 500 }}>{label}</span>}
                  {collapsed && (
                    <div className="absolute left-full ml-3 px-2 py-1 bg-slate-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50 transition-opacity">
                      {label}
                    </div>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Bottom section */}
        <div className="px-3 pb-4 space-y-1 border-t border-white/10 pt-3">
          <button className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/8 transition-all ${collapsed ? 'justify-center' : ''}`}>
            <HelpCircle className="w-5 h-5 flex-shrink-0" />
            {!collapsed && <span style={{ fontSize: '14px', fontWeight: 500 }}>Help & Support</span>}
          </button>
          <button className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/8 transition-all ${collapsed ? 'justify-center' : ''}`}>
            <Settings className="w-5 h-5 flex-shrink-0" />
            {!collapsed && <span style={{ fontSize: '14px', fontWeight: 500 }}>Settings</span>}
          </button>

          {/* User profile */}
          <div className={`flex items-center gap-3 px-3 py-2.5 mt-2 rounded-lg bg-white/5 ${collapsed ? 'justify-center' : ''}`}>
            <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0" style={{ fontSize: '13px', fontWeight: 600, color: 'white' }}>
              SH
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <div className="text-white truncate" style={{ fontSize: '13px', fontWeight: 500 }}>Syneos Health</div>
                <div className="text-slate-500 truncate" style={{ fontSize: '11px' }}>Medical Affairs</div>
              </div>
            )}
            {!collapsed && <LogOut className="w-4 h-4 text-slate-500 flex-shrink-0 cursor-pointer hover:text-white" />}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="bg-white border-b border-slate-200 px-4 lg:px-6 py-3 flex items-center gap-4 flex-shrink-0">
          <button
            className="lg:hidden p-2 rounded-lg hover:bg-slate-100"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>

          <div className="flex-1 flex items-center gap-3 bg-slate-100 rounded-lg px-3 py-2 max-w-lg">
            <Search className="w-4 h-4 text-slate-400 flex-shrink-0" />
            <input
              type="text"
              placeholder="Search documents, queries, references..."
              className="flex-1 bg-transparent text-slate-700 placeholder-slate-400 outline-none min-w-0"
              style={{ fontSize: '14px' }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const val = (e.target as HTMLInputElement).value.trim();
                  if (val) navigate(`/chat?q=${encodeURIComponent(val)}`);
                }
              }}
            />
          </div>

          <div className="flex items-center gap-2 ml-auto">
            <button
              onClick={() => navigate('/chat')}
              className="hidden sm:flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              style={{ fontSize: '14px', fontWeight: 500 }}
            >
              <MessageSquare className="w-4 h-4" />
              New Chat
            </button>
            <button className="relative p-2 rounded-lg hover:bg-slate-100">
              <Bell className="w-5 h-5 text-slate-600" />
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
