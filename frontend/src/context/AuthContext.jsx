import React, { createContext, useState, useEffect, useCallback } from 'react';
import authService from '../services/authService';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // Initialize from storage on startup
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = authService.getToken();
      if (storedToken) {
        try {
          const fetchedUser = await authService.getMe();
          setUser(fetchedUser);
          setToken(storedToken);
          localStorage.setItem('user', JSON.stringify(fetchedUser));
        } catch (_) {
          authService.logout();
          setUser(null);
          setToken(null);
        }
      }
      setLoading(false);
    };

    initAuth();

    // Listen for global 401 unauthorized notifications
    const handleUnauthorized = () => {
      setUser(null);
      setToken(null);
    };

    window.addEventListener('auth-unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth-unauthorized', handleUnauthorized);
  }, []);

  const login = useCallback(async (email, password) => {
    setLoading(true);
    try {
      const result = await authService.login(email, password);
      setUser(result.user);
      setToken(result.token);
      return result.user;
    } finally {
      setLoading(false);
    }
  }, []);

  const signup = useCallback(async (email, password) => {
    setLoading(true);
    try {
      const newUser = await authService.signup(email, password);
      return newUser;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
    setToken(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, signup, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
};
export default AuthProvider;
