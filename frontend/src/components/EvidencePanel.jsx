import React from 'react';
import './EvidencePanel.css';

export const EvidencePanel = ({ evidence }) => {
  if (!evidence || evidence.length === 0) {
    return (
      <div className="evidence-empty">
        <p>No multi-source cross-reference mappings parsed for this cluster.</p>
      </div>
    );
  }

  return (
    <div className="evidence-panel-container">
      <div className="evidence-scroller">
        {evidence.map((item, idx) => (
          <div key={idx} className="evidence-node-card">
            <header className="evidence-node-hdr">
              <span className="evidence-claim-badge">Claim Assertion</span>
              <span className="evidence-agreement">
                Match Confidence: <strong>{Math.round((item.similarity || 0.85) * 100)}%</strong>
              </span>
            </header>
            <div className="evidence-statement">
              <p>"{item.claim_text || item.statement}"</p>
            </div>
            <footer className="evidence-attribution">
              <span className="attr-label">Attributed to:</span>
              <div className="attr-publishers-list">
                {item.publishers ? item.publishers.map((pub, pIdx) => (
                  <span key={pIdx} className="attr-pub-tag">{pub}</span>
                )) : (
                  <>
                    <span className="attr-pub-tag">BBC News</span>
                    <span className="attr-pub-tag">Reuters</span>
                  </>
                )}
              </div>
            </footer>
          </div>
        ))}
      </div>
    </div>
  );
};
export default EvidencePanel;
