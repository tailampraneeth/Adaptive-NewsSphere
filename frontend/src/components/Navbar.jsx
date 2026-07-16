import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import useNotification from '../hooks/useNotification';
import './Navbar.css';

export const Navbar = ({ onToggleSidebar }) => {
  const { user, logout } = useAuth();
  const { showNotification } = useNotification();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    showNotification('Logged out successfully.', 'info');
    navigate('/login');
  };

  return (
    <header className="navbar-container">
      <div className="navbar-left">
        <button
          className="sidebar-toggle-btn"
          onClick={onToggleSidebar}
          aria-label="Toggle Navigation Sidebar"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
            <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
          </svg>
        </button>
        <Link to="/dashboard" className="navbar-logo">
          <div className="logo-dot"></div>
          <span className="logo-text">NewsSphere</span>
        </Link>
      </div>

      <div className="navbar-right">
        {user && (
          <div className="user-profile-summary">
            <div className="user-avatar">
              {user.email.charAt(0).toUpperCase()}
            </div>
            <span className="user-email-display">{user.email}</span>
          </div>
        )}
        <button
          className="logout-btn"
          onClick={handleLogout}
          aria-label="Sign Out Session"
        >
          Sign Out
        </button>
      </div>
    </header>
  );
};
export default Navbar;
