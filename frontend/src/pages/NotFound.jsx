import React from 'react';
import { Link } from 'react-router-dom';
import './NotFound.css';

export const NotFound = () => {
  return (
    <div className="not-found-container animate-slide-up">
      <div className="not-found-card">
        <h1 className="error-code">404</h1>
        <h2>Event Horizon Reached</h2>
        <p>The page you are looking for has been merged or does not exist in our story clusters.</p>
        <Link to="/dashboard" className="home-btn">
          Return to Dashboard
        </Link>
      </div>
    </div>
  );
};
export default NotFound;
