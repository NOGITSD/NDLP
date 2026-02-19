import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { Bot, LogIn, UserPlus, Zap, Brain, Heart, Shield } from 'lucide-react';

export default function LoginPage() {
  const { login, register, googleLogin, guest, error, setError } = useAuth();
  const googleBtnRef = useRef(null);
  const googleInitRef = useRef(false);
  const [googleClientId, setGoogleClientId] = useState('');
  const [mode, setMode] = useState('login'); // login | register
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (mode === 'login') {
        await login(username, password);
      } else {
        await register(username, password, email, displayName);
      }
    } catch { /* error is set via context */ }
    setSubmitting(false);
  };

  const handleGuest = async () => {
    setSubmitting(true);
    setError(null);
    try { await guest(); } catch { /* */ }
    setSubmitting(false);
  };

  const handleGoogleCallback = useCallback(async (response) => {
    if (!response.credential) return;
    setSubmitting(true);
    setError(null);
    try {
      await googleLogin(response.credential);
    } catch { /* error set via context */ }
    setSubmitting(false);
  }, [googleLogin, setError]);

  // Fetch runtime config (supports deployments where VITE_* build env is not available)
  useEffect(() => {
    let alive = true;
    fetch('/api/config')
      .then(r => r.ok ? r.json() : null)
      .then(cfg => {
        if (!alive || !cfg) return;
        if (typeof cfg.google_client_id === 'string') {
          setGoogleClientId(cfg.google_client_id);
        }
      })
      .catch(() => { /* best-effort */ });
    return () => { alive = false; };
  }, []);

  // Initialize Google Sign-In
  useEffect(() => {
    if (googleInitRef.current) return;
    const initGoogle = () => {
      const clientId = googleClientId || import.meta.env.VITE_GOOGLE_CLIENT_ID;
      if (!clientId || !window.google?.accounts?.id) return;
      googleInitRef.current = true;
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleGoogleCallback,
      });
      if (googleBtnRef.current) {
        window.google.accounts.id.renderButton(googleBtnRef.current, {
          theme: 'filled_black',
          size: 'large',
          width: 380,
          text: 'continue_with',
          shape: 'rectangular',
          logo_alignment: 'left',
        });
      }
    };
    // GIS script may load after component mount
    if (window.google?.accounts?.id) {
      initGoogle();
    } else {
      const timer = setInterval(() => {
        if (window.google?.accounts?.id) {
          clearInterval(timer);
          initGoogle();
        }
      }, 200);
      return () => clearInterval(timer);
    }
  }, [handleGoogleCallback, googleClientId]);

  const hasGoogleClientId = !!googleClientId || !!import.meta.env.VITE_GOOGLE_CLIENT_ID;

  return (
    <div className="h-full flex bg-[#0f1117]">
      {/* Left — branding */}
      <div className="hidden lg:flex flex-1 flex-col items-center justify-center bg-gradient-to-br from-[#0f1117] via-[#141822] to-[#0f1117] border-r border-[#1e2028] p-12">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-jarvis-500 to-jarvis-700 flex items-center justify-center shadow-lg shadow-jarvis-500/20">
            <Bot size={28} className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">JARVIS</h1>
            <p className="text-xs text-[#666]">Personal AI Secretary</p>
          </div>
        </div>

        <div className="space-y-4 max-w-xs">
          <div className="flex items-start gap-3 p-3 rounded-xl bg-[#1a1c24]/50 border border-[#2a2d37]/50">
            <Brain size={18} className="text-jarvis-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-xs font-medium text-[#ccc]">Remembers You</p>
              <p className="text-[10px] text-[#666]">Learns your preferences, schedule, and personality over time</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 rounded-xl bg-[#1a1c24]/50 border border-[#2a2d37]/50">
            <Heart size={18} className="text-pink-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-xs font-medium text-[#ccc]">Emotional Intelligence</p>
              <p className="text-[10px] text-[#666]">Biological hormone model adapts to your emotional state</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 rounded-xl bg-[#1a1c24]/50 border border-[#2a2d37]/50">
            <Shield size={18} className="text-emerald-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-xs font-medium text-[#ccc]">Multi-Platform</p>
              <p className="text-[10px] text-[#666]">Web, LINE, Discord — same identity everywhere</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right — auth form */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8 justify-center">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-jarvis-500 to-jarvis-700 flex items-center justify-center">
              <Bot size={20} className="text-white" />
            </div>
            <h1 className="text-xl font-bold text-white">JARVIS</h1>
          </div>

          <h2 className="text-lg font-bold text-white mb-1">
            {mode === 'login' ? 'Welcome back' : 'Create account'}
          </h2>
          <p className="text-xs text-[#666] mb-6">
            {mode === 'login'
              ? 'Sign in to continue your conversation with Jarvis'
              : 'Register to let Jarvis remember you across sessions'}
          </p>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-900/20 border border-red-700/30 text-red-400 text-xs">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3">
            {mode === 'register' && (
              <input
                type="text"
                placeholder="Display Name (optional)"
                value={displayName}
                onChange={e => setDisplayName(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg bg-[#1a1c24] border border-[#2a2d37] text-sm text-white placeholder-[#555] focus:outline-none focus:border-jarvis-600/50"
              />
            )}
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              className="w-full px-4 py-2.5 rounded-lg bg-[#1a1c24] border border-[#2a2d37] text-sm text-white placeholder-[#555] focus:outline-none focus:border-jarvis-600/50"
            />
            {mode === 'register' && (
              <input
                type="email"
                placeholder="Email (optional)"
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg bg-[#1a1c24] border border-[#2a2d37] text-sm text-white placeholder-[#555] focus:outline-none focus:border-jarvis-600/50"
              />
            )}
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={6}
              className="w-full px-4 py-2.5 rounded-lg bg-[#1a1c24] border border-[#2a2d37] text-sm text-white placeholder-[#555] focus:outline-none focus:border-jarvis-600/50"
            />

            <button
              type="submit"
              disabled={submitting}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-jarvis-600 text-white text-sm font-medium hover:bg-jarvis-500 transition-colors disabled:opacity-50"
            >
              {mode === 'login' ? <LogIn size={16} /> : <UserPlus size={16} />}
              {submitting ? 'Processing...' : mode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          {/* Toggle login/register */}
          <p className="text-center text-xs text-[#666] mt-4">
            {mode === 'login' ? (
              <>Don&apos;t have an account?{' '}
                <button onClick={() => { setMode('register'); setError(null); }}
                  className="text-jarvis-400 hover:underline">Register</button>
              </>
            ) : (
              <>Already have an account?{' '}
                <button onClick={() => { setMode('login'); setError(null); }}
                  className="text-jarvis-400 hover:underline">Sign In</button>
              </>
            )}
          </p>

          {/* Divider */}
          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px bg-[#2a2d37]" />
            <span className="text-[10px] text-[#555] uppercase">or</span>
            <div className="flex-1 h-px bg-[#2a2d37]" />
          </div>

          {/* Google Sign-In */}
          {hasGoogleClientId && (
            <div className="mb-3">
              <div ref={googleBtnRef} className="flex justify-center [&>div]:!w-full" />
            </div>
          )}
          {!hasGoogleClientId && (
            <button
              disabled
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-[#1a1c24] border border-[#2a2d37] text-[#555] text-sm cursor-not-allowed mb-3"
              title="Set VITE_GOOGLE_CLIENT_ID to enable"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" className="flex-shrink-0">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Google Sign-In (not configured)
            </button>
          )}

          {/* Guest mode */}
          <button
            onClick={handleGuest}
            disabled={submitting}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-[#1a1c24] border border-[#2a2d37] text-[#888] text-sm hover:text-white hover:border-[#3a3d47] transition-colors disabled:opacity-50"
          >
            <Zap size={16} />
            Try as Guest
          </button>
          <p className="text-center text-[10px] text-[#444] mt-2">
            Guest mode — no memory saved across sessions
          </p>
        </div>
      </div>
    </div>
  );
}
