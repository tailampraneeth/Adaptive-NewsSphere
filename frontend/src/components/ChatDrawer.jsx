import React, { useState, useEffect, useRef } from 'react';
import useAuth from '../hooks/useAuth';
import useNotification from '../hooks/useNotification';
import chatService from '../services/chatService';
import analyticsService from '../services/analyticsService';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import LoadingSkeleton from './LoadingSkeleton';
import './ChatDrawer.css';

export const ChatDrawer = ({ storyId, isOpen, onClose }) => {
  const { user } = useAuth();
  const { showNotification } = useNotification();
  
  const [session, setSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [typing, setTyping] = useState(false);

  const scrollRef = useRef(null);

  // Initialize or fetch chat session
  useEffect(() => {
    if (!storyId || !isOpen || !user) return;

    const loadSession = async () => {
      setLoading(true);
      try {
        // List existing user sessions for this user
        const sessions = await chatService.listSessions(user.id);
        const match = sessions.find((s) => s.story_id === storyId);

        if (match) {
          setSession(match);
          const fullSession = await chatService.getSession(match.id);
          setMessages(fullSession.messages || []);
        } else {
          // Create new session
          const newSession = await chatService.createSession(user.id, storyId);
          setSession(newSession);
          setMessages([]);
        }
        analyticsService.recordChatOpen(storyId);
      } catch (err) {
        showNotification(err.message || 'Failed to initialize assistant session.', 'error');
      } finally {
        setLoading(false);
      }
    };

    loadSession();
  }, [storyId, isOpen, user, showNotification]);

  // Scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, typing]);

  const handleSendMessage = async (text) => {
    if (!session || sending) return;

    // Append user message immediately
    const userMsg = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setSending(true);
    setTyping(true);

    let assistantContent = '';
    let assistantMeta = {};

    // Append initial blank assistant message for streaming
    setMessages((prev) => [...prev, { role: 'assistant', content: '', metadata: {} }]);

    const tStart = Date.now();

    await chatService.sendMessage(
      session.id,
      text,
      (chunk) => {
        // Streaming chunk callback
        if (chunk.token) {
          assistantContent += chunk.token;
        }
        if (chunk.citations || chunk.response_confidence_score) {
          assistantMeta = {
            citations: chunk.citations || assistantMeta.citations,
            response_confidence_score: chunk.response_confidence_score || assistantMeta.response_confidence_score,
            ...chunk
          };
        }

        // Update last message
        setMessages((prev) => {
          const list = [...prev];
          const lastIdx = list.length - 1;
          list[lastIdx] = {
            role: 'assistant',
            content: assistantContent,
            metadata: assistantMeta
          };
          return list;
        });
        setTyping(false);
      },
      () => {
        // Complete callback
        setSending(false);
        analyticsService.recordLlmLatency(Date.now() - tStart);
      },
      (err) => {
        // Error callback
        setSending(false);
        setTyping(false);
        showNotification(err.message || 'Stream connection interrupted.', 'error');
      }
    );
  };

  const suggestedQuestions = [
    'What are the core consensus facts?',
    'Is there any conflicting reports or disputed views?',
    'Provide a quick summary of the main timeline.',
  ];

  if (!isOpen) return null;

  return (
    <aside className="chat-drawer-container open" aria-label="Story Assistant Chat">
      <header className="chat-drawer-header">
        <div className="hdr-meta">
          <h3>Story Assistant</h3>
          <span className="engine-version-tag">Engine v1</span>
        </div>
        <button className="chat-close-btn" onClick={onClose} aria-label="Close Chat Panel">
          &times;
        </button>
      </header>

      <div className="chat-messages-area" ref={scrollRef}>
        {loading ? (
          <LoadingSkeleton type="chat" />
        ) : messages.length === 0 ? (
          <div className="chat-welcome-state">
            <div className="welcome-avatar">🤖</div>
            <h4>Conversational RAG Grounded Assistant</h4>
            <p>
              Ask me anything about this story cluster. My responses are strictly constrained to facts reported by verified sources to prevent hallucinations.
            </p>
            
            <div className="suggested-row">
              {suggestedQuestions.map((q, idx) => (
                <button
                  key={idx}
                  className="suggested-btn"
                  onClick={() => handleSendMessage(q)}
                  disabled={sending}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="messages-list">
            {messages.map((msg, idx) => (
              <ChatMessage key={idx} message={msg} />
            ))}
            {typing && (
              <div className="typing-indicator-chat pulse">
                🤖 Assistant is crafting grounded response...
              </div>
            )}
          </div>
        )}
      </div>

      <footer className="chat-drawer-footer">
        <ChatInput onSend={handleSendMessage} disabled={loading || sending} />
      </footer>
    </aside>
  );
};
export default ChatDrawer;
