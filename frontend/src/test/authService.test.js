import { describe, it, expect, vi, beforeEach } from 'vitest';
import authService from '../services/authService';
import * as api from '../services/api';

vi.mock('../services/api', () => ({
  request: vi.fn(),
}));

describe('authService Unit Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('signup should invoke POST request to signup endpoint', async () => {
    const mockUser = { id: '123', email: 'test@example.com' };
    vi.mocked(api.request).mockResolvedValueOnce(mockUser);

    const result = await authService.signup('test@example.com', 'pwd123');

    expect(api.request).toHaveBeenCalledWith('/api/v1/auth/signup', {
      method: 'POST',
      body: { email: 'test@example.com', password: 'pwd123' },
    });
    expect(result).toEqual(mockUser);
  });

  it('login should store JWT and fetch profile info on success', async () => {
    const mockTokenRes = { access_token: 'mock-jwt-token', token_type: 'bearer' };
    const mockUser = { id: '123', email: 'test@example.com' };

    // Mock login endpoint first, then me profile endpoint
    vi.mocked(api.request)
      .mockResolvedValueOnce(mockTokenRes)
      .mockResolvedValueOnce(mockUser);

    const result = await authService.login('test@example.com', 'pwd123');

    expect(api.request).toHaveBeenNthCalledWith(1, '/api/v1/auth/login', {
      method: 'POST',
      body: { email: 'test@example.com', password: 'pwd123' },
    });
    expect(api.request).toHaveBeenNthCalledWith(2, '/api/v1/auth/me', {
      method: 'GET',
    });

    expect(localStorage.getItem('token')).toBe('mock-jwt-token');
    expect(JSON.parse(localStorage.getItem('user'))).toEqual(mockUser);
    expect(result.user).toEqual(mockUser);
    expect(result.token).toBe('mock-jwt-token');
  });

  it('logout should purge JWT and user session profile from storage', () => {
    localStorage.setItem('token', 'jwt-to-clear');
    localStorage.setItem('user', JSON.stringify({ email: 'user@test.com' }));

    authService.logout();

    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
    expect(authService.isAuthenticated()).toBe(false);
  });
});
