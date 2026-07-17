import React from 'react';
import { useNavigate } from 'react-router-dom';
import './StoryCard.css';

export const StoryCard = ({ story, onInteract }) => {
  const navigate = useNavigate();

  const handleCardClick = () => {
    if (onInteract) {
      onInteract(story.story_id, 'click');
    }
    navigate(`/story/${story.story_id}`);
  };

  return (
    <article
      className="story-card animate-slide-up"
      onClick={handleCardClick}
      tabIndex="0"
      role="button"
      aria-label={`Read story: ${story.title}`}
    >
      {story.image_url && (
        <div className="story-card-image-wrapper">
          <img src={story.image_url} alt="" className="story-card-image" loading="lazy" />
        </div>
      )}

      <div className="story-card-content">
        <header className="story-card-header">
          <div className="badge-row">
            <span className={`badge badge-color-${story.verification_color}`}>
              <span className="badge-icon">{story.verification_icon}</span>
              {story.verification_label}
            </span>
            <span className="category-label-tag">{story.predicted_category}</span>
          </div>
          <h3 className="story-title">{story.title}</h3>
        </header>

        <p className="story-summary-preview">
          {story.summary ? (story.summary.length > 140 ? story.summary.substring(0, 140) + '...' : story.summary) : 'No summary available.'}
        </p>

        <footer className="story-card-footer">
          <div className="source-stats">
            <span className="stat-item">
              <strong>{story.article_count}</strong> {story.article_count === 1 ? 'article' : 'articles'}
            </span>
            <span className="stat-separator">•</span>
            <span className="stat-item">
              <strong>{story.publisher_diversity}</strong> {story.publisher_diversity === 1 ? 'source' : 'sources'}
            </span>
          </div>
          {story.explanation && (
            <div className="story-recommendation-explanation">
              {story.explanation}
            </div>
          )}
        </footer>
      </div>
    </article>
  );
};
export default StoryCard;
