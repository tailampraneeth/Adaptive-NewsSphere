import React, { useState } from 'react';
import './SummaryCards.css';

export const SummaryCards = ({ summaryQuick, summaryBeginner, summaryProfessional, defaultSummary }) => {
  const [level, setLevel] = useState('quick');

  const getSummaryText = () => {
    if (level === 'quick') return summaryQuick || defaultSummary || 'Quick scan summary loading...';
    if (level === 'beginner') return summaryBeginner || defaultSummary || 'Conceptual summary loading...';
    return summaryProfessional || defaultSummary || 'Professional analysis loading...';
  };

  return (
    <div className="summary-tab-container">
      <div className="summary-tabs-row" role="tablist" aria-label="Summary Complexity Level">
        <button
          className={`summary-tab ${level === 'quick' ? 'active' : ''}`}
          onClick={() => setLevel('quick')}
          role="tab"
          aria-selected={level === 'quick'}
        >
          Quick Scan
        </button>
        <button
          className={`summary-tab ${level === 'beginner' ? 'active' : ''}`}
          onClick={() => setLevel('beginner')}
          role="tab"
          aria-selected={level === 'beginner'}
        >
          Beginner View
        </button>
        <button
          className={`summary-tab ${level === 'professional' ? 'active' : ''}`}
          onClick={() => setLevel('professional')}
          role="tab"
          aria-selected={level === 'professional'}
        >
          Professional
        </button>
      </div>

      <div className="summary-tab-panel animate-slide-up" role="tabpanel">
        <p className="summary-body-text">{getSummaryText()}</p>
      </div>
    </div>
  );
};
export default SummaryCards;
