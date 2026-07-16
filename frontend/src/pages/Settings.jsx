import React, { useState, useEffect } from 'react';
import useTheme from '../hooks/useTheme';
import useNotification from '../hooks/useNotification';
import analyticsService from '../services/analyticsService';
import ThemeSwitcher from '../components/ThemeSwitcher';
import './Settings.css';

export const Settings = () => {
  const { theme } = useTheme();
  const { showNotification } = useNotification();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    setStats(analyticsService.getStats());
  }, []);

  const handleClearHistory = () => {
    localStorage.removeItem('ans_local_analytics');
    setStats(analyticsService.getStats());
    showNotification('Local browsing metrics and profile preferences successfully purged.', 'success');
  };

  const formatDuration = (sec) => {
    if (!sec) return '0s';
    const hrs = Math.floor(sec / 3600);
    const mins = Math.floor((sec % 3600) / 60);
    const secs = sec % 60;
    
    let result = '';
    if (hrs > 0) result += `${hrs}h `;
    if (mins > 0) result += `${mins}m `;
    result += `${secs}s`;
    return result;
  };

  return (
    <div className="settings-container animate-slide-up">
      <header className="settings-header">
        <h1>Preferences & Diagnostics</h1>
        <p>Manage your interface appearance and explore local system telemetry.</p>
      </header>

      <div className="settings-grid">
        {/* Appearance Panel */}
        <section className="settings-card">
          <h2>Interface Appearance</h2>
          <p className="card-desc">Toggle color schemes. Adaptive theme automatically adapts based on system settings.</p>
          <div className="theme-toggle-row">
            <ThemeSwitcher />
          </div>
        </section>

        {/* Local Diagnostics / Analytics */}
        <section className="settings-card diagnostics-card">
          <h2>Local Workspace Telemetry</h2>
          <p className="card-desc">Audit logs tracked entirely inside your local browser storage. No cloud leaks.</p>
          
          {stats && (
            <div className="diagnostics-metrics-grid">
              <div className="metric-box">
                <span className="metric-label">Session Duration</span>
                <span className="metric-value">{formatDuration(stats.totalSessionDurationSeconds)}</span>
              </div>
              <div className="metric-box">
                <span className="metric-label">Login Count</span>
                <span className="metric-value">{stats.loginCount}</span>
              </div>
              <div className="metric-box">
                <span className="metric-label">Story Views</span>
                <span className="metric-value">
                  {Object.values(stats.storyOpens || {}).reduce((a, b) => a + b, 0)}
                </span>
              </div>
              <div className="metric-box">
                <span className="metric-label">LLM Latency (Avg)</span>
                <span className="metric-value">
                  {stats.avgLlmLatencyMs ? `${stats.avgLlmLatencyMs} ms` : 'N/A'}
                </span>
              </div>
            </div>
          )}
        </section>

        {/* Privacy Panel */}
        <section className="settings-card danger-card">
          <h2>Privacy & Data Scrubbing</h2>
          <p className="card-desc">Comply with data privacy rules. Scrub all local telemetry metrics, logs, and preference variables immediately.</p>
          <button className="clear-history-btn" onClick={handleClearHistory}>
            Purge Local Telemetry Data
          </button>
        </section>
      </div>
    </div>
  );
};
export default Settings;
