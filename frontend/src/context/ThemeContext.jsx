import React, { createContext, useState, useEffect } from 'react';

export const ThemeContext = createContext();

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'system';
  });

  const [activeTheme, setActiveTheme] = useState('light');

  useEffect(() => {
    const root = document.documentElement;
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const applyTheme = () => {
      let resolved = 'light';
      if (theme === 'dark') {
        resolved = 'dark';
      } else if (theme === 'light') {
        resolved = 'light';
      } else {
        resolved = mediaQuery.matches ? 'dark' : 'light';
      }
      
      setActiveTheme(resolved);
      root.setAttribute('data-theme', resolved);
    };

    applyTheme();
    localStorage.setItem('theme', theme);

    const listener = () => {
      if (theme === 'system') {
        applyTheme();
      }
    };

    mediaQuery.addEventListener('change', listener);
    return () => mediaQuery.removeEventListener('change', listener);
  }, [theme]);

  const toggleTheme = (newTheme) => {
    if (['light', 'dark', 'system'].includes(newTheme)) {
      setTheme(newTheme);
    }
  };

  return (
    <ThemeContext.Provider value={{ theme, activeTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
