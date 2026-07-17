import { request } from './api';

export const storyService = {
  async getStoryDetails(storyId) {
    return await request(`/api/v1/stories/${storyId}`, {
      method: 'GET',
    });
  },

  async getRelatedStories(storyId) {
    return await request(`/api/v1/stories/${storyId}/related`, {
      method: 'GET',
    });
  }
};
export default storyService;
