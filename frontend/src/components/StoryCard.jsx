import React from 'react';
import { useNavigate } from 'react-router-dom';
import './StoryCard.css';

export const StoryCard = ({ story, onInteract }) => {
  const navigate = useNavigate();

  const handleCardClick = () => {
    if (onInteract) {
      onInteract(story.id, 'click');
    }
    navigate(`/story/${story.id}`);
  };

  const getScoreClass = (score) => {
    if (score >= 0.70) return 'score-high';
    if (score >= 0.45) return 'score-medium';
    return 'score-low';
  };

  return (
    <article className="story-card animate-slide-up" onClick={handleCardClick} tabIndex="0" role="button" aria-label={`Read story: ${story.title}`}>
      <header className="story-card-header">
        <div className="badge-row">
          {story.verification_score !== undefined && (
            <span className={`badge ${getScoreClass(story.verification_score)}`}>
              Verified {Math.round(story.verification_score * 100)}%
            </span>
          )}
          {story.has_conflicts && (
            <span className="badge conflict-badge">Disputed Views</span>
          )}
          {story.trending_score > 0.6 && (
            <span className="badge trending-badge">Trending</span>
          )}
        </div>
        <h3 className="story-title">{story.title}</h3>
      </header>

      <div className="story-summary-preview">
        <p>{story.summary ? story.summary.substring(0, 180) + '...' : 'No summary generated yet.'}</p>
      </div>

      <footer className="story-card-footer">
        <div className="source-stats">
          <span className="stat-item">
            <strong>{story.article_count}</strong> articles
          </span>
          <span className="stat-separator">•</span>
          <span className="stat-item">
            <strong>{story.publisher_diversity}</strong> sources
          </span>
        </div>
        <div className="story-meta-indicators">
          {story.credibility_score !== undefined && (
            <span className="credibility-indicator" title="Source Credibility Rating">
              Trust Score: <strong>{Math.round(story.credibility_score * 100)}%</strong>
            </span>
          )}
        </div>
      </footer>
    </article>
  );
};
export default StoryCard;
