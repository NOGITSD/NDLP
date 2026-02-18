import { useState, useEffect, useCallback, useRef } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, AreaChart, Area,
} from 'recharts';
import { Download, FileText, FileSpreadsheet, X, TrendingUp, Heart, Shield, BarChart3, Camera } from 'lucide-react';
import { getExportHistory, downloadExportTxt, downloadExportCsv } from '../api';

const HORMONE_COLORS = {
  Dopamine: '#fbbf24',
  Serotonin: '#34d399',
  Oxytocin: '#f472b6',
  Endorphin: '#fb923c',
  Cortisol: '#f87171',
  Adrenaline: '#a78bfa',
  GABA: '#60a5fa',
  Norepinephrine: '#2dd4bf',
};

const EMOTION_COLORS = {
  Joy: '#fbbf24',
  Serenity: '#34d399',
  Love: '#f472b6',
  Excitement: '#fb923c',
  Sadness: '#60a5fa',
  Fear: '#a78bfa',
  Anger: '#f87171',
  Surprise: '#2dd4bf',
};

function TabButton({ active, onClick, icon: Icon, label }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
        active
          ? 'bg-jarvis-700/40 text-jarvis-300 border border-jarvis-600/50'
          : 'text-[#777] hover:text-[#aaa] hover:bg-[#1a1c24]'
      }`}
    >
      <Icon size={13} />
      {label}
    </button>
  );
}

export default function ExportPanel({ sessionId, onClose }) {
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('hormones');
  const [exporting, setExporting] = useState(false);
  const chartContainerRef = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getExportHistory(sessionId);
      setHistory(data);
    } catch (err) {
      console.error('Export load error:', err);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => { load(); }, [load]);

  const handleTxtExport = async () => {
    setExporting(true);
    try { await downloadExportTxt(sessionId); } finally { setExporting(false); }
  };

  const handleCsvExport = async () => {
    setExporting(true);
    try { await downloadExportCsv(sessionId); } finally { setExporting(false); }
  };

  const handleScreenshot = async () => {
    if (!chartContainerRef.current) return;
    setExporting(true);
    try {
      // Use SVG-based export: grab the SVG from recharts
      const svgEl = chartContainerRef.current.querySelector('svg');
      if (!svgEl) return;
      const svgData = new XMLSerializer().serializeToString(svgEl);
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();
      const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
      const url = URL.createObjectURL(svgBlob);
      img.onload = () => {
        canvas.width = img.width * 2;
        canvas.height = img.height * 2;
        ctx.scale(2, 2);
        ctx.fillStyle = '#0f1117';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0);
        canvas.toBlob((blob) => {
          const a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = `jarvis_${tab}_${sessionId}.png`;
          a.click();
          URL.revokeObjectURL(a.href);
        });
        URL.revokeObjectURL(url);
        setExporting(false);
      };
      img.onerror = () => { setExporting(false); };
      img.src = url;
    } catch { setExporting(false); }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
        <div className="bg-[#14161e] border border-[#2a2d37] rounded-2xl p-8 text-[#888]">
          Loading export data...
        </div>
      </div>
    );
  }

  const turns = history?.turns || [];
  if (turns.length === 0) {
    return (
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
        <div className="bg-[#14161e] border border-[#2a2d37] rounded-2xl p-8 text-center">
          <p className="text-[#888] mb-4">No conversation data to export yet.</p>
          <button onClick={onClose} className="text-xs text-jarvis-400 hover:underline">Close</button>
        </div>
      </div>
    );
  }

  // Prepare chart data
  const hormoneData = turns.map((t) => {
    const entry = { turn: t.turn, message: t.message?.slice(0, 30) || '' };
    const h = t.hormones || {};
    for (const [key, val] of Object.entries(h)) {
      entry[key] = parseFloat(val) || 0;
    }
    return entry;
  });

  const emotionData = turns.map((t) => {
    const entry = { turn: t.turn, message: t.message?.slice(0, 30) || '' };
    const e = t.emotions || {};
    for (const [key, val] of Object.entries(e)) {
      entry[key] = parseFloat(val) || 0;
    }
    return entry;
  });

  const trustData = turns.map((t) => ({
    turn: t.turn,
    trust: t.trust || 0,
    dominant: t.dominant_emotion || '',
    message: t.message?.slice(0, 30) || '',
  }));

  const signalData = turns.map((t) => ({
    turn: t.turn,
    S: t.input?.S || 0,
    D: t.input?.D || 0,
    C: t.input?.C || 1,
    message: t.message?.slice(0, 30) || '',
  }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    const msg = payload[0]?.payload?.message || '';
    return (
      <div className="bg-[#1a1c24] border border-[#2a2d37] rounded-lg p-3 text-xs max-w-xs">
        <p className="text-[#888] mb-1">Turn {label}{msg ? `: "${msg}..."` : ''}</p>
        {payload.map((p, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
            <span className="text-[#aaa]">{p.name}:</span>
            <span className="text-white font-mono">{typeof p.value === 'number' ? p.value.toFixed(3) : p.value}</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#14161e] border border-[#2a2d37] rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#1e2028]">
          <div className="flex items-center gap-3">
            <BarChart3 size={18} className="text-jarvis-400" />
            <div>
              <h2 className="text-sm font-bold text-white">EVC Export & Analysis</h2>
              <p className="text-[10px] text-[#666]">{turns.length} turns · {sessionId}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleScreenshot}
              disabled={exporting}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-[#1a1c24] border border-[#2a2d37] text-[#aaa] hover:text-white hover:border-jarvis-600/50 transition-colors disabled:opacity-50"
            >
              <Camera size={13} />
              PNG
            </button>
            <button
              onClick={handleTxtExport}
              disabled={exporting}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-[#1a1c24] border border-[#2a2d37] text-[#aaa] hover:text-white hover:border-jarvis-600/50 transition-colors disabled:opacity-50"
            >
              <FileText size={13} />
              TXT
            </button>
            <button
              onClick={handleCsvExport}
              disabled={exporting}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-[#1a1c24] border border-[#2a2d37] text-[#aaa] hover:text-white hover:border-jarvis-600/50 transition-colors disabled:opacity-50"
            >
              <FileSpreadsheet size={13} />
              CSV
            </button>
            <button onClick={onClose} className="p-1.5 text-[#666] hover:text-white rounded-lg hover:bg-[#1a1c24] transition-colors">
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Tab bar */}
        <div className="flex gap-1 p-3 border-b border-[#1e2028]">
          <TabButton active={tab === 'hormones'} onClick={() => setTab('hormones')} icon={TrendingUp} label="Hormones" />
          <TabButton active={tab === 'emotions'} onClick={() => setTab('emotions')} icon={Heart} label="Emotions" />
          <TabButton active={tab === 'trust'} onClick={() => setTab('trust')} icon={Shield} label="Trust" />
          <TabButton active={tab === 'signals'} onClick={() => setTab('signals')} icon={BarChart3} label="Signals (S/D/C)" />
        </div>

        {/* Chart */}
        <div className="flex-1 p-4 overflow-auto" ref={chartContainerRef}>
          {tab === 'hormones' && (
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={hormoneData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2028" />
                <XAxis dataKey="turn" stroke="#555" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 1]} stroke="#555" tick={{ fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                {Object.entries(HORMONE_COLORS).map(([name, color]) => (
                  <Line key={name} type="monotone" dataKey={name} stroke={color} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}

          {tab === 'emotions' && (
            <ResponsiveContainer width="100%" height={400}>
              <AreaChart data={emotionData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2028" />
                <XAxis dataKey="turn" stroke="#555" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 1]} stroke="#555" tick={{ fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                {Object.entries(EMOTION_COLORS).map(([name, color]) => (
                  <Area key={name} type="monotone" dataKey={name} stroke={color} fill={color} fillOpacity={0.15} strokeWidth={2} />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          )}

          {tab === 'trust' && (
            <ResponsiveContainer width="100%" height={400}>
              <AreaChart data={trustData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2028" />
                <XAxis dataKey="turn" stroke="#555" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 1]} stroke="#555" tick={{ fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="trust" stroke="#34d399" fill="#34d399" fillOpacity={0.2} strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          )}

          {tab === 'signals' && (
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={signalData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2028" />
                <XAxis dataKey="turn" stroke="#555" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 1.5]} stroke="#555" tick={{ fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <Line type="monotone" dataKey="S" stroke="#34d399" strokeWidth={2} name="S (positive)" dot={{ r: 3 }} />
                <Line type="monotone" dataKey="D" stroke="#f87171" strokeWidth={2} name="D (negative)" dot={{ r: 3 }} />
                <Line type="monotone" dataKey="C" stroke="#fbbf24" strokeWidth={2} name="C (context)" dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          )}

          {/* Turn-by-turn table below chart */}
          <div className="mt-6">
            <h3 className="text-xs font-semibold text-[#888] uppercase tracking-wider mb-3">Turn-by-Turn Log</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-[11px] text-[#aaa]">
                <thead>
                  <tr className="border-b border-[#1e2028]">
                    <th className="text-left py-2 px-2 text-[#666]">#</th>
                    <th className="text-left py-2 px-2 text-[#666]">Message</th>
                    <th className="text-center py-2 px-2 text-[#666]">S</th>
                    <th className="text-center py-2 px-2 text-[#666]">D</th>
                    <th className="text-center py-2 px-2 text-[#666]">C</th>
                    <th className="text-left py-2 px-2 text-[#666]">Dominant</th>
                    <th className="text-center py-2 px-2 text-[#666]">Trust</th>
                  </tr>
                </thead>
                <tbody>
                  {turns.map((t) => (
                    <tr key={t.turn} className="border-b border-[#1a1c24] hover:bg-[#1a1c24]/50">
                      <td className="py-1.5 px-2 font-mono">{t.turn}</td>
                      <td className="py-1.5 px-2 max-w-[200px] truncate">{t.message || '-'}</td>
                      <td className="py-1.5 px-2 text-center font-mono text-emerald-400">{(t.input?.S || 0).toFixed(2)}</td>
                      <td className="py-1.5 px-2 text-center font-mono text-red-400">{(t.input?.D || 0).toFixed(2)}</td>
                      <td className="py-1.5 px-2 text-center font-mono text-amber-400">{(t.input?.C || 1).toFixed(2)}</td>
                      <td className="py-1.5 px-2" style={{ color: EMOTION_COLORS[t.dominant_emotion] || '#888' }}>
                        {t.dominant_emotion}
                      </td>
                      <td className="py-1.5 px-2 text-center font-mono">{(t.trust || 0).toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
