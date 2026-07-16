import React from 'react';
import CitationCard from './CitationCard';
import './ChatMessage.css';

export const ChatMessage = ({ message }) => {
  const isUser = message.role === 'user';
  
  // Format citations if available in metadata
  const metadata = message.metadata ? (typeof message.metadata === 'string' ? JSON.parse(message.metadata) : message.metadata) : {};
  const citationsList = metadata.citations || [];
  const confidenceScore = metadata.response_confidence_score || metadata.confidence;

  const getConfidenceClass = (score) => {
    if (score >= 0.75) return 'conf-high';
    if (score >= 0.50) return 'conf-medium';
    return 'conf-low';
  };

  return (
    <div className={`chat-message-bubble-wrapper ${isUser ? 'bubble-user' : 'bubble-assistant'}`}>
      <div className="chat-bubble-avatar">
        {isUser ? 'U' : 'AI'}
      </div>
      
      <div className="chat-bubble-content-block">
        <div className="chat-bubble-payload">
          <p className="bubble-text">{message.content}</p>
          
          {!isUser && confidenceScore !== undefined && (
            <span className={`confidence-badge-chat ${getConfidenceClass(confidenceScore)}`}>
              Confidence: {Math.round(confidenceScore * 100)}%
            </span>
          )}
        </div>

        {!isUser && citationsList.length > 0 && (
          <div className="chat-bubble-citations">
            <span className="citations-header-lbl">Sources Cited:</span>
            <div className="citations-cards-stack">
              {citationsList.map((cit, idx) => (
                <CitationCard key={idx} citation={{ ...cit, index: idx + 1 }} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
export default ChatMessage;
