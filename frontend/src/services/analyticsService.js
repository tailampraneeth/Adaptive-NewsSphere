/**
 * Local Analytics Service
 * Tracks user interactions and RAG stats locally in localStorage.
 * No third-party servers.
 */
const STORAGE_KEY = 'ans_local_analytics';

const getAnalytics = () => {
  const data = localStorage.getItem(STORAGE_KEY);
  if (!data) {
    return {
      loginCount: 0,
      storyOpens: {},
      chatOpens: {},
      themeUsage: { light: 0, dark: 0, system: 0 },
      sessionStartTime: Date.now(),
      totalSessionDurationSeconds: 0,
      avgLlmLatencyMs: 0,
      llmCallsCount: 0
    };
  }
  try {
    return JSON.parse(data);
  } catch (_) {
    return {};
  }
};

const saveAnalytics = (data) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
};

export const analyticsService = {
  recordLogin() {
    const stats = getAnalytics();
    stats.loginCount = (stats.loginCount || 0) + 1;
    saveAnalytics(stats);
  },

  recordStoryOpen(storyId) {
    const stats = getAnalytics();
    stats.storyOpens = stats.storyOpens || {};
    stats.storyOpens[storyId] = (stats.storyOpens[storyId] || 0) + 1;
    saveAnalytics(stats);
  },

  recordChatOpen(storyId) {
    const stats = getAnalytics();
    stats.chatOpens = stats.chatOpens || {};
    stats.chatOpens[storyId] = (stats.chatOpens[storyId] || 0) + 1;
    saveAnalytics(stats);
  },

  recordThemeUsage(themeName) {
    const stats = getAnalytics();
    stats.themeUsage = stats.themeUsage || { light: 0, dark: 0, system: 0 };
    stats.themeUsage[themeName] = (stats.themeUsage[themeName] || 0) + 1;
    saveAnalytics(stats);
  },

  recordLlmLatency(latencyMs) {
    const stats = getAnalytics();
    const currentTotal = (stats.avgLlmLatencyMs || 0) * (stats.llmCallsCount || 0);
    stats.llmCallsCount = (stats.llmCallsCount || 0) + 1;
    stats.avgLlmLatencyMs = Math.round((currentTotal + latencyMs) / stats.llmCallsCount);
    saveAnalytics(stats);
  },

  updateSessionDuration() {
    const stats = getAnalytics();
    const durationSeconds = Math.round((Date.now() - stats.sessionStartTime) / 1000);
    stats.totalSessionDurationSeconds = (stats.totalSessionDurationSeconds || 0) + durationSeconds;
    stats.sessionStartTime = Date.now(); // Reset start reference
    saveAnalytics(stats);
  },

  getStats() {
    this.updateSessionDuration();
    return getAnalytics();
  }
};
export default analyticsService;
