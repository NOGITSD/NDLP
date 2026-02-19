import { useState, useRef, useEffect } from 'react';
import { Play, Square, Download, FileText, FileSpreadsheet, BarChart3, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { downloadExportTxt, downloadExportCsv } from '../api';

const EMOTION_COLORS = {
  Joy: '#fbbf24', Serenity: '#34d399', Love: '#f472b6', Excitement: '#fb923c',
  Sadness: '#60a5fa', Fear: '#a78bfa', Anger: '#f87171', Surprise: '#2dd4bf',
};

export default function AutoTestPanel({ onClose, onDone }) {
  const [status, setStatus] = useState('idle'); // idle | running | done | error
  const [total, setTotal] = useState(0);
  const [current, setCurrent] = useState(0);
  const [logs, setLogs] = useState([]);
  const [sessionId, setSessionId] = useState('autotest_' + Date.now());
  const [doneSessionId, setDoneSessionId] = useState(null);
  const abortRef = useRef(null);
  const logEndRef = useRef(null);
  const statusRef = useRef('idle');
  const totalRef = useRef(0);
  const currentRef = useRef(0);
  const doneRef = useRef(false);

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const startTest = async () => {
    doneRef.current = false;
    statusRef.current = 'running';
    setStatus('running');
    setCurrent(0);
    setLogs([]);

    const sid = 'autotest_' + Date.now();
    setSessionId(sid);

    try {
      const controller = new AbortController();
      abortRef.current = controller;

      const res = await fetch(`/api/autotest/start?session_id=${encodeURIComponent(sid)}`, {
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`Server error: ${res.status} ${res.statusText}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;
          try {
            const event = JSON.parse(jsonStr);

            if (event.type === 'start') {
              setTotal(event.total);
            } else if (event.type === 'turn') {
              setCurrent(event.turn);
              setLogs(prev => [...prev, event]);
            } else if (event.type === 'error') {
              setLogs(prev => [...prev, { ...event, isError: true }]);
            } else if (event.type === 'done') {
              doneRef.current = true;
              statusRef.current = 'done';
              setStatus('done');
              setDoneSessionId(event.session_id);
            }
          } catch { /* skip bad JSON */ }
        }
      }

      // Fallback if server closed stream without sending 'done' event
      if (!doneRef.current) {
        statusRef.current = 'done';
        setStatus('done');
        setDoneSessionId(sid);
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        statusRef.current = 'idle';
        setStatus('idle');
      } else {
        statusRef.current = 'error';
        setStatus('error');
        setLogs(prev => [...prev, { type: 'error', turn: 0, error: err.message, isError: true }]);
      }
    }
  };

  const stopTest = () => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    setStatus('done');
    setDoneSessionId(sessionId);
  };

  const pct = total > 0 ? Math.round((current / total) * 100) : 0;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#14161e] border border-[#2a2d37] rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#1e2028]">
          <div className="flex items-center gap-3">
            <Play size={18} className="text-amber-400" />
            <div>
              <h2 className="text-sm font-bold text-white">Auto-Test Mode</h2>
              <p className="text-[10px] text-[#666]">Run 100 messages through full Groq + EVC pipeline</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 text-[#666] hover:text-white rounded-lg hover:bg-[#1a1c24] transition-colors">
            <X size={16} />
          </button>
        </div>

        {/* Progress bar */}
        <div className="px-4 py-3 border-b border-[#1e2028]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-[#888]">
              {status === 'idle' && 'Ready to start'}
              {status === 'running' && `Running turn ${current}/${total}...`}
              {status === 'done' && `Completed ${current}/${total} turns`}
              {status === 'error' && 'Error occurred'}
            </span>
            <span className="text-xs font-mono text-[#888]">{pct}%</span>
          </div>
          <div className="w-full h-2 bg-[#1a1c24] rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                status === 'error' ? 'bg-red-500' :
                status === 'done' ? 'bg-emerald-400' :
                'bg-jarvis-500'
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 mt-3">
            {status === 'idle' && (
              <button
                onClick={startTest}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium bg-jarvis-600 text-white hover:bg-jarvis-500 transition-colors"
              >
                <Play size={14} />
                Start 100-Message Test
              </button>
            )}
            {status === 'running' && (
              <button
                onClick={stopTest}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium bg-red-600 text-white hover:bg-red-500 transition-colors"
              >
                <Square size={14} />
                Stop
              </button>
            )}
            {(status === 'done' && doneSessionId) && (
              <>
                <button
                  onClick={() => { onDone?.(doneSessionId); }}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium bg-amber-600 text-white hover:bg-amber-500 transition-colors"
                >
                  <BarChart3 size={14} />
                  View Graphs
                </button>
                <button
                  onClick={() => downloadExportTxt(doneSessionId)}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs bg-[#1a1c24] border border-[#2a2d37] text-[#aaa] hover:text-white hover:border-jarvis-600/50 transition-colors"
                >
                  <FileText size={13} />
                  Export TXT
                </button>
                <button
                  onClick={() => downloadExportCsv(doneSessionId)}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs bg-[#1a1c24] border border-[#2a2d37] text-[#aaa] hover:text-white hover:border-jarvis-600/50 transition-colors"
                >
                  <FileSpreadsheet size={13} />
                  Export CSV
                </button>
                <button
                  onClick={() => { setStatus('idle'); setCurrent(0); setLogs([]); }}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs text-[#666] hover:text-white transition-colors"
                >
                  Re-run
                </button>
              </>
            )}
          </div>
        </div>

        {/* Live log */}
        <div className="flex-1 overflow-y-auto p-4 font-mono text-[11px]">
          {logs.length === 0 && status === 'idle' && (
            <div className="text-center text-[#555] py-8">
              <p className="mb-2">100 test messages covering:</p>
              <div className="flex flex-wrap justify-center gap-2 text-[10px]">
                <span className="px-2 py-0.5 rounded-full bg-emerald-900/30 text-emerald-400 border border-emerald-700/30">25 Positive</span>
                <span className="px-2 py-0.5 rounded-full bg-[#1a1c24] text-[#888] border border-[#2a2d37]">20 Neutral</span>
                <span className="px-2 py-0.5 rounded-full bg-amber-900/30 text-amber-400 border border-amber-700/30">15 Slightly Negative</span>
                <span className="px-2 py-0.5 rounded-full bg-red-900/30 text-red-400 border border-red-700/30">10 Very Negative</span>
                <span className="px-2 py-0.5 rounded-full bg-purple-900/30 text-purple-400 border border-purple-700/30">15 Mixed</span>
                <span className="px-2 py-0.5 rounded-full bg-jarvis-900/30 text-jarvis-400 border border-jarvis-700/30">15 Recovery Arc</span>
              </div>
            </div>
          )}

          {logs.map((log, i) => (
            <div
              key={i}
              className={`flex items-start gap-2 py-1.5 border-b border-[#1a1c24]/50 animate-message ${
                log.isError ? 'text-red-400' : ''
              }`}
            >
              {log.isError ? (
                <AlertCircle size={12} className="text-red-400 mt-0.5 flex-shrink-0" />
              ) : (
                <CheckCircle size={12} className="text-emerald-400/60 mt-0.5 flex-shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[#555] w-8">#{log.turn}</span>
                  <span className="text-[#ccc] truncate max-w-[200px]">{log.message}</span>
                  {log.dominant_emotion && (
                    <span
                      className="text-[10px] px-1.5 py-0.5 rounded-full"
                      style={{
                        color: EMOTION_COLORS[log.dominant_emotion] || '#888',
                        backgroundColor: (EMOTION_COLORS[log.dominant_emotion] || '#888') + '15',
                        border: `1px solid ${(EMOTION_COLORS[log.dominant_emotion] || '#888')}30`,
                      }}
                    >
                      {log.dominant_emotion}
                    </span>
                  )}
                  {log.trust !== undefined && (
                    <span className="text-[10px] text-[#555]">T:{log.trust}</span>
                  )}
                  {log.signals && (
                    <span className="text-[10px] text-[#444]">
                      S:{log.signals.S} D:{log.signals.D}
                    </span>
                  )}
                  {log.elapsed_sec !== undefined && (
                    <span className="text-[10px] text-[#333]">{log.elapsed_sec}s</span>
                  )}
                </div>
                {log.reply && (
                  <div className="text-[10px] text-[#555] mt-0.5 truncate max-w-[600px]">
                    → {log.reply}
                  </div>
                )}
                {log.isError && log.error && (
                  <div className="text-[10px] text-red-400/80 mt-0.5">Error: {log.error}</div>
                )}
              </div>
            </div>
          ))}

          {status === 'running' && (
            <div className="flex items-center gap-2 py-2 text-jarvis-400">
              <Loader2 size={12} className="animate-spin" />
              <span>Processing turn {current + 1}...</span>
            </div>
          )}

          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
}
