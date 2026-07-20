import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import authService from '../services/authService';
import useNotification from '../hooks/useNotification';
import './AuthPage.css';

export const ForgotPassword = () => {
  const { showNotification } = useNotification();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email) {
      showNotification('Please enter your email address.', 'warning');
      return;
    }

    setLoading(true);
    try {
      await authService.forgotPassword(email);
      setSubmitted(true);
      showNotification('If the email is registered, a password reset link has been sent.', 'success');
    } catch (err) {
      showNotification(err.message || 'Failed to send password reset request.', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-form-card animate-slide-up">
      <h2>Reset Password</h2>
      
      {!submitted ? (
        <>
          <p className="auth-subtitle">
            Enter your email below. We'll send you a secure link to reset your password.
          </p>
          <form onSubmit={handleSubmit} className="auth-form-body">
            <div className="form-group">
              <label htmlFor="reset-email">Email Address</label>
              <input
                id="reset-email"
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                aria-label="Email Address"
              />
            </div>

            <button type="submit" className="auth-submit-btn" disabled={loading}>
              {loading ? 'Sending Link...' : 'Send Reset Link'}
            </button>
          </form>
        </>
      ) : (
        <div style={{ textAlign: 'center', padding: '10px 0' }}>
          <p className="auth-subtitle" style={{ color: 'var(--success)', fontWeight: '600', marginBottom: '24px' }}>
            ✓ Check your inbox
          </p>
          <p className="auth-subtitle" style={{ fontSize: '14px', lineHeight: '1.6', margin: '0 0 24px 0' }}>
            We've sent a secure, single-use password reset link to <strong>{email}</strong>. 
            The link will expire in 30 minutes.
          </p>
          <p className="auth-subtitle" style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Didn't receive the email? Check your spam folder or wait 60 seconds to try again.
          </p>
        </div>
      )}

      <div className="auth-switch-link" style={{ marginTop: '20px' }}>
        <span>Remember your credentials? </span>
        <Link to="/login">Sign in here</Link>
      </div>
    </div>
  );
};

export default ForgotPassword;
