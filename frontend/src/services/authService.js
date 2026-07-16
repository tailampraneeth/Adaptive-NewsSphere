import { request } from './api';

export const authService = {
  async signup(email, password) {
    const data = await request('/api/v1/auth/signup', {
      method: 'POST',
      body: { email, password },
    });
    return data;
  },

  async login(email, password) {
    const response = await request('/api/v1/auth/login', {
      method: 'POST',
      body: { email, password },
    });
    
    if (response && response.access_token) {
      localStorage.setItem('token', response.access_token);
      
      // Fetch user profile info
      const user = await this.getMe();
      localStorage.setItem('user', JSON.stringify(user));
      return { user, token: response.access_token };
    }
    
    throw new Error('Authentication failed: missing access token.');
  },

  logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  },

  async getMe() {
    const user = await request('/api/v1/auth/me', {
      method: 'GET',
    });
    return user;
  },

  getCurrentUser() {
    const userStr = localStorage.getItem('user');
    if (!userStr) return null;
    try {
      return JSON.parse(userStr);
    } catch (_) {
      return null;
    }
  },

  getToken() {
    return localStorage.getItem('token');
  },

  isAuthenticated() {
    return !!localStorage.getItem('token');
  }
};
export default authService;
