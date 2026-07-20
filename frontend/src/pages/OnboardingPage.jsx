import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import useNotification from '../hooks/useNotification';
import authService from '../services/authService';
import './OnboardingPage.css';

const CATEGORIES = [
  "Technology", "Business", "Politics", "Science",
  "Health", "Sports", "Entertainment", "Environment", "World"
];

const PUBLISHERS = [
  { id: "reuters", name: "Reuters" },
  { id: "ap", name: "AP News" },
  { id: "bbc", name: "BBC News" },
  { id: "guardian", name: "The Guardian" },
  { id: "verge", name: "The Verge" },
  { id: "techcrunch", name: "TechCrunch" }
];

export const OnboardingPage = () => {
  const { user, setUser } = useAuth();
  const { showNotification } = useNotification();
  const navigate = useNavigate();

  const [step, setStep] = useState(1);
  const [name, setName] = useState('');
  const [country, setCountry] = useState('India');
  const [preferredCategories, setPreferredCategories] = useState([]);
  const [preferredPublishers, setPreferredPublishers] = useState([]);
  const [theme, setTheme] = useState('dark');
  const [briefTime, setBriefTime] = useState('morning');
  const [loading, setLoading] = useState(false);

  const toggleCategory = (cat) => {
    setPreferredCategories(prev =>
      prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]
    );
  };

  const togglePublisher = (pubId) => {
    setPreferredPublishers(prev =>
      prev.includes(pubId) ? prev.filter(p => p !== pubId) : [...prev, pubId]
    );
  };

  const handleNext = () => {
    if (step === 1 && !name.strip()) {
      showNotification('Please enter your name.', 'warning');
      return;
    }
    setStep(prev => prev + 1);
  };

  const handleBack = () => {
    setStep(prev => prev - 1);
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const payload = {
        name,
        country,
        preferred_categories: preferredCategories,
        preferred_publishers: preferredPublishers,
        theme,
        brief_time: briefTime
      };
      const updatedUser = await authService.onboard(payload);
      setUser(updatedUser);
      showNotification('Onboarding complete! Welcome to Heimdall.', 'success');
      navigate('/dashboard');
    } catch (err) {
      showNotification(err.message || 'Onboarding failed. Please try again.', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="onboard-container">
      <div className="onboard-card animate-slide-up">
        {/* Progress indicator */}
        <div className="onboard-progress">
          <div className={`progress-dot ${step >= 1 ? 'active' : ''}`}>1</div>
          <div className="progress-line"></div>
          <div className={`progress-dot ${step >= 2 ? 'active' : ''}`}>2</div>
          <div className="progress-line"></div>
          <div className={`progress-dot ${step >= 3 ? 'active' : ''}`}>3</div>
        </div>

        {step === 1 && (
          <div className="onboard-step">
            <h2>Welcome to Heimdall</h2>
            <p className="step-subtitle">Let's configure your watchful guardian dashboard</p>
            
            <div className="form-group">
              <label htmlFor="onboard-name">Your Name</label>
              <input
                id="onboard-name"
                type="text"
                placeholder="Heimdall Guardian"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="onboard-country">Your Country</label>
              <select
                id="onboard-country"
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

            <div className="step-actions">
              <button className="primary-btn" onClick={handleNext}>Next Step</button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="onboard-step">
            <h2>Pick interests</h2>
            <p className="step-subtitle">Heimdall tailors feed categories based on your tags</p>

            <div className="categories-grid">
              {CATEGORIES.map(cat => (
                <button
                  key={cat}
                  className={`category-tag-btn ${preferredCategories.includes(cat) ? 'selected' : ''}`}
                  onClick={() => toggleCategory(cat)}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div className="step-actions">
              <button className="secondary-btn" onClick={handleBack}>Back</button>
              <button className="primary-btn" onClick={handleNext}>Next Step</button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="onboard-step">
            <h2>Your Appearance</h2>
            <p className="step-subtitle">Configure theme, publishers, and daily briefing time</p>

            <div className="form-group">
              <label>Reading Experience</label>
              <div className="theme-toggle-row">
                <button
                  className={`theme-option ${theme === 'dark' ? 'active' : ''}`}
                  onClick={() => setTheme('dark')}
                >
                  Dark Mode
                </button>
                <button
                  className={`theme-option ${theme === 'light' ? 'active' : ''}`}
                  onClick={() => setTheme('light')}
                >
                  Light Mode
                </button>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="onboard-brief">Preferred Daily Briefing Time</label>
              <select
                id="onboard-brief"
                value={briefTime}
                onChange={(e) => setBriefTime(e.target.value)}
              >
                <option value="morning">Morning (06:00 - 12:00)</option>
                <option value="afternoon">Afternoon (12:00 - 18:00)</option>
                <option value="evening">Evening (18:00 - Midnight)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Favorite Publishers (Optional)</label>
              <div className="publishers-row">
                {PUBLISHERS.map(pub => (
                  <button
                    key={pub.id}
                    className={`publisher-tag ${preferredPublishers.includes(pub.id) ? 'selected' : ''}`}
                    onClick={() => togglePublisher(pub.id)}
                  >
                    {pub.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="step-actions">
              <button className="secondary-btn" onClick={handleBack}>Back</button>
              <button className="primary-btn" onClick={handleSubmit} disabled={loading}>
                {loading ? 'Completing Setup...' : 'Enter Heimdall'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
export default OnboardingPage;
