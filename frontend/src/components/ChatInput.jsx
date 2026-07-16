import React, { useState } from 'react';
import './ChatInput.css';

export const ChatInput = ({ onSend, disabled }) => {
  const [text, setText] = useState('');

  const handleFormSubmit = (e) => {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText('');
  };

  return (
    <form onSubmit={handleFormSubmit} className="chat-input-form">
      <input
        type="text"
        className="chat-input-text"
        placeholder={disabled ? 'Waiting for assistant response...' : 'Ask a grounding query...'}
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
        aria-label="Ask a grounding query"
      />
      <button
        type="submit"
        className="chat-send-btn"
        disabled={disabled || !text.trim()}
        aria-label="Send Message"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
          <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
        </svg>
      </button>
    </form>
  );
};
export default ChatInput;
