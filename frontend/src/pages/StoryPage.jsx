import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import useNotification from '../hooks/useNotification';
import storyService from '../services/storyService';
import feedService from '../services/feedService';
import analyticsService from '../services/analyticsService';
import SummaryCards from '../components/SummaryCards';
import Timeline from '../components/Timeline';
import VerificationPanel from '../components/VerificationPanel';
import EvidencePanel from '../components/EvidencePanel';
import ChatDrawer from '../components/ChatDrawer';
import LoadingSkeleton from '../components/LoadingSkeleton';
import './StoryPage.css';

export const StoryPage = () => {
  const { id } = useParams();
  const { user } = useAuth();
  const { showNotification } = useNotification();

  const [story, setStory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activePanel, setActivePanel] = useState('summary');
  const [drawerOpen, setDrawerOpen] = useState(false);

  // 1. Dwell interaction tracker
  useEffect(() => {
    const tStart = Date.now();
    analyticsService.recordStoryOpen(id);

    return () => {
      const dwellSeconds = Math.round((Date.now() - tStart) / 1000);
      if (user && id && dwellSeconds > 0) {
        feedService.recordInteraction(user.id, id, 'dwell', dwellSeconds).catch(() => {});
      }
    };
  }, [id, user]);

  // 2. Fetch story details
  useEffect(() => {
    const fetchStory = async () => {
      setLoading(true);
      try {
        const data = await storyService.getStoryDetails(id);
        setStory(data);
      } catch (err) {
        showNotification(err.message || 'Error loading story details.', 'error');
      } finally {
        setLoading(false);
      }
    };

    fetchStory();
  }, [id, showNotification]);

  const recordAction = async (type) => {
    if (!user || !id) return;
    try {
      await feedService.recordInteraction(user.id, id, type);
    } catch (_) {}
  };

  if (loading) {
    return <LoadingSkeleton type="page" />;
  }

  if (!story) {
    return (
      <div className="story-error-state animate-slide-up">
        <h3>Story Cluster Unavailable</h3>
        <p>This story may have been archived or merged into another timeline.</p>
        <Link to="/dashboard" className="back-link">Return to Dashboard</Link>
      </div>
    );
  }

  const getScoreClass = (score) => {
    if (score >= 0.70) return 'score-high';
    if (score >= 0.45) return 'score-medium';
    return 'score-low';
  };

  return (
    <div className="story-detail-page">
      <header className="story-detail-header animate-slide-up">
        <Link to="/dashboard" className="back-to-dash-btn">
          &larr; Back to Feed
        </Link>
        
        <div className="story-title-row">
          <h1>{story.title}</h1>
        </div>

        <div className="story-badges-row">
          {story.verification_score !== undefined && (
            <div className={`meta-badge-box ${getScoreClass(story.verification_score)}`}>
              <span className="box-lbl">Factual Verification</span>
              <span className="box-val">{Math.round(story.verification_score * 100)}%</span>
            </div>
          )}
          {story.credibility_score !== undefined && (
            <div className={`meta-badge-box ${getScoreClass(story.credibility_score)}`}>
              <span className="box-lbl">Source Trust Score</span>
              <span className="box-val">{Math.round(story.credibility_score * 100)}%</span>
            </div>
          )}
          <div className="meta-badge-box">
            <span className="box-lbl">Factual Consensus</span>
            <span className="box-val">{story.has_conflicts ? 'Disputed' : 'Consensus'}</span>
          </div>
        </div>
      </header>

      <div className="story-page-body-grid animate-slide-up">
        <div className="story-left-column">
          {/* Tabs bar */}
          <nav className="story-detail-tabs" aria-label="Story Detail Sections">
            <button 
              className={`story-tab-link ${activePanel === 'summary' ? 'active' : ''}`}
              onClick={() => setActivePanel('summary')}
            >
              AI Summaries
            </button>
            <button 
              className={`story-tab-link ${activePanel === 'timeline' ? 'active' : ''}`}
              onClick={() => setActivePanel('timeline')}
            >
              Timeline
            </button>
            <button 
              className={`story-tab-link ${activePanel === 'verification' ? 'active' : ''}`}
              onClick={() => setActivePanel('verification')}
            >
              Claims Audit
            </button>
            <button 
              className={`story-tab-link ${activePanel === 'evidence' ? 'active' : ''}`}
              onClick={() => setActivePanel('evidence')}
            >
              Evidence Trail
            </button>
          </nav>

          {/* Panel details */}
          <div className="story-panel-display-content">
            {activePanel === 'summary' && (
              <SummaryCards
                summaryQuick={story.summary_quick}
                summaryBeginner={story.summary_beginner}
                summaryProfessional={story.summary_professional}
                defaultSummary={story.summary}
              />
            )}
            {activePanel === 'timeline' && (
              <Timeline milestones={story.timelines} />
            )}
            {activePanel === 'verification' && (
              <VerificationPanel
                verificationScore={story.verification_score}
                hasConflicts={story.has_conflicts}
                evidence={story.evidence}
                metadata={story.verification_metadata}
              />
            )}
            {activePanel === 'evidence' && (
              <EvidencePanel evidence={story.evidence} />
            )}
          </div>
        </div>

        <div className="story-right-column">
          {/* Ask Assistant trigger */}
          <section className="assistant-cta-card">
            <h3>Verify with Grounded AI</h3>
            <p>Converse with our RAG agent to verify specifics of this cluster without hallucinations.</p>
            <button 
              className="launch-assistant-btn"
              onClick={() => {
                setDrawerOpen(true);
                recordAction('chat_open');
              }}
            >
              Launch Chat Assistant
            </button>
          </section>

          {/* Source Articles list */}
          <section className="story-sources-card">
            <h3>Contributing Publications ({story.articles?.length || 0})</h3>
            <div className="sources-list-stack">
              {story.articles?.map((art) => (
                <div key={art.id} className="source-list-item">
                  <div className="source-info">
                    <span className="source-publisher-title">{art.publisher_name}</span>
                    {art.source_url ? (
                      <a 
                        href={art.source_url} 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        className="source-headline-link"
                        onClick={() => recordAction('share')}
                      >
                        {art.title}
                      </a>
                    ) : (
                      <span className="source-headline-static">{art.title}</span>
                    )}
                  </div>
                  <div className="source-credibility-rating" title="Publisher Credibility Index">
                    {Math.round(art.credibility_score * 100)}%
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Related Stories */}
          {story.related_stories?.length > 0 && (
            <section className="story-sources-card">
              <h3>Related Story Clusters</h3>
              <div className="related-stories-links-stack">
                {story.related_stories.map((rel) => (
                  <Link 
                    key={rel.id} 
                    to={`/story/${rel.id}`} 
                    className="related-story-link-row"
                    onClick={() => recordAction('click_related')}
                  >
                    <span className="related-title">{rel.title}</span>
                    <span className="related-trend">Trend: {Math.round(rel.trending_score * 100)}%</span>
                  </Link>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>

      <ChatDrawer
        storyId={id}
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  );
};
export default StoryPage;
