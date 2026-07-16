import { request } from './api';

export const feedService = {
  async getPersonalizedFeed(userId) {
    const data = await request(`/api/v1/feed/${userId}`, {
      method: 'GET',
    });
    return data;
  },

  async recordInteraction(userId, storyId, interactionType, dwellSeconds = null) {
    const data = await request('/api/v1/feed/interact', {
      method: 'POST',
      body: {
        user_id: userId,
        story_id: storyId,
        interaction_type: interactionType,
        dwell_seconds: dwellSeconds,
      },
    });
    return data;
  },

  async getProfileHealth(userId) {
    const data = await request(`/api/v1/feed/${userId}/profile/health`, {
      method: 'GET',
    });
    return data;
  },

  async getRecommendationStats() {
    const data = await request('/api/v1/feed/health', {
      method: 'GET',
    });
    return data;
  }
};
export default feedService;
