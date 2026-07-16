import React from 'react';
import './CitationCard.css';

export const CitationCard = ({ citation }) => {
  return (
    <div className="citation-node-card">
      <div className="cit-badge">Source [{citation.index || 1}]</div>
      <div className="cit-body">
        <h5 className="cit-publisher">{citation.publisher_name}</h5>
        {citation.article_title && <p className="cit-title">"{citation.article_title}"</p>}
        <div className="cit-metrics">
          {citation.similarity !== undefined && (
            <span className="cit-similarity">
              Similarity: <strong>{Math.round(citation.similarity * 100)}%</strong>
            </span>
          )}
          {citation.confidence !== undefined && (
            <span className="cit-confidence">
              Confidence: <strong>{Math.round(citation.confidence * 100)}%</strong>
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
export default CitationCard;
