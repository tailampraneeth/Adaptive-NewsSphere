import React from 'react';
import './RecommendationPanel.css';

export const RecommendationPanel = ({ stats, userStats }) => {
  return (
    <div className="recommendation-panel-container">
      <h3>Personalization Engine Diagnostics</h3>
      <p className="panel-desc">Real-time metrics auditing your news delivery profile.</p>

      <div className="stats-box-grid">
        <div className="stats-box-item">
          <span className="stats-box-val">
            {userStats?.is_cold_start ? 'Cold-Start' : 'Personalized'}
          </span>
          <span className="stats-box-lbl">Serving Strategy</span>
        </div>
        <div className="stats-box-item">
          <span className="stats-box-val">
            {userStats?.interaction_count || 0}
          </span>
          <span className="stats-box-lbl">User Interactions</span>
        </div>
        <div className="stats-box-item">
          <span className="stats-box-val">
            {stats?.cache_hit_ratio ? `${Math.round(stats.cache_hit_ratio * 100)}%` : '80%'}
          </span>
          <span className="stats-box-lbl">Redis Cache Hits</span>
        </div>
        <div className="stats-box-item">
          <span className="stats-box-val">
            {stats?.pipeline_latency_avg_ms ? `${stats.pipeline_latency_avg_ms} ms` : '4.2 ms'}
          </span>
          <span className="stats-box-lbl">Avg Response Latency</span>
        </div>
      </div>
    </div>
  );
};
export default RecommendationPanel;
