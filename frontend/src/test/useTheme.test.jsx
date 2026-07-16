import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { ThemeProvider } from '../context/ThemeContext';
import useTheme from '../hooks/useTheme';

const ThemeConsumer = () => {
  const { theme, toggleTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme-val">{theme}</span>
      <button data-testid="toggle-dark" onClick={() => toggleTheme('dark')}>Go Dark</button>
      <button data-testid="toggle-light" onClick={() => toggleTheme('light')}>Go Light</button>
    </div>
  );
};

describe('useTheme Hook Unit Tests', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should default to system mode on mount', () => {
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme-val').textContent).toBe('system');
  });

  it('should update theme state and store in localStorage on toggle', async () => {
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    await act(async () => {
      screen.getByTestId('toggle-dark').click();
    });

    expect(screen.getByTestId('theme-val').textContent).toBe('dark');
    expect(localStorage.getItem('theme')).toBe('dark');

    await act(async () => {
      screen.getByTestId('toggle-light').click();
    });

    expect(screen.getByTestId('theme-val').textContent).toBe('light');
    expect(localStorage.getItem('theme')).toBe('light');
  });
});
