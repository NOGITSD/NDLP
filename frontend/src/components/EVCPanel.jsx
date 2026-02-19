import { useState } from 'react';
import { Activity, Heart, Brain, Shield, TrendingUp, User, Bot } from 'lucide-react';

const EMOTION_CONFIG = {
  Joy: { color: '#fbbf24', emoji: '😊' },
  Serenity: { color: '#34d399', emoji: '😌' },
  Love: { color: '#f472b6', emoji: '🥰' },
  Excitement: { color: '#fb923c', emoji: '🤩' },
  Sadness: { color: '#60a5fa', emoji: '😢' },
  Fear: { color: '#a78bfa', emoji: '😨' },
  Anger: { color: '#f87171', emoji: '😠' },
  Surprise: { color: '#2dd4bf', emoji: '😲' },
};

const HORMONE_NAMES = [
  'Dopamine', 'Serotonin', 'Oxytocin', 'Endorphin',
  'Cortisol', 'Adrenaline', 'GABA', 'Norepinephrine',
];

const HORMONE_COLORS = [
  '#fbbf24', '#34d399', '#f472b6', '#fb923c',
  '#f87171', '#a78bfa', '#60a5fa', '#2dd4bf',
];

function EmotionBar({ name, value, color, emoji }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs w-5 text-center">{emoji}</span>
      <div className="flex-1 h-2 bg-[#1a1c24] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-[10px] text-[#888] w-8 text-right font-mono">{pct}%</span>
    </div>
  );
}

function HormoneBar({ name, value, color }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-[#777] w-16 truncate">{name}</span>
      <div className="flex-1 h-1.5 bg-[#1a1c24] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-[10px] text-[#666] w-7 text-right font-mono">{pct}</span>
    </div>
  );
}

function TrustMeter({ value }) {
  const pct = Math.round(value * 100);
  const hue = value * 120; // 0=red → 120=green
  return (
    <div className="flex items-center gap-2">
      <Shield size={12} className="text-[#888]" />
      <span className="text-[10px] text-[#888] w-8">Trust</span>
      <div className="flex-1 h-2 bg-[#1a1c24] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${pct}%`, backgroundColor: `hsl(${hue}, 70%, 50%)` }}
        />
      </div>
      <span className="text-xs font-mono" style={{ color: `hsl(${hue}, 70%, 60%)` }}>
        {pct}%
      </span>
    </div>
  );
}

function ViewToggle({ activeView, onToggle }) {
  return (
    <div className="flex bg-[#1a1c24] rounded-lg p-0.5 gap-0.5">
      <button
        onClick={() => onToggle('jarvis')}
        className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-semibold transition-all ${activeView === 'jarvis'
            ? 'bg-jarvis-500/20 text-jarvis-300 shadow-sm'
            : 'text-[#555] hover:text-[#888]'
          }`}
      >
        <Bot size={11} />
        Jarvis
      </button>
      <button
        onClick={() => onToggle('user')}
        className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-semibold transition-all ${activeView === 'user'
            ? 'bg-cyan-500/20 text-cyan-300 shadow-sm'
            : 'text-[#555] hover:text-[#888]'
          }`}
      >
        <User size={11} />
        User
      </button>
    </div>
  );
}

function EVCStateView({ state, label, accentColor }) {
  const emotions = state.emotions || {};
  const hormones = state.hormones || {};
  const trust = state.trust ?? 0.5;
  const dominant = state.dominant_emotion || 'Neutral';
  const blend = state.emotion_blend || '';
  const turn = state.turn || 0;

  const emotionEntries = Object.entries(emotions).sort((a, b) => b[1] - a[1]);
  const hormoneValues = HORMONE_NAMES.map(name => {
    const key = name.toLowerCase();
    return hormones[key] ?? hormones[name] ?? 0;
  });

  const dominantConfig = EMOTION_CONFIG[dominant] || { color: '#888', emoji: '🤖' };

  return (
    <>
      {/* Dominant Emotion */}
      <div className="p-4 border-b border-[#1e2028]">
        <div className="flex items-center gap-3">
          <div
            className="animate-pulse-glow w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
            style={{ backgroundColor: dominantConfig.color + '20', border: `1px solid ${dominantConfig.color}40` }}
          >
            {dominantConfig.emoji}
          </div>
          <div>
            <div className="text-sm font-semibold" style={{ color: dominantConfig.color }}>
              {dominant}
            </div>
            <div className="text-[10px] text-[#666] mt-0.5 max-w-[160px] truncate">{blend}</div>
          </div>
        </div>
      </div>

      {/* Trust */}
      <div className="p-4 border-b border-[#1e2028]">
        <TrustMeter value={trust} />
      </div>

      {/* Emotions */}
      <div className="p-4 border-b border-[#1e2028]">
        <div className="flex items-center gap-1.5 mb-3">
          <Heart size={12} className="text-pink-400" />
          <span className="text-[10px] font-semibold text-[#888] uppercase tracking-wider">Emotions</span>
        </div>
        <div className="flex flex-col gap-1.5">
          {emotionEntries.map(([name, value]) => {
            const cfg = EMOTION_CONFIG[name] || { color: '#888', emoji: '?' };
            return <EmotionBar key={name} name={name} value={value} color={cfg.color} emoji={cfg.emoji} />;
          })}
        </div>
      </div>

      {/* Hormones */}
      <div className="p-4">
        <div className="flex items-center gap-1.5 mb-3">
          <TrendingUp size={12} className="text-emerald-400" />
          <span className="text-[10px] font-semibold text-[#888] uppercase tracking-wider">Hormones</span>
        </div>
        <div className="flex flex-col gap-1">
          {HORMONE_NAMES.map((name, i) => (
            <HormoneBar key={name} name={name} value={hormoneValues[i]} color={HORMONE_COLORS[i]} />
          ))}
        </div>
      </div>
    </>
  );
}

export default function EVCPanel({ botState, userState }) {
  const [activeView, setActiveView] = useState('jarvis');

  const hasData = activeView === 'jarvis' ? !!botState : !!userState;
  const currentState = activeView === 'jarvis' ? botState : userState;
  const turn = currentState?.turn || botState?.turn || 0;

  if (!botState && !userState) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-[#555] text-sm gap-2 p-6">
        <Activity size={32} className="text-[#333]" />
        <p>เริ่มสนทนาเพื่อดูสถานะ EVC</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-y-auto">
      {/* Header with Toggle */}
      <div className="p-4 border-b border-[#1e2028]">
        <div className="flex items-center gap-2 mb-2">
          <Activity size={14} className="text-jarvis-400" />
          <span className="text-xs font-semibold text-jarvis-300 uppercase tracking-wider">EVC Engine</span>
          <span className="text-[10px] text-[#555] ml-auto">Turn {turn}</span>
        </div>
        <ViewToggle activeView={activeView} onToggle={setActiveView} />
      </div>

      {/* Label */}
      <div className="px-4 pt-2 pb-1">
        <span className={`text-[10px] font-semibold uppercase tracking-wider ${activeView === 'jarvis' ? 'text-jarvis-400' : 'text-cyan-400'
          }`}>
          {activeView === 'jarvis' ? '🤖 Jarvis\'s Emotions' : '👤 User\'s Emotions'}
        </span>
      </div>

      {/* Content */}
      {hasData ? (
        <EVCStateView
          state={currentState}
          label={activeView === 'jarvis' ? 'Jarvis' : 'User'}
          accentColor={activeView === 'jarvis' ? '#22d3ee' : '#06b6d4'}
        />
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center text-[#555] text-xs gap-2 p-6">
          <User size={24} className="text-[#333]" />
          <p>ยังไม่มีข้อมูล{activeView === 'user' ? ' User' : ''}</p>
        </div>
      )}
    </div>
  );
}
