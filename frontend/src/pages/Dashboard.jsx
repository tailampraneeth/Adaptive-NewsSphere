import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import useNotification from '../hooks/useNotification';
import feedService from '../services/feedService';
import StoryCard from '../components/StoryCard';
import LoadingSkeleton from '../components/LoadingSkeleton';
import './Dashboard.css';

export const Dashboard = () => {
  const { user } = useAuth();
  const { showNotification } = useNotification();
  const navigate = useNavigate();

  const [stories, setStories] = useState([]);
  const [cursor, setCursor] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  
  // Daily Brief States
  const [showBrief, setShowBrief] = useState(false);
  const [briefStories, setBriefStories] = useState([]);

  // Check connectivity
  useEffect(() => {
    const goOnline = () => {
      setIsOffline(false);
      showNotification('You are back online.', 'success');
      loadInitialFeed();
    };
    const goOffline = () => {
      setIsOffline(true);
      showNotification('You are offline. Showing cached content.', 'warning');
      loadCachedFeed();
    };

    window.addEventListener('online', goOnline);
    window.addEventListener('offline', goOffline);
    return () => {
      window.removeEventListener('online', goOnline);
      window.removeEventListener('offline', goOffline);
    };
  }, [showNotification]);

  const loadCachedFeed = () => {
    const cached = localStorage.getItem('heimdall_cached_feed');
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        setStories(parsed.results || []);
        setCursor(parsed.next_cursor || '');
        // Load brief stories from cache if possible
        setBriefStories(parsed.results?.slice(0, 5) || []);
        checkDailyBriefWindow(parsed.results?.slice(0, 5) || []);
      } catch (_) {
        setStories([]);
      }
    }
    setLoading(false);
  };

  const checkDailyBriefWindow = (feedStories) => {
    if (!feedStories || feedStories.length === 0) return;

    // Check if dismissed today
    const today = new Date().toDateString();
    const dismissedDate = localStorage.getItem('heimdall_brief_dismissed_date');
    if (dismissedDate === today) {
      setShowBrief(false);
      return;
    }

    // Check hourly window
    const hour = new Date().getHours();
    const briefPref = user?.brief_time || 'morning';
    
    let isWindow = false;
    if (briefPref === 'morning' && hour >= 6 && hour < 12) isWindow = true;
    else if (briefPref === 'afternoon' && hour >= 12 && hour < 18) isWindow = true;
    else if (briefPref === 'evening' && hour >= 18 && hour < 24) isWindow = true;

    if (isWindow) {
      setBriefStories(feedStories.slice(0, 5));
      setShowBrief(true);
    } else {
      setShowBrief(false);
    }
  };

  const loadInitialFeed = async () => {
    setLoading(true);
    try {
      if (!navigator.onLine) {
        loadCachedFeed();
        return;
      }
      const data = await feedService.getPersonalizedFeed('', 20);
      setStories(data.results || []);
      setCursor(data.next_cursor || '');
      
      // Store in cache for offline
      localStorage.setItem('heimdall_cached_feed', JSON.stringify(data));
      
      checkDailyBriefWindow(data.results || []);
    } catch (err) {
      showNotification(err.message || 'Failed to load feed.', 'error');
      loadCachedFeed(); // Fallback to cache on api fail
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      loadInitialFeed();
    }
  }, [user]);

  const loadMoreStories = async () => {
    if (loadingMore || !cursor) return;
    setLoadingMore(true);
    try {
      const data = await feedService.getPersonalizedFeed(cursor, 15);
      setStories(prev => [...prev, ...(data.results || [])]);
      setCursor(data.next_cursor || '');
    } catch (err) {
      showNotification(err.message || 'Failed to load more stories.', 'error');
    } finally {
      setLoadingMore(false);
    }
  };

  const handleInteraction = async (storyId, type) => {
    try {
      await feedService.recordInteraction(storyId, type);
    } catch (_) {
      // Telemetry fail silently
    }
  };

  const dismissBrief = () => {
    const today = new Date().toDateString();
    localStorage.setItem('heimdall_brief_dismissed_date', today);
    setShowBrief(false);
  };

  return (
    <div className="dashboard-container">
      {isOffline && (
        <div className="offline-banner animate-slide-down">
          <span>Offline Mode: displaying cached feed.</span>
        </div>
      )}

      {/* Daily Briefing Banner (Polish #4) */}
      {showBrief && briefStories.length > 0 && (
        <section className="daily-brief-section animate-slide-up">
          <div className="brief-card">
            <div className="brief-card-header">
              <div className="brief-title-row">
                <span className="brief-badge">⚡ Daily Brief</span>
                <h3>Your Watchful Briefing</h3>
              </div>
              <button className="dismiss-brief-btn" onClick={dismissBrief} aria-label="Dismiss Briefing">
                ✕
              </button>
            </div>
            <p className="brief-desc">Here are today's top 5 must-read stories tailored for you:</p>
            <div className="brief-stories-list">
              {briefStories.map((s, idx) => (
                <div key={s.story_id} className="brief-story-item" onClick={() => navigate(`/story/${s.story_id}`)}>
                  <span className="brief-number">{idx + 1}</span>
                  <span className="brief-story-title">{s.title}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="feed-section">
        <header className="feed-header-row">
          <h2>Personalized Intell Feed</h2>
          <button className="refresh-feed-btn" onClick={loadInitialFeed} disabled={loading} aria-label="Refresh Feed">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
            </svg>
          </button>
        </header>

        {loading ? (
          <LoadingSkeleton type="feed" />
        ) : stories.length === 0 ? (
          <div className="feed-empty-state animate-slide-up">
            <div className="empty-icon">🦉</div>
            <h3>Nothing reported yet</h3>
            <p>Your RSS watchtower is scanning. New story clusters will appear soon.</p>
          </div>
        ) : (
          <div className="feed-list-container">
            {stories.map((story) => (
              <StoryCard
                key={story.story_id}
                story={story}
                onInteract={handleInteraction}
              />
            ))}
          </div>
        )}

        {cursor && !loading && (
          <div className="load-more-container">
            <button
              className="load-more-btn"
              onClick={loadMoreStories}
              disabled={loadingMore}
            >
              {loadingMore ? 'Resolving new streams...' : 'Load Older intelligence'}
            </button>
          </div>
        )}
      </section>
    </div>
  );
};
export default Dashboard;
