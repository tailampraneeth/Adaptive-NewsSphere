import { request } from './api';

export const feedService = {
  async getPersonalizedFeed(cursor = '', limit = 20) {
    const path = `/api/v1/feed?limit=${limit}${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`;
    return await request(path, { method: 'GET' });
  },

  async getTrendingFeed(cursor = '', limit = 20) {
    const path = `/api/v1/feed/trending?limit=${limit}${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`;
    return await request(path, { method: 'GET' });
  },

  async recordInteraction(storyId, interactionType, readPct = 0, dwellSeconds = 0) {
    return await request('/api/v1/feed/interact', {
      method: 'POST',
      body: {
        story_id: storyId,
        interaction_type: interactionType,
        read_pct: readPct,
        dwell_seconds: dwellSeconds,
      },
    });
  }
};
export default feedService;
