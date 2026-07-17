import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import useTheme from '../hooks/useTheme';
import useNotification from '../hooks/useNotification';
import authService from '../services/authService';
import publisherService from '../services/publisherService';
import ThemeSwitcher from '../components/ThemeSwitcher';
import './Settings.css';

const CATEGORIES = [
  "Technology", "Business", "Politics", "Science",
  "Health", "Sports", "Entertainment", "Environment", "World"
];

export const Settings = () => {
  const { user, setUser, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { showNotification } = useNotification();
  const navigate = useNavigate();

  const [name, setName] = useState(user?.name || '');
  const [country, setCountry] = useState(user?.country || 'India');
  const [briefTime, setBriefTime] = useState(user?.brief_time || 'morning');
  const [preferredCats, setPreferredCats] = useState(user?.preferred_categories || []);
  const [hiddenCats, setHiddenCats] = useState(user?.hidden_categories || []);
  const [preferredPubs, setPreferredPubs] = useState(user?.preferred_publishers || []);
  const [publishersList, setPublishersList] = useState([]);
  
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const fetchPubs = async () => {
      try {
        const list = await publisherService.listPublishers();
        setPublishersList(list || []);
      } catch (_) {}
    };
    fetchPubs();
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      showNotification('Name cannot be empty.', 'warning');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        name,
        country,
        brief_time: briefTime,
        preferred_categories: preferredCats,
        hidden_categories: hiddenCats,
        preferred_publishers: preferredPubs
      };
      const updatedUser = await authService.updateProfile(payload);
      setUser(updatedUser);
      showNotification('Profile updated successfully!', 'success');
    } catch (err) {
      showNotification(err.message || 'Failed to update profile.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleTogglePrefCategory = (cat) => {
    setPreferredCats(prev =>
      prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]
    );
  };

  const handleToggleHiddenCategory = (cat) => {
    setHiddenCats(prev =>
      prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]
    );
  };

  const handleTogglePublisher = (pubId) => {
    setPreferredPubs(prev =>
      prev.includes(pubId) ? prev.filter(p => p !== pubId) : [...prev, pubId]
    );
  };

  const handleLogout = () => {
    logout();
    showNotification('Logged out successfully.', 'info');
    navigate('/login');
  };

  const handleDeleteAccount = async () => {
    const confirm = window.confirm(
      "Are you absolutely sure you want to delete your Heimdall account? All your bookmarks, reading history, and preferences will be permanently purged."
    );
    if (!confirm) return;

    setDeleting(true);
    try {
      await authService.deleteAccount();
      showNotification('Your account has been deleted.', 'success');
      navigate('/login');
    } catch (err) {
      showNotification(err.message || 'Account deletion failed.', 'error');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="settings-container animate-slide-up">
      <header className="settings-header">
        <h2>Watchtower Settings</h2>
        <p>Customize your intelligence feed constraints and profile parameters.</p>
      </header>

      <form onSubmit={handleSave} className="settings-form">
        {/* Profile Card */}
        <section className="settings-card">
          <h3>Personal Details</h3>
          <div className="form-group">
            <label htmlFor="settings-name">Your Name</label>
            <input
              id="settings-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="settings-country">Country</label>
            <select
              id="settings-country"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
            >
              <option value="India">India</option>
              <option value="United States">United States</option>
              <option value="United Kingdom">United Kingdom</option>
              <option value="Germany">Germany</option>
              <option value="Singapore">Singapore</option>
            </select>
          </div>
        </section>

        {/* Categories preferences */}
        <section className="settings-card">
          <h3>Category Preferences</h3>
          
          <label className="section-subtitle-lbl">Preferred Categories (shown higher)</label>
          <div className="tags-row">
            {CATEGORIES.map(cat => (
              <button
                key={cat}
                type="button"
                className={`tag-toggle-btn ${preferredCats.includes(cat) ? 'selected' : ''}`}
                onClick={() => handleTogglePrefCategory(cat)}
              >
                {cat}
              </button>
            ))}
          </div>

          <label className="section-subtitle-lbl" style={{ marginTop: '16px', display: 'block' }}>
            Hidden Categories (completely filtered)
          </label>
          <div className="tags-row">
            {CATEGORIES.map(cat => (
              <button
                key={cat}
                type="button"
                className={`tag-toggle-btn danger ${hiddenCats.includes(cat) ? 'selected' : ''}`}
                onClick={() => handleToggleHiddenCategory(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
        </section>

        {/* Daily brief and publishers */}
        <section className="settings-card">
          <h3>Briefing & Publishers</h3>
          
          <div className="form-group">
            <label htmlFor="settings-brief">Daily Briefing Time</label>
            <select
              id="settings-brief"
              value={briefTime}
              onChange={(e) => setBriefTime(e.target.value)}
            >
              <option value="morning">Morning (06:00 - 12:00)</option>
              <option value="afternoon">Afternoon (12:00 - 18:00)</option>
              <option value="evening">Evening (18:00 - Midnight)</option>
            </select>
          </div>

          <label className="section-subtitle-lbl">Preferred Publishers</label>
          <div className="tags-row">
            {publishersList.map(pub => (
              <button
                key={pub.id}
                type="button"
                className={`tag-toggle-btn ${preferredPubs.includes(pub.id) ? 'selected' : ''}`}
                onClick={() => handleTogglePublisher(pub.id)}
              >
                {pub.name}
              </button>
            ))}
          </div>
        </section>

        {/* Appearance */}
        <section className="settings-card">
          <h3>System Settings</h3>
          <div className="theme-switcher-row">
            <span className="theme-label">Interface Theme:</span>
            <ThemeSwitcher />
          </div>
        </section>

        <div className="settings-submit-actions">
          <button type="submit" className="save-btn" disabled={loading}>
            {loading ? 'Saving Preferences...' : 'Save Watchtower Settings'}
          </button>
        </div>
      </form>

      {/* Danger Zone */}
      <section className="settings-card danger-card" style={{ marginTop: '24px' }}>
        <h3>Account Options</h3>
        <p className="danger-desc">Log out or permanently delete your watchlist data.</p>
        <div className="danger-actions-row">
          <button type="button" className="logout-action-btn" onClick={handleLogout}>
            Log Out Session
          </button>
          <button type="button" className="delete-account-btn" onClick={handleDeleteAccount} disabled={deleting}>
            {deleting ? 'Deleting account...' : 'Delete Account'}
          </button>
        </div>
      </section>
    </div>
  );
};
export default Settings;
