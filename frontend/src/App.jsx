import { useRef, useEffect, useState } from 'react';
import { PanelRightOpen, PanelRightClose, BarChart3, FlaskConical, Loader2 } from 'lucide-react';
import { AuthProvider, useAuth } from './hooks/useAuth.jsx';
import { useChat } from './hooks/useChat';
import LoginPage from './components/LoginPage';
import Sidebar from './components/Sidebar';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import TypingIndicator from './components/TypingIndicator';
import EVCPanel from './components/EVCPanel';
import WelcomeScreen from './components/WelcomeScreen';
import ExportPanel from './components/ExportPanel';
import AutoTestPanel from './components/AutoTestPanel';

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

function AppContent() {
  const { user, loading, isAuthenticated, logout, isGuest } = useAuth();

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-[#0f1117]">
        <Loader2 size={24} className="animate-spin text-jarvis-400" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return <ChatApp user={user} logout={logout} isGuest={isGuest} />;
}

function ChatApp({ user, logout, isGuest }) {
  const { messages, isLoading, botState, userState, send, reset, sessionId, conversations, activeConvId, loadConversation } = useChat();
  const [showEVC, setShowEVC] = useState(true);
  const [showExport, setShowExport] = useState(false);
  const [showAutoTest, setShowAutoTest] = useState(false);
  const [exportSessionOverride, setExportSessionOverride] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  return (
    <div className="h-full flex bg-[#0f1117]">
      {/* Sidebar */}
      <div className="w-56 flex-shrink-0 hidden md:block">
        <Sidebar sessionId={sessionId} onReset={reset} user={user} onLogout={logout} isGuest={isGuest} conversations={conversations} activeConvId={activeConvId} onSelectConversation={loadConversation} />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <div className="h-12 flex items-center justify-between px-4 border-b border-[#1e2028] flex-shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-[#888]">Jarvis Online</span>
            {botState && (
              <span className="text-[10px] text-[#555] ml-2">
                Turn {botState.turn} ·{' '}
                <span style={{ color: getEmotionColor(botState.dominant_emotion) }}>
                  {botState.dominant_emotion}
                </span>
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setShowAutoTest(true)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[10px] font-medium text-[#666] hover:text-emerald-400 hover:bg-[#1a1c24] transition-colors"
              title="Auto-Test 100 Messages"
            >
              <FlaskConical size={14} />
              Auto-Test
            </button>
            <button
              onClick={() => { setExportSessionOverride(null); setShowExport(true); }}
              disabled={messages.length === 0}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[10px] font-medium text-[#666] hover:text-amber-400 hover:bg-[#1a1c24] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              title="Export & Analysis"
            >
              <BarChart3 size={14} />
              Export
            </button>
            <button
              onClick={() => setShowEVC(!showEVC)}
              className="p-1.5 rounded-md text-[#666] hover:text-jarvis-400 hover:bg-[#1a1c24] transition-colors"
              title={showEVC ? 'Hide EVC Panel' : 'Show EVC Panel'}
            >
              {showEVC ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
            </button>
          </div>
        </div>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <WelcomeScreen />
          ) : (
            <div className="max-w-3xl mx-auto py-4">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
              {isLoading && <TypingIndicator />}
            </div>
          )}
        </div>

        {/* Input */}
        <div className="max-w-3xl mx-auto w-full">
          <ChatInput onSend={send} disabled={isLoading} />
        </div>
      </div>

      {/* EVC Panel */}
      {showEVC && (
        <div className="w-64 flex-shrink-0 border-l border-[#1e2028] bg-[#14161e] hidden lg:block">
          <EVCPanel botState={botState} userState={userState} />
        </div>
      )}
      {/* Export Modal */}
      {showExport && (
        <ExportPanel sessionId={exportSessionOverride || sessionId} onClose={() => { setShowExport(false); setExportSessionOverride(null); }} />
      )}
      {/* Auto-Test Modal */}
      {showAutoTest && (
        <AutoTestPanel
          onClose={() => setShowAutoTest(false)}
          onDone={(sid) => {
            setShowAutoTest(false);
            setExportSessionOverride(sid);
            setShowExport(true);
          }}
        />
      )}
    </div>
  );
}

function getEmotionColor(emotion) {
  const map = {
    Joy: '#fbbf24',
    Serenity: '#34d399',
    Love: '#f472b6',
    Excitement: '#fb923c',
    Sadness: '#60a5fa',
    Fear: '#a78bfa',
    Anger: '#f87171',
    Surprise: '#2dd4bf',
  };
  return map[emotion] || '#888';
}
