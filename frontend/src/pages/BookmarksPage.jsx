import React, { useState, useEffect } from 'react';
import bookmarkService from '../services/bookmarkService';
import StoryCard from '../components/StoryCard';
import LoadingSkeleton from '../components/LoadingSkeleton';
import useNotification from '../hooks/useNotification';
import './Dashboard.css';

export const BookmarksPage = () => {
  const { showNotification } = useNotification();
  
  const [bookmarks, setBookmarks] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadBookmarks = async () => {
    setLoading(true);
    try {
      if (!navigator.onLine) {
        const cached = localStorage.getItem('heimdall_cached_bookmarks');
        if (cached) {
          setBookmarks(JSON.parse(cached) || []);
        }
        setLoading(false);
        return;
      }

      const list = await bookmarkService.listBookmarks();
      setBookmarks(list || []);
      localStorage.setItem('heimdall_cached_bookmarks', JSON.stringify(list || []));
    } catch (err) {
      showNotification(err.message || 'Failed to load bookmarks.', 'error');
      // Fallback
      const cached = localStorage.getItem('heimdall_cached_bookmarks');
      if (cached) setBookmarks(JSON.parse(cached) || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBookmarks();
  }, []);

  return (
    <div className="dashboard-container">
      <section className="feed-section">
        <header className="feed-header-row">
          <h2>Saved Intelligence</h2>
        </header>

        {loading ? (
          <LoadingSkeleton type="feed" />
        ) : bookmarks.length === 0 ? (
          <div className="feed-empty-state animate-slide-up">
            <div className="empty-icon">📁</div>
            <h3>No bookmarks saved</h3>
            <p>Tap the bookmark icon inside story briefs to save them here for offline access.</p>
          </div>
        ) : (
          <div className="feed-list-container">
            {bookmarks.map((b) => (
              <StoryCard
                key={b.story_id}
                story={{
                  story_id: b.story_id,
                  title: b.title,
                  predicted_category: b.predicted_category,
                  summary: '', // bookmarks item view is simplified
                  article_count: 1,
                  publisher_diversity: 1,
                  image_url: b.image_url,
                  verification_label: 'Saved briefing',
                  verification_color: 'gray',
                  verification_icon: '🖹'
                }}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
};
export default BookmarksPage;
