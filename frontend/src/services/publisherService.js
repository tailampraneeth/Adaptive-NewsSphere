import { request } from './api';

export const publisherService = {
  async listPublishers() {
    return await request('/api/v1/publishers', { method: 'GET' });
  }
};
export default publisherService;
