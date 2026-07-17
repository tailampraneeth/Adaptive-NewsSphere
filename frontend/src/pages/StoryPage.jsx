import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import useNotification from '../hooks/useNotification';
import storyService from '../services/storyService';
import feedService from '../services/feedService';
import bookmarkService from '../services/bookmarkService';
import Timeline from '../components/Timeline';
import LoadingSkeleton from '../components/LoadingSkeleton';
import './StoryPage.css';

export const StoryPage = () => {
  const { id } = useParams();
  const { user } = useAuth();
  const { showNotification } = useNotification();
  const navigate = useNavigate();

  const [story, setStory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [bookmarked, setBookmarked] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [sourcesCollapsed, setSourcesCollapsed] = useState(true);

  // 1. Reading completion & scroll tracking
  useEffect(() => {
    const startTime = Date.now();
    let maxProgress = 0;

    const handleScroll = () => {
      const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
      if (totalHeight <= 0) return;
      const progress = Math.round((window.scrollY / totalHeight) * 100);
      maxProgress = Math.max(maxProgress, progress);
      setScrollProgress(Math.min(100, progress));
    };

    window.addEventListener('scroll', handleScroll);

    return () => {
      window.removeEventListener('scroll', handleScroll);
      const dwellSeconds = Math.round((Date.now() - startTime) / 1000);
      if (dwellSeconds > 1 && id) {
        const interactionType = maxProgress >= 70 ? 'finish' : 'read';
        feedService.recordInteraction(id, interactionType, Math.min(100, maxProgress), dwellSeconds)
          .catch(() => {});
      }
    };
  }, [id]);

  // 2. Fetch Story Details
  const fetchStoryData = async () => {
    setLoading(true);
    try {
      if (!navigator.onLine) {
        const cached = localStorage.getItem(`heimdall_story_cache_${id}`);
        if (cached) {
          const parsed = JSON.parse(cached);
          setStory(parsed.story);
          setBookmarked(parsed.bookmarked);
        } else {
          setStory(null);
        }
        setLoading(false);
        return;
      }

      const data = await storyService.getStoryDetails(id);
      setStory(data);

      const bookmarks = await bookmarkService.listBookmarks();
      const isSaved = bookmarks.some(b => b.story_id === id);
      setBookmarked(isSaved);

      saveStoryToOfflineCache(id, data, isSaved);
    } catch (err) {
      showNotification(err.message || 'Failed to fetch story details.', 'error');
      const cached = localStorage.getItem(`heimdall_story_cache_${id}`);
      if (cached) {
        const parsed = JSON.parse(cached);
        setStory(parsed.story);
        setBookmarked(parsed.bookmarked);
      }
    } finally {
      setLoading(false);
    }
  };

  const saveStoryToOfflineCache = (storyId, storyData, isSaved) => {
    const cacheKeysStr = localStorage.getItem('heimdall_story_cache_keys') || '[]';
    let cacheKeys = JSON.parse(cacheKeysStr);

    cacheKeys = cacheKeys.filter(k => k !== storyId);
    cacheKeys.unshift(storyId);

    if (cacheKeys.length > 20) {
      const evictedId = cacheKeys.pop();
      localStorage.removeItem(`heimdall_story_cache_${evictedId}`);
    }

    localStorage.setItem('heimdall_story_cache_keys', JSON.stringify(cacheKeys));
    localStorage.setItem(`heimdall_story_cache_${storyId}`, JSON.stringify({
      story: storyData,
      bookmarked: isSaved,
      timestamp: Date.now()
    }));
  };

  useEffect(() => {
    if (id) {
      fetchStoryData();
    }
  }, [id]);

  const handleToggleBookmark = async () => {
    try {
      if (bookmarked) {
        await bookmarkService.removeBookmark(id);
        setBookmarked(false);
        showNotification('Story removed from bookmarks.', 'info');
      } else {
        await bookmarkService.addBookmark(id);
        setBookmarked(true);
        showNotification('Story saved to bookmarks.', 'success');
      }
    } catch (err) {
      showNotification(err.message || 'Bookmark action failed.', 'error');
    }
  };

  if (loading) {
    return <LoadingSkeleton type="page" />;
  }

  if (!story) {
    return (
      <div className="story-error-state animate-slide-up">
        <h3>Story Brief Unavailable</h3>
        <p>This story briefing is not cached or is currently inaccessible offline.</p>
        <Link to="/dashboard" className="back-link">Return to Feed</Link>
      </div>
    );
  }

  const getStoryImage = () => {
    for (let art of story.articles || []) {
      if (art.image_url) return art.image_url;
    }
    return null;
  };

  const coverImage = getStoryImage();

  // Parse AI Summary into distinct headers
  const summarySections = {};
  if (story.ai_summary) {
    story.ai_summary.split('## ').forEach(section => {
      const lines = section.split('\n');
      const header = lines[0].trim();
      const body = lines.slice(1).join('\n').trim();
      if (header) {
        summarySections[header] = body;
      }
    });
  }

  const mainArticle = story.articles && story.articles.length > 0 ? story.articles[0] : null;

  // Helper to render body with list detection
  const renderSectionBody = (bodyText) => {
    if (bodyText.startsWith('-')) {
      return (
        <ul>
          {bodyText.split('\n').map((li, lidx) => (
            <li key={lidx}>{li.replace(/^-\s+/, '')}</li>
          ))}
        </ul>
      );
    }
    return <p>{bodyText}</p>;
  };

  // Determine user friendly verification tag
  const getVerificationLabel = () => {
    if (story.has_conflicts) {
      return { text: 'Conflicting Details Reported', color: 'status-disputed', icon: '⚠' };
    }
    if (story.publisher_diversity >= 3) {
      return { text: 'Verified by Multiple Sources', color: 'status-verified', icon: '✓' };
    }
    return { text: 'Single Source Report', color: 'status-single', icon: '●' };
  };

  const verificationBadge = getVerificationLabel();

  return (
    <div className="story-page-container">
      {/* Sticky Progress Bar */}
      <div className="reading-progress-bar" style={{ width: `${scrollProgress}%` }}></div>

      {/* Back Navigation Bar */}
      <div className="story-nav-header">
        <Link to="/" className="back-arrow-btn">
          &larr; Back to Feed
        </Link>
        <button
          className={`bookmark-toggle-btn ${bookmarked ? 'active' : ''}`}
          onClick={handleToggleBookmark}
          aria-label="Toggle Bookmark"
        >
          <svg viewBox="0 0 24 24" width="20" height="20" fill={bookmarked ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
          </svg>
        </button>
      </div>

      {/* Cover Image */}
      {coverImage && (
        <div className="story-cover-image-container">
          <img src={coverImage} alt="" className="story-cover-image" />
        </div>
      )}

      {/* 1. Headline Area */}
      <header className="story-headline-header">
        <div className="headline-meta-row">
          <span className="story-category-tag">{story.predicted_category}</span>
          <span className={`story-verification-badge ${verificationBadge.color}`}>
            {verificationBadge.icon} {verificationBadge.text}
          </span>
        </div>
        <h1 className="story-main-title">{story.title}</h1>
      </header>

      {/* Quick Facts Panel */}
      <section className="quick-facts-panel">
        <div className="fact-item">
          <span className="fact-label">Published</span>
          <span className="fact-value">{new Date(story.last_updated_at).toLocaleDateString()}</span>
        </div>
        <div className="fact-item">
          <span className="fact-label">Sources</span>
          <span className="fact-value">{story.publisher_diversity} publications</span>
        </div>
        <div className="fact-item">
          <span className="fact-label">Reading Time</span>
          <span className="fact-value">~4 min read</span>
        </div>
        <div className="fact-item">
          <span className="fact-label">Region Context</span>
          <span className="fact-value">{story.region_tags?.join(', ') || 'Global'}</span>
        </div>
      </section>

      {/* 2. AI Summary Card (Briefing Summary) */}
      {story.ai_summary && (
        <section className="ai-briefing-summary-card">
          <h3 className="section-title-premium">Intelligence Briefing</h3>
          <div className="ai-briefing-body">
            {Object.keys(summarySections).map((key) => {
              if (key === 'Key Takeaways') return null; // Key Takeaways rendered separately below
              return (
                <div key={key} className="briefing-block">
                  <h4 className="briefing-block-title">{key}</h4>
                  <div className="briefing-block-text">
                    {renderSectionBody(summarySections[key])}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* 3. Full News Content */}
      <section className="story-full-news-content">
        <h3 className="section-title-premium">Full News Coverage</h3>
        <article className="premium-article-body">
          {mainArticle ? (
            <>
              <div className="article-byline-premium">
                <span className="byline-source">Published by <strong>{mainArticle.publisher_name}</strong></span>
                {mainArticle.author && <span className="byline-author"> | By {mainArticle.author}</span>}
              </div>
              <div className="article-text-paragraphs">
                {mainArticle.body_text ? (
                  mainArticle.body_text.split('\n\n').map((paragraph, pIdx) => (
                    <p key={pIdx}>{paragraph}</p>
                  ))
                ) : (
                  <p>{story.summary}</p>
                )}
              </div>
            </>
          ) : (
            <p className="no-article-text">{story.summary}</p>
          )}
        </article>
      </section>

      {/* 4. Key Takeaways Section */}
      {summarySections['Key Takeaways'] && (
        <section className="key-takeaways-highlight-card">
          <h3 className="takeaways-title">Key Takeaways</h3>
          <div className="takeaways-body-list">
            {renderSectionBody(summarySections['Key Takeaways'])}
          </div>
        </section>
      )}

      {/* 5. Chronology Timeline (Compressed Card) */}
      {story.timelines && story.timelines.length > 0 && (
        <section className="timeline-section-card-compressed">
          <h3 className="section-title-premium">Story Chronology</h3>
          <div className="timeline-compressed-wrapper">
            <Timeline milestones={story.timelines} />
          </div>
        </section>
      )}

      {/* 6. Collapsible Contributing Publications (Sources) */}
      <section className="collapsible-sources-section">
        <button
          className="collapsible-sources-toggle"
          onClick={() => setSourcesCollapsed(!sourcesCollapsed)}
          aria-expanded={!sourcesCollapsed}
        >
          <span>Sources & Contributing Outlets ({story.articles?.length || 0})</span>
          <span className="toggle-chevron-icon">{sourcesCollapsed ? '▼' : '▲'}</span>
        </button>

        {!sourcesCollapsed && (
          <div className="sources-list-stack-expanded animate-fade-in">
            {story.articles?.map((art) => (
              <div key={art.id} className="source-article-row-item">
                <div className="source-row-top">
                  <span className="source-pub-title">{art.publisher_name}</span>
                  <span className="source-trust-score">Trust: {Math.round(art.credibility_score * 100)}%</span>
                </div>
                <a
                  href={art.canonical_url || art.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="source-headline-link"
                >
                  {art.title}
                </a>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 7. Related Stories */}
      {story.related_stories && story.related_stories.length > 0 && (
        <section className="related-stories-section-compact">
          <h3 className="section-title-premium">Related Briefings</h3>
          <div className="related-stories-compact-grid">
            {story.related_stories.map((rel) => (
              <div
                key={rel.id}
                className="related-story-compact-card"
                onClick={() => navigate(`/story/${rel.id}`)}
              >
                <span className="related-compact-category">{rel.predicted_category}</span>
                <h4 className="related-compact-title">{rel.title}</h4>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};

export default StoryPage;
