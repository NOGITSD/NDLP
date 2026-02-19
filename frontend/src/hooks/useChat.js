import { useState, useCallback, useRef, useEffect } from 'react';
import { sendChat, getUserConversations, getConversationMessages } from '../api';

function generateSessionId() {
  return 'session_' + Math.random().toString(36).slice(2, 10);
}

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [botState, setBotState] = useState(null);
  const [error, setError] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const sessionIdRef = useRef(generateSessionId());

  const sessionId = sessionIdRef.current;

  // Load conversation list on mount
  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = useCallback(async () => {
    try {
      const convs = await getUserConversations(30);
      setConversations(convs);
    } catch { /* guest users won't have conversations */ }
  }, []);

  const loadConversation = useCallback(async (convId) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getConversationMessages(convId);
      const msgs = data.messages || data;
      const formatted = msgs.map((m, i) => ({
        id: `${convId}_${i}`,
        role: m.role,
        content: m.content,
        timestamp: m.created_at ? new Date(m.created_at) : new Date(),
        dominant_emotion: m.dominant_emotion,
        trust_level: m.trust_level,
      }));
      setMessages(formatted);
      setActiveConvId(convId);
      // Restore EVC state (hormones/emotions/trust) with time-based decay applied
      if (data.bot_state) {
        setBotState(data.bot_state);
      }
      // Use convId as session so new messages append to the same conversation
      sessionIdRef.current = `conv_${convId}`;
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

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
      const data = await sendChat(sessionIdRef.current, text.trim());
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
      // Refresh conversation list (new conversation may have been created)
      loadConversations();
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
  }, [isLoading, loadConversations]);

  const reset = useCallback(() => {
    sessionIdRef.current = generateSessionId();
    setMessages([]);
    setBotState(null);
    setError(null);
    setActiveConvId(null);
  }, []);

  return {
    messages, isLoading, botState, error, send, reset, sessionId,
    conversations, activeConvId, loadConversation, loadConversations,
  };
}
