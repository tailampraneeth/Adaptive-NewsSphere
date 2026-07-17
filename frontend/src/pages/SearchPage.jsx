import React, { useState, useEffect } from 'react';
import searchService from '../services/searchService';
import publisherService from '../services/publisherService';
import StoryCard from '../components/StoryCard';
import LoadingSkeleton from '../components/LoadingSkeleton';
import useNotification from '../hooks/useNotification';
import './SearchPage.css';

const CATEGORIES = [
  "Technology", "Business", "Politics", "Science",
  "Health", "Sports", "Entertainment", "Environment", "World"
];

export const SearchPage = () => {
  const { showNotification } = useNotification();

  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [publisher, setPublisher] = useState('');
  const [region, setRegion] = useState('');
  const [sort, setSort] = useState('relevance');
  
  const [publishersList, setPublishersList] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  // Load publisher filters list on startup
  useEffect(() => {
    const loadPublishers = async () => {
      try {
        const list = await publisherService.listPublishers();
        setPublishersList(list || []);
      } catch (_) {
        // fail silently for secondary filters
      }
    };
    loadPublishers();
  }, []);

  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!query.trim()) {
      showNotification('Please enter a search query.', 'warning');
      return;
    }

    setLoading(true);
    setSearched(true);
    try {
      const data = await searchService.search(query, category, publisher, region, sort);
      setResults(data.results || []);
    } catch (err) {
      showNotification(err.message || 'Search execution failed.', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="search-page-container">
      <header className="search-header">
        <h2>Intelligence Database Search</h2>
      </header>

      {/* Search Input and Filters */}
      <form onSubmit={handleSearch} className="search-form-card">
        <div className="search-input-wrapper">
          <input
            type="search"
            placeholder="Search keywords, events, named entities..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="search-input-field"
            required
            aria-label="Search text query"
          />
          <button type="submit" className="search-submit-btn" disabled={loading}>
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>

        <div className="search-filters-grid">
          {/* Category Filter */}
          <div className="filter-group">
            <label htmlFor="filter-category">Category</label>
            <select
              id="filter-category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="">All Categories</option>
              {CATEGORIES.map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          {/* Publisher Filter */}
          <div className="filter-group">
            <label htmlFor="filter-publisher">Publisher</label>
            <select
              id="filter-publisher"
              value={publisher}
              onChange={(e) => setPublisher(e.target.value)}
            >
              <option value="">All Publishers</option>
              {publishersList.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          {/* Region Filter */}
          <div className="filter-group">
            <label htmlFor="filter-region">Region</label>
            <input
              id="filter-region"
              type="text"
              placeholder="e.g. India, Telangana"
              value={region}
              onChange={(e) => setRegion(e.target.value)}
            />
          </div>

          {/* Sort Selector */}
          <div className="filter-group">
            <label htmlFor="filter-sort">Sort By</label>
            <select
              id="filter-sort"
              value={sort}
              onChange={(e) => setSort(e.target.value)}
            >
              <option value="relevance">Relevance rank</option>
              <option value="newest">Newest first</option>
            </select>
          </div>
        </div>
      </form>

      {/* Results Rendering */}
      <section className="search-results-section">
        {loading ? (
          <LoadingSkeleton type="feed" />
        ) : searched && results.length === 0 ? (
          <div className="search-empty-state animate-slide-up">
            <div className="empty-icon">🔍</div>
            <h3>No intelligence matched</h3>
            <p>Try refining your query or resetting some filters.</p>
          </div>
        ) : (
          <div className="feed-list-container">
            {results.map((story) => (
              <StoryCard
                key={story.story_id}
                story={story}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
};
export default SearchPage;
