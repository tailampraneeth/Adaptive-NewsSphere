import '@testing-library/jest-dom';
import { beforeAll, afterAll, afterEach } from 'vitest';

// Global mocks for testing environment if needed
beforeAll(() => {
  global.localStorage = {
    state: {},
    getItem(key) { return this.state[key] || null; },
    setItem(key, val) { this.state[key] = String(val); },
    removeItem(key) { delete this.state[key]; },
    clear() { this.state = {}; }
  };
});

afterEach(() => {
  localStorage.clear();
});
