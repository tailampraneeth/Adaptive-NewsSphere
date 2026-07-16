import React from 'react';
import './LoadingSkeleton.css';

export const LoadingSkeleton = ({ type = 'feed' }) => {
  if (type === 'page') {
    return (
      <div className="skeleton-page-container">
        <div className="skeleton-spinner"></div>
        <p className="pulse">Loading NewsSphere...</p>
      </div>
    );
  }

  if (type === 'chat') {
    return (
      <div className="skeleton-chat-container">
        <div className="skeleton-bubble left pulse"></div>
        <div className="skeleton-bubble right pulse"></div>
        <div className="skeleton-bubble left pulse"></div>
      </div>
    );
  }

  // Default: feed card skeletons
  return (
    <div className="skeleton-feed-grid">
      {[1, 2, 3].map((i) => (
        <div key={i} className="skeleton-card pulse">
          <div className="skeleton-line title"></div>
          <div className="skeleton-line body"></div>
          <div className="skeleton-line footer"></div>
        </div>
      ))}
    </div>
  );
};
export default LoadingSkeleton;
