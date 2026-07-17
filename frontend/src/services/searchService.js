import { request } from './api';

export const searchService = {
  async search(query, category = '', publisher = '', region = '', sort = 'relevance') {
    let path = `/api/v1/search?q=${encodeURIComponent(query)}&sort=${sort}`;
    if (category) path += `&category=${encodeURIComponent(category)}`;
    if (publisher) path += `&publisher=${encodeURIComponent(publisher)}`;
    if (region) path += `&region=${encodeURIComponent(region)}`;
    
    return await request(path, { method: 'GET' });
  }
};
export default searchService;
