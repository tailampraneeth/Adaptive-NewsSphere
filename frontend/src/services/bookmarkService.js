import { request } from './api';

export const bookmarkService = {
  async listBookmarks() {
    return await request('/api/v1/bookmarks', { method: 'GET' });
  },

  async addBookmark(storyId) {
    return await request(`/api/v1/bookmarks/${storyId}`, { method: 'POST' });
  },

  async removeBookmark(storyId) {
    return await request(`/api/v1/bookmarks/${storyId}`, { method: 'DELETE' });
  }
};
export default bookmarkService;
