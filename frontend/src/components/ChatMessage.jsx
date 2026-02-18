import { Bot, User, Zap, Brain, Sparkles } from 'lucide-react';

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`animate-message flex gap-3 px-4 py-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-jarvis-700/30 border border-jarvis-600/40 flex items-center justify-center mt-1">
          <Bot size={16} className="text-jarvis-400" />
        </div>
      )}

      <div className={`max-w-[75%] flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
            isUser
              ? 'bg-jarvis-600 text-white rounded-br-md'
              : message.isError
                ? 'bg-red-900/30 border border-red-700/40 text-red-200 rounded-bl-md'
                : 'bg-[#1e2028] border border-[#2a2d37] text-[#e4e5e7] rounded-bl-md'
          }`}
        >
          {message.content}
        </div>

        {/* Meta badges for bot messages */}
        {!isUser && !message.isError && (message.matchedSkill || message.memoryUsed || (message.learnedFacts && message.learnedFacts.length > 0)) && (
          <div className="flex flex-wrap gap-1.5 px-1">
            {message.matchedSkill && (
              <span className="inline-flex items-center gap-1 text-[10px] text-jarvis-400 bg-jarvis-900/30 border border-jarvis-700/30 rounded-full px-2 py-0.5">
                <Zap size={10} />
                {message.matchedSkill}
              </span>
            )}
            {message.memoryUsed && (
              <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-900/30 border border-emerald-700/30 rounded-full px-2 py-0.5">
                <Brain size={10} />
                memory
              </span>
            )}
            {message.learnedFacts && message.learnedFacts.length > 0 && (
              <span className="inline-flex items-center gap-1 text-[10px] text-amber-400 bg-amber-900/30 border border-amber-700/30 rounded-full px-2 py-0.5"
                    title={message.learnedFacts.map(f => `${f.key}: ${f.value}`).join(', ')}>
                <Sparkles size={10} />
                learned {message.learnedFacts.length} fact{message.learnedFacts.length > 1 ? 's' : ''}
              </span>
            )}
          </div>
        )}

        <span className="text-[10px] text-[#555] px-1">
          {message.timestamp.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[#2a2d37] border border-[#3a3d47] flex items-center justify-center mt-1">
          <User size={16} className="text-[#8a8d97]" />
        </div>
      )}
    </div>
  );
}
