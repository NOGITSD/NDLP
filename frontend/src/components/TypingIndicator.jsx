import { Bot } from 'lucide-react';

export default function TypingIndicator() {
  return (
    <div className="animate-message flex gap-3 px-4 py-3">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-jarvis-700/30 border border-jarvis-600/40 flex items-center justify-center mt-1">
        <Bot size={16} className="text-jarvis-400" />
      </div>
      <div className="bg-[#1e2028] border border-[#2a2d37] rounded-2xl rounded-bl-md px-4 py-3 flex gap-1.5 items-center">
        <div className="typing-dot w-2 h-2 rounded-full bg-jarvis-400" />
        <div className="typing-dot w-2 h-2 rounded-full bg-jarvis-400" />
        <div className="typing-dot w-2 h-2 rounded-full bg-jarvis-400" />
      </div>
    </div>
  );
}
