import React from 'react';
import { Outlet } from 'react-router-dom';
import './AuthLayout.css';

export const AuthLayout = () => {
  return (
    <div className="auth-layout-container">
      <div className="auth-background-shapes">
        <div className="shape circle-1"></div>
        <div className="shape circle-2"></div>
      </div>
      <div className="auth-glass-panel">
        <header className="auth-logo-header">
          <div className="logo-badge">ANS</div>
          <h1>NewsSphere</h1>
          <p>AI-Powered News Intelligence Platform</p>
        </header>
        <main className="auth-content">
          <Outlet />
        </main>
        <footer className="auth-footer">
          <p>© 2026 Adaptive NewsSphere. Peaceful, verifiable news.</p>
        </footer>
      </div>
    </div>
  );
};
export default AuthLayout;
