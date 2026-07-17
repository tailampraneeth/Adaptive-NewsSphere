import React, { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import authService from '../services/authService';
import useNotification from '../hooks/useNotification';
import './AuthPage.css';

export const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const { showNotification } = useNotification();
  const navigate = useNavigate();

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!token) {
      showNotification('Missing or invalid password reset token.', 'error');
      return;
    }

    if (!password || !confirmPassword) {
      showNotification('Please fill in all password fields.', 'warning');
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
      await authService.resetPassword(token, password);
      setSuccess(true);
      showNotification('Password reset successfully! Redirecting...', 'success');
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (err) {
      showNotification(err.message || 'Password reset failed. Token may be invalid or expired.', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-form-card animate-slide-up">
      <h2>Change Password</h2>

      {!token ? (
        <div style={{ textAlign: 'center', padding: '10px 0' }}>
          <p className="auth-subtitle" style={{ color: 'var(--error)', fontWeight: '600', marginBottom: '16px' }}>
            ⚠ Invalid Link
          </p>
          <p className="auth-subtitle" style={{ fontSize: '14px', lineHeight: '1.6', marginBottom: '24px' }}>
            The password reset link is invalid or missing a security token. Please request a new link.
          </p>
          <Link to="/forgot-password" className="auth-submit-btn" style={{ textDecoration: 'none', display: 'block', textAlign: 'center' }}>
            Request New Link
          </Link>
        </div>
      ) : !success ? (
        <>
          <p className="auth-subtitle">
            Create a secure, new password for your Heimdall account.
          </p>
          <form onSubmit={handleSubmit} className="auth-form-body">
            <div className="form-group">
              <label htmlFor="new-password">New Password</label>
              <input
                id="new-password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                aria-label="New Password (Minimum 6 characters)"
              />
            </div>

            <div className="form-group">
              <label htmlFor="confirm-password">Confirm Password</label>
              <input
                id="confirm-password"
                type="password"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                aria-label="Confirm Password"
              />
            </div>

            <button type="submit" className="auth-submit-btn" disabled={loading}>
              {loading ? 'Updating Password...' : 'Save New Password'}
            </button>
          </form>
        </>
      ) : (
        <div style={{ textAlign: 'center', padding: '10px 0' }}>
          <p className="auth-subtitle" style={{ color: 'var(--success)', fontWeight: '600', marginBottom: '16px' }}>
            ✓ Credentials Updated
          </p>
          <p className="auth-subtitle" style={{ fontSize: '14px', lineHeight: '1.6', marginBottom: '24px' }}>
            Your password has been successfully updated. Redirecting you to the login screen...
          </p>
          <Link to="/login" className="auth-submit-btn" style={{ textDecoration: 'none', display: 'block', textAlign: 'center' }}>
            Back to Sign In
          </Link>
        </div>
      )}
    </div>
  );
};

export default ResetPassword;
