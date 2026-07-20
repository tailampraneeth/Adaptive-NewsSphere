import React, { useState, useEffect } from 'react';
import feedService from '../services/feedService';
import StoryCard from '../components/StoryCard';
import LoadingSkeleton from '../components/LoadingSkeleton';
import './Dashboard.css'; // sharing layout css classes

export const TrendingPage = () => {
  const [stories, setStories] = useState([]);
  const [cursor, setCursor] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const loadInitialTrending = async () => {
    setLoading(true);
    try {
      const data = await feedService.getTrendingFeed('', 20);
      setStories(data.results || []);
      setCursor(data.next_cursor || '');
    } catch (err) {
      console.error("Failed to load trending stream:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitialTrending();
  }, []);

  const loadMoreTrending = async () => {
    if (loadingMore || !cursor) return;
    setLoadingMore(true);
    try {
      const data = await feedService.getTrendingFeed(cursor, 15);
      setStories(prev => [...prev, ...(data.results || [])]);
      setCursor(data.next_cursor || '');
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingMore(false);
    }
  };

  return (
    <div className="dashboard-container">
      <section className="feed-section">
        <header className="feed-header-row">
          <h2>Trending Watch</h2>
        </header>

        {loading ? (
          <LoadingSkeleton type="feed" />
        ) : stories.length === 0 ? (
          <div className="feed-empty-state">
            <div className="empty-icon">📈</div>
            <h3>No trending streams yet</h3>
            <p>We are collecting data across active RSS sources.</p>
          </div>
        ) : (
          <div className="feed-list-container">
            {stories.map((story) => (
              <StoryCard
                key={story.story_id}
                story={story}
              />
            ))}
          </div>
        )}

        {cursor && !loading && (
          <div className="load-more-container">
            <button
              className="load-more-btn"
              onClick={loadMoreTrending}
              disabled={loadingMore}
            >
              {loadingMore ? 'Resolving new streams...' : 'Load More trending'}
            </button>
          </div>
        )}
      </section>
    </div>
  );
};
export default TrendingPage;
