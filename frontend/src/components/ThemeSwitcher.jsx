import React from 'react';
import useTheme from '../hooks/useTheme';
import analyticsService from '../services/analyticsService';
import './ThemeSwitcher.css';

export const ThemeSwitcher = () => {
  const { theme, toggleTheme } = useTheme();

  const handleToggle = (mode) => {
    toggleTheme(mode);
    analyticsService.recordThemeUsage(mode);
  };

  return (
    <div className="theme-switcher-container" role="radiogroup" aria-label="Appearance Mode">
      {['light', 'dark', 'system'].map((mode) => (
        <button
          key={mode}
          className={`theme-btn ${theme === mode ? 'active' : ''}`}
          onClick={() => handleToggle(mode)}
          role="radio"
          aria-checked={theme === mode}
          aria-label={`${mode.charAt(0).toUpperCase() + mode.slice(1)} Mode`}
        >
          {mode === 'light' && (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1zM5.99 4.58c-.39-.39-1.03-.39-1.41 0s-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41L5.99 4.58zm12.37 12.37c-.39-.39-1.03-.39-1.41 0s-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41l-1.06-1.06zm1.06-12.37c-.39-.39-1.02-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06c.38-.38.38-1.02 0-1.41zm-12.37 12.37c-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06c.39-.38.39-1.02 0-1.41z"/>
            </svg>
          )}
          {mode === 'dark' && (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M12.3 22c5.02 0 9.1-4.08 9.1-9.1 0-2.3-.85-4.4-2.26-6.02-.34-.39-.93-.24-1.07.25-.48 1.67-1.44 3.12-2.76 4.15-1.28.99-2.88 1.54-4.57 1.54-1.69 0-3.29-.55-4.57-1.54-1.32-1.03-2.28-2.48-2.76-4.15-.14-.49-.73-.64-1.07-.25C1.85 8.5 1 10.6 1 12.9 1 17.92 5.08 22 10.1 22h2.2z"/>
            </svg>
          )}
          {mode === 'system' && (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M20 18c1.1 0 1.99-.9 1.99-2L22 4c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2H0v2h24v-2h-4zM4 4h16v12H4V4z"/>
            </svg>
          )}
          <span className="btn-text">{mode}</span>
        </button>
      ))}
    </div>
  );
};
export default ThemeSwitcher;
