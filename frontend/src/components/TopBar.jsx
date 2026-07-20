import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import './TopBar.css';

export const TopBar = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="topbar-container">
      <div className="topbar-left">
        <Link to="/" className="topbar-logo">
          <img
            src="/logo.jpg"
            alt="Heimdall Logo"
            className="heimdall-logo-small-img"
            style={{ width: '28px', height: '28px', borderRadius: '50%', marginRight: '8px', border: '1px solid var(--primary)' }}
          />
          <span className="logo-title">Heimdall</span>
        </Link>
      </div>

      <div className="topbar-right">
        {/* Search Icon Shortcut */}
        <button
          className="topbar-icon-btn"
          onClick={() => navigate('/search')}
          aria-label="Open Search Interface"
        >
          <svg
            viewBox="0 0 24 24"
            width="22"
            height="22"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </button>

        {/* User avatar shortcut linking to settings */}
        {user && (
          <Link to="/settings" className="topbar-avatar-link" aria-label="View Account Settings">
            <div className="topbar-avatar">
              {user.name ? user.name.charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()}
            </div>
          </Link>
        )}
      </div>
    </header>
  );
};
export default TopBar;
