import React, { useState, useEffect } from 'react';
import useAuth from '../hooks/useAuth';
import useNotification from '../hooks/useNotification';
import feedService from '../services/feedService';
import chatService from '../services/chatService';
import FeedList from '../components/FeedList';
import RecommendationPanel from '../components/RecommendationPanel';
import ChatDrawer from '../components/ChatDrawer';
import './Dashboard.css';

export const Dashboard = () => {
  const { user } = useAuth();
  const { showNotification } = useNotification();

  const [feed, setFeed] = useState(null);
  const [activeSessions, setActiveSessions] = useState([]);
  const [recStats, setRecStats] = useState(null);
  const [userStats, setUserStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedStoryId, setSelectedStoryId] = useState(null);

  const loadDashboardData = async () => {
    if (!user) return;
    setLoading(true);
    try {
      // 1. Load feed
      const feedData = await feedService.getPersonalizedFeed(user.id);
      setFeed(feedData);

      // 2. Load active chat sessions
      const sessions = await chatService.listSessions(user.id);
      setActiveSessions(sessions);

      // 3. Load recommendation stats
      const stats = await feedService.getRecommendationStats();
      setRecStats(stats);

      // 4. Load user profile health
      const uStats = await feedService.getProfileHealth(user.id);
      setUserStats(uStats);
    } catch (err) {
      showNotification(err.message || 'Error resolving dashboard data.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, [user]);

  const handleInteraction = async (storyId, type) => {
    if (!user) return;
    try {
      await feedService.recordInteraction(user.id, storyId, type);
    } catch (_) {
      // Fail silently for telemetry record
    }
  };

  const handleOpenChat = (storyId) => {
    setSelectedStoryId(storyId);
    setDrawerOpen(true);
  };

  // Compile aggregate metrics
  const totalStories = feed?.stories?.length || 0;
  const verifiedStoriesCount = feed?.stories?.filter(s => s.verification_score >= 0.70).length || 0;

  // Extract unique topics from feed stories
  const trendingTopics = [];
  if (feed?.stories) {
    const topicSet = new Set();
    feed.stories.forEach(s => {
      // Pull representative keywords or mock topics
      if (s.recommendation_metadata?.matched_categories) {
        s.recommendation_metadata.matched_categories.forEach(c => topicSet.add(c));
      }
    });
    topicSet.forEach(t => trendingTopics.push(t));
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-main-content">
        <header className="dashboard-welcome-header">
          <h1>Welcome to Your NewsSphere</h1>
          <p>Verified, context-bound story intelligence platform.</p>
        </header>

        <section className="feed-section">
          <div className="feed-header-row">
            <h2>Personalized Story Feed</h2>
            <span className="feed-strategy-tag">
              Strategy: {feed?.strategy ? feed.strategy.replace('_', ' ') : 'loading'}
            </span>
          </div>
          <FeedList
            stories={feed?.stories}
            loading={loading}
            onInteract={handleInteraction}
          />
        </section>
      </div>

      <div className="dashboard-sidebar-panels">
        {/* Recommendation Statistics Panel */}
        <RecommendationPanel stats={recStats} userStats={userStats} />

        {/* Stories Statistics */}
        <section className="dash-panel-card">
          <h3>Sphere Summary</h3>
          <div className="summary-numbers">
            <div className="number-item">
              <span className="number-value">{totalStories}</span>
              <span className="number-label">Stories Today</span>
            </div>
            <div className="number-item">
              <span className="number-value">{verifiedStoriesCount}</span>
              <span className="number-label">Verified Stories</span>
            </div>
          </div>
        </section>

        {/* Trending Topics Panel */}
        <section className="dash-panel-card">
          <h3>Trending Topics</h3>
          <div className="topics-pill-box">
            {trendingTopics.length === 0 ? (
              <span className="no-topics">Ingesting topics...</span>
            ) : (
              trendingTopics.map((topic, idx) => (
                <span key={idx} className="topic-pill-tag">
                  #{topic}
                </span>
              ))
            )}
          </div>
        </section>

        {/* Active Conversations Panel */}
        <section className="dash-panel-card active-sessions-panel">
          <h3>Active Conversations</h3>
          <div className="sessions-list">
            {activeSessions.length === 0 ? (
              <p className="no-sessions">No active conversations threads.</p>
            ) : (
              activeSessions.map((session) => (
                <div key={session.id} className="session-link-item">
                  <div className="session-info">
                    <span className="session-title-lbl">{session.title || 'Conversational Session'}</span>
                    <span className="session-msgs-count">{session.message_count || 0} messages</span>
                  </div>
                  <button 
                    className="session-resume-btn"
                    onClick={() => handleOpenChat(session.story_id)}
                  >
                    Resume
                  </button>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      {selectedStoryId && (
        <ChatDrawer
          storyId={selectedStoryId}
          isOpen={drawerOpen}
          onClose={() => setDrawerOpen(false)}
        />
      )}
    </div>
  );
};
export default Dashboard;
