import React, { useState } from 'react';
import './VerificationPanel.css';

export const VerificationPanel = ({ verificationScore, hasConflicts, evidence, metadata }) => {
  const [activeTab, setActiveTab] = useState('corroborated');

  // Parse supporting vs conflicting from metadata or evidence
  const corroboratedClaims = evidence ? evidence.filter(e => !e.is_conflict) : [];
  const disputedClaims = evidence ? evidence.filter(e => e.is_conflict) : [];

  const getAgreementText = (score) => {
    if (score >= 0.8) return 'Strong Publisher Consensus';
    if (score >= 0.5) return 'Moderate Agreement';
    return 'Diverging / Uncorroborated Reports';
  };

  return (
    <div className="verification-container">
      <div className="verification-status-card">
        <div className="status-metric">
          <span className="metric-title">Claims Agreement</span>
          <span className="metric-score">{Math.round((verificationScore || 0) * 100)}%</span>
        </div>
        <div className="status-summary">
          <h4>{getAgreementText(verificationScore)}</h4>
          <p>
            {hasConflicts 
              ? 'Factual contradictions or numerical conflicts have been detected across reporting outlets. Tap Disputed Claims for detail.'
              : 'Outlets are reporting consistent key facts. Statements are corroborated across multiple sources.'
            }
          </p>
        </div>
      </div>

      <div className="claims-panel-tabs">
        <button 
          className={`tab-btn ${activeTab === 'corroborated' ? 'active' : ''}`}
          onClick={() => setActiveTab('corroborated')}
        >
          Corroborated Facts ({corroboratedClaims.length})
        </button>
        <button 
          className={`tab-btn ${activeTab === 'disputed' ? 'active' : ''}`}
          onClick={() => setActiveTab('disputed')}
        >
          Disputed / Conflicting ({disputedClaims.length})
        </button>
      </div>

      <div className="claims-list-body">
        {activeTab === 'corroborated' && (
          <div className="claims-stack">
            {corroboratedClaims.length === 0 ? (
              <p className="no-claims">No corroborated claims cataloged for this story cluster.</p>
            ) : (
              corroboratedClaims.map((claim, idx) => (
                <div key={idx} className="claim-item-card">
                  <div className="claim-text">
                    <strong>Fact:</strong> {claim.claim_text || claim.statement}
                  </div>
                  <div className="claim-provenance">
                    <span className="sources-count">Corroborated by {claim.source_count || 2} publishers</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'disputed' && (
          <div className="claims-stack">
            {disputedClaims.length === 0 ? (
              <p className="no-claims">No factual conflicts detected in this cluster. Outlets are in consensus.</p>
            ) : (
              disputedClaims.map((claim, idx) => (
                <div key={idx} className="claim-item-card conflict-item">
                  <div className="claim-text">
                    <strong>Contradiction:</strong> {claim.claim_text || claim.statement}
                  </div>
                  <div className="claim-provenance">
                    <span className="conflict-tag">Disputed</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};
export default VerificationPanel;
