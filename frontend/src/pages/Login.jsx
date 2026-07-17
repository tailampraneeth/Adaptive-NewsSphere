import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import useNotification from '../hooks/useNotification';
import './AuthPage.css';

export const Login = () => {
  const { login } = useAuth();
  const { showNotification } = useNotification();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      showNotification('Please fill in all credential fields.', 'warning');
      return;
    }

    setLoading(true);
    try {
      const loggedUser = await login(email, password);
      showNotification('Welcome back! Logged in successfully.', 'success');
      
      if (rememberMe) {
        localStorage.setItem('heimdall_remember_email', email);
      } else {
        localStorage.removeItem('heimdall_remember_email');
      }

      if (loggedUser && !loggedUser.onboarding_complete) {
        navigate('/onboard');
      } else {
        navigate('/dashboard');
      }
    } catch (err) {
      showNotification(err.message || 'Login failed. Verify credentials.', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-form-card animate-slide-up">
      <h2>Access Watchtower</h2>
      <p className="auth-subtitle">Real-time, verified world news at your fingertips.</p>
      
      <form onSubmit={handleSubmit} className="auth-form-body">
        <div className="form-group">
          <label htmlFor="login-email">Email Address</label>
          <input
            id="login-email"
            type="email"
            placeholder="name@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            aria-label="Email Address"
          />
        </div>

        <div className="form-group">
          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            aria-label="Password"
          />
        </div>

        <div className="auth-options-row">
          <label className="checkbox-container">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
            />
            <span className="checkbox-label">Remember Me</span>
          </label>
          <Link to="/forgot-password" style={{ color: 'var(--primary)', fontWeight: '600', textDecoration: 'none' }}>
            Forgot Password?
          </Link>
        </div>

        <button type="submit" className="auth-submit-btn" disabled={loading}>
          {loading ? 'Authenticating...' : 'Sign In'}
        </button>
      </form>

      <div className="auth-switch-link">
        <span>Don't have an account? </span>
        <Link to="/signup">Register here</Link>
      </div>
    </div>
  );
};
export default Login;
