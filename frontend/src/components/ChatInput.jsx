import { useState, useRef, useEffect } from 'react';
import { SendHorizonal } from 'lucide-react';

export default function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState('');
  const inputRef = useRef(null);

  useEffect(() => {
    if (!disabled) inputRef.current?.focus();
  }, [disabled]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text);
    setText('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 p-4 border-t border-[#1e2028]">
      <div className="flex-1 relative">
        <textarea
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="พิมพ์ข้อความ..."
          disabled={disabled}
          rows={1}
          className="w-full resize-none bg-[#1a1c24] border border-[#2a2d37] rounded-xl px-4 py-3 pr-12 text-sm text-[#e4e5e7] placeholder-[#555] focus:outline-none focus:border-jarvis-600/60 focus:ring-1 focus:ring-jarvis-600/30 transition-colors disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!text.trim() || disabled}
          className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center rounded-lg bg-jarvis-600 text-white hover:bg-jarvis-500 disabled:opacity-30 disabled:hover:bg-jarvis-600 transition-colors"
        >
          <SendHorizonal size={16} />
        </button>
      </div>
    </form>
  );
}
