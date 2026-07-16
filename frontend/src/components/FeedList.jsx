import React from 'react';
import StoryCard from './StoryCard';
import LoadingSkeleton from './LoadingSkeleton';
import './FeedList.css';

export const FeedList = ({ stories, loading, onInteract }) => {
  if (loading) {
    return <LoadingSkeleton type="feed" />;
  }

  if (!stories || stories.length === 0) {
    return (
      <div className="feed-empty-state">
        <div className="empty-icon">🍃</div>
        <h3>Quiet Day in the Sphere</h3>
        <p>No new story clusters matching your profile are reported right now. Check back shortly.</p>
      </div>
    );
  }

  return (
    <div className="feed-list-container">
      {stories.map((story) => (
        <StoryCard key={story.id} story={story} onInteract={onInteract} />
      ))}
    </div>
  );
};
export default FeedList;
