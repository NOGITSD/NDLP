import { Plus, RotateCcw, Cpu, Sparkles, LogOut, User, Zap, Shield } from 'lucide-react';

export default function Sidebar({ sessionId, onReset, user, onLogout, isGuest }) {
  return (
    <div className="h-full flex flex-col bg-[#12141b] border-r border-[#1e2028]">
      {/* Logo */}
      <div className="p-4 border-b border-[#1e2028]">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-jarvis-700/40 border border-jarvis-600/50 flex items-center justify-center">
            <Cpu size={18} className="text-jarvis-400" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-tight">JARVIS</h1>
            <p className="text-[10px] text-jarvis-400/70">AI Personal Secretary</p>
          </div>
        </div>
      </div>

      {/* User info */}
      {user && (
        <div className="px-4 py-3 border-b border-[#1e2028]">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-full bg-[#1a1c24] border border-[#2a2d37] flex items-center justify-center flex-shrink-0">
              {isGuest ? <Zap size={13} className="text-amber-400" /> : <User size={13} className="text-jarvis-400" />}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-[#ccc] truncate">{user.display_name || user.username || 'Guest'}</p>
              <div className="flex items-center gap-1.5">
                {isGuest ? (
                  <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-amber-900/30 text-amber-400 border border-amber-700/30">Guest</span>
                ) : (
                  <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-emerald-900/30 text-emerald-400 border border-emerald-700/30 flex items-center gap-0.5">
                    <Shield size={8} /> {user.auth_provider || 'local'}
                  </span>
                )}
              </div>
            </div>
          </div>
          {isGuest && (
            <p className="text-[9px] text-[#555] mt-1.5 leading-tight">
              Memory not saved across sessions
            </p>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="p-3 flex flex-col gap-1">
        <button
          onClick={onReset}
          className="flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-sm text-[#aaa] hover:text-white hover:bg-[#1a1c24] transition-colors"
        >
          <Plus size={15} />
          <span>New Chat</span>
        </button>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Session info + logout */}
      <div className="p-4 border-t border-[#1e2028]">
        <div className="flex items-center gap-2">
          <Sparkles size={12} className="text-jarvis-500/50" />
          <span className="text-[10px] text-[#555] truncate font-mono">{sessionId}</span>
        </div>
        <div className="flex items-center gap-3 mt-2">
          <button
            onClick={onReset}
            className="flex items-center gap-1.5 text-[10px] text-[#555] hover:text-red-400 transition-colors"
          >
            <RotateCcw size={10} />
            Reset
          </button>
          <button
            onClick={onLogout}
            className="flex items-center gap-1.5 text-[10px] text-[#555] hover:text-red-400 transition-colors"
          >
            <LogOut size={10} />
            Logout
          </button>
        </div>
      </div>
    </div>
  );
}
