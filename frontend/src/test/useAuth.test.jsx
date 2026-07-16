import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthProvider } from '../context/AuthContext';
import useAuth from '../hooks/useAuth';
import authService from '../services/authService';

vi.mock('../services/authService', () => ({
  default: {
    isAuthenticated: vi.fn(),
    getCurrentUser: vi.fn(),
    getToken: vi.fn(),
    login: vi.fn(),
    signup: vi.fn(),
    logout: vi.fn(),
  }
}));

// Helper component that consumes hook for testing
const HookConsumer = () => {
  const { user, login, logout, isAuthenticated } = useAuth();
  return (
    <div>
      <span data-testid="auth-state">{isAuthenticated ? 'logged-in' : 'anonymous'}</span>
      <span data-testid="user-email">{user?.email || 'none'}</span>
      <button data-testid="login-btn" onClick={() => login('test@test.com', 'pwd')}>Log In</button>
      <button data-testid="logout-btn" onClick={logout}>Log Out</button>
    </div>
  );
};

describe('useAuth Hook Unit Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should initialize with anonymous user if storage is empty', async () => {
    vi.mocked(authService.isAuthenticated).mockReturnValue(false);

    await act(async () => {
      render(
        <AuthProvider>
          <HookConsumer />
        </AuthProvider>
      );
    });

    expect(screen.getByTestId('auth-state').textContent).toBe('anonymous');
    expect(screen.getByTestId('user-email').textContent).toBe('none');
  });

  it('should auto-login from storage on mount if token exists', async () => {
    vi.mocked(authService.isAuthenticated).mockReturnValue(true);
    vi.mocked(authService.getCurrentUser).mockReturnValue({ email: 'auto@test.com' });
    vi.mocked(authService.getToken).mockReturnValue('jwt-123');

    await act(async () => {
      render(
        <AuthProvider>
          <HookConsumer />
        </AuthProvider>
      );
    });

    expect(screen.getByTestId('auth-state').textContent).toBe('logged-in');
    expect(screen.getByTestId('user-email').textContent).toBe('auto@test.com');
  });

  it('should handle login call successfully', async () => {
    vi.mocked(authService.isAuthenticated).mockReturnValue(false);
    vi.mocked(authService.login).mockResolvedValueOnce({ email: 'action@test.com' });

    await act(async () => {
      render(
        <AuthProvider>
          <HookConsumer />
        </AuthProvider>
      );
    });

    await act(async () => {
      screen.getByTestId('login-btn').click();
    });

    expect(authService.login).toHaveBeenCalledWith('test@test.com', 'pwd');
    expect(screen.getByTestId('auth-state').textContent).toBe('logged-in');
    expect(screen.getByTestId('user-email').textContent).toBe('action@test.com');
  });
});
