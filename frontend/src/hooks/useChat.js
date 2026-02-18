import { useState, useCallback, useRef } from 'react';
import { sendChat } from '../api';

function generateSessionId() {
  return 'session_' + Math.random().toString(36).slice(2, 10);
}

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [botState, setBotState] = useState(null);
  const [error, setError] = useState(null);
  const sessionIdRef = useRef(generateSessionId());

  const sessionId = sessionIdRef.current;

  const send = useCallback(async (text) => {
    if (!text.trim() || isLoading) return;
    setError(null);

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const data = await sendChat(sessionId, text.trim());
      const botMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        userEmotion: data.user_emotion,
        signals: data.signals,
        matchedSkill: data.matched_skill,
        memoryUsed: data.memory_used,
        learnedFacts: data.learned_facts || [],
      };
      setMessages(prev => [...prev, botMsg]);
      setBotState(data.bot_state);
    } catch (err) {
      setError(err.message);
      const errMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'ขออภัยครับ เกิดข้อผิดพลาด กรุณาลองอีกครั้ง',
        timestamp: new Date(),
        isError: true,
      };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, sessionId]);

  const reset = useCallback(() => {
    sessionIdRef.current = generateSessionId();
    setMessages([]);
    setBotState(null);
    setError(null);
  }, []);

  return { messages, isLoading, botState, error, send, reset, sessionId };
}
