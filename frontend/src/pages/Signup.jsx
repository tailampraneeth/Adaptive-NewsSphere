import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import useNotification from '../hooks/useNotification';
import './AuthPage.css';

export const Signup = () => {
  const { signup, login } = useAuth();
  const { showNotification } = useNotification();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password || !confirmPassword) {
      showNotification('Please fill in all registration fields.', 'warning');
      return;
    }

    if (password !== confirmPassword) {
      showNotification('Passwords do not match.', 'warning');
      return;
    }

    if (password.length < 6) {
      showNotification('Password must be at least 6 characters long.', 'warning');
      return;
    }

    setLoading(true);
    try {
      await signup(email, password);
      showNotification('Registration successful! Logging in automatically...', 'success');
      
      // Auto login user
      await login(email, password);
      navigate('/dashboard');
    } catch (err) {
      showNotification(err.message || 'Registration failed. Try again.', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-form-card animate-slide-up">
      <h2>Create Account</h2>
      <p className="auth-subtitle">Register to customize your NewsSphere feed</p>

      <form onSubmit={handleSubmit} className="auth-form-body">
        <div className="form-group">
          <label htmlFor="signup-email">Email Address</label>
          <input
            id="signup-email"
            type="email"
            placeholder="name@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            aria-label="Email Address"
          />
        </div>

        <div className="form-group">
          <label htmlFor="signup-password">Password</label>
          <input
            id="signup-password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            aria-label="Password (Minimum 6 characters)"
          />
        </div>

        <div className="form-group">
          <label htmlFor="signup-confirm-password">Confirm Password</label>
          <input
            id="signup-confirm-password"
            type="password"
            placeholder="••••••••"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            aria-label="Confirm Password"
          />
        </div>

        <button type="submit" className="auth-submit-btn" disabled={loading}>
          {loading ? 'Registering...' : 'Create Account'}
        </button>
      </form>

      <div className="auth-switch-link">
        <span>Already have an account? </span>
        <Link to="/login">Sign in here</Link>
      </div>
    </div>
  );
};
export default Signup;
