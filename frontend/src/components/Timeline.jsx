import React from 'react';
import './Timeline.css';

export const Timeline = ({ milestones }) => {
  if (!milestones || milestones.length === 0) {
    return (
      <div className="timeline-empty pulse">
        <p>Building chronological event timeline...</p>
      </div>
    );
  }

  // Sort milestones chronologically
  const sortedMilestones = [...milestones].sort(
    (a, b) => new Date(a.event_timestamp) - new Date(b.event_timestamp)
  );

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="timeline-wrapper">
      <div className="timeline-track"></div>
      
      <div className="timeline-nodes-list" role="list">
        {sortedMilestones.map((node, index) => (
          <div key={node.id || index} className="timeline-node" role="listitem">
            <div className="node-marker-container">
              <div className="node-dot"></div>
              {index < sortedMilestones.length - 1 && <div className="node-line"></div>}
            </div>
            
            <div className="node-content-card">
              <span className="node-timestamp">{formatDate(node.event_timestamp)}</span>
              <h4 className="node-headline">{node.headline}</h4>
              <p className="node-description">{node.description}</p>
              {node.event_type && (
                <span className="node-type-tag">{node.event_type.toLowerCase()}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
export default Timeline;
