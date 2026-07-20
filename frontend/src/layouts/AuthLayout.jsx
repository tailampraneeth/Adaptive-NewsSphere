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
          <img
            src="/logo.jpg"
            alt="Heimdall Logo"
            className="heimdall-logo-img"
            style={{ width: '80px', height: '80px', borderRadius: '50%', marginBottom: '16px', border: '2px solid var(--primary)' }}
          />
          <h1>Heimdall</h1>
          <p style={{ color: 'var(--text-secondary)', fontWeight: '600', letterSpacing: '0.5px', textTransform: 'uppercase', fontSize: '11px' }}>
            Personalized News App
          </p>
        </header>
        <main className="auth-content">
          <Outlet />
        </main>
        <footer className="auth-footer">
          <p>© 2026 Heimdall Watchtower. Peaceful, verifiable news.</p>
        </footer>
      </div>
    </div>
  );
};
export default AuthLayout;
