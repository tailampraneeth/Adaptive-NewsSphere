import { request } from './api';

export const storyService = {
  async getStoryDetails(storyId) {
    const data = await request(`/api/v1/stories/${storyId}`, {
      method: 'GET',
    });
    return data;
  }
};
export default storyService;
