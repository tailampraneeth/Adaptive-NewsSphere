import { request } from './api';

export const chatService = {
  async createSession(userId, storyId) {
    const data = await request('/api/v1/chat/sessions', {
      method: 'POST',
      body: {
        user_id: userId,
        story_id: storyId,
      },
    });
    return data;
  },

  async getSession(sessionId) {
    const data = await request(`/api/v1/chat/sessions/${sessionId}`, {
      method: 'GET',
    });
    return data;
  },

  async listSessions(userId) {
    const data = await request(`/api/v1/chat/sessions/user/${userId}/list`, {
      method: 'GET',
    });
    return data;
  },

  async deleteSession(sessionId) {
    const data = await request(`/api/v1/chat/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    return data;
  },

  async getChatHealth() {
    const data = await request('/api/v1/chat/health', {
      method: 'GET',
    });
    return data;
  },

  /**
   * Submits a message to the RAG chat assistant, reading standard SSE stream
   * tokens using a native Fetch stream reader.
   */
  async sendMessage(sessionId, message, onChunk, onComplete, onError) {
    const token = localStorage.getItem('token');
    const headers = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(`/api/v1/chat/sessions/${sessionId}/message`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ message }),
      });

      if (!response.ok) {
        let errText = 'Failed to submit chat message';
        try {
          const responseText = await response.text();
          try {
            const errJson = JSON.parse(responseText);
            errText = errJson.detail || errText;
          } catch (_) {
            errText = responseText || errText;
          }
        } catch (_) {
          // Fallback if even text() fails
        }
        throw new Error(errText);
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('text/event-stream')) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop(); // Keep incomplete line

          for (const line of lines) {
            const cleanLine = line.trim();
            if (!cleanLine) continue;

            if (cleanLine.startsWith('data: ')) {
              const dataStr = cleanLine.substring(6);
              if (dataStr === '[DONE]') {
                onComplete();
                return;
              }
              try {
                const parsed = JSON.parse(dataStr);
                onChunk(parsed);
              } catch (_) {
                // Fallback direct yield
                onChunk({ token: dataStr });
              }
            }
          }
        }
        // Yield any trailing buffer
        if (buffer && buffer.trim()) {
          const cleanLine = buffer.trim();
          if (cleanLine.startsWith('data: ')) {
            const dataStr = cleanLine.substring(6);
            if (dataStr !== '[DONE]') {
              try {
                onChunk(JSON.parse(dataStr));
              } catch (_) {
                onChunk({ token: dataStr });
              }
            }
          }
        }
        onComplete();
      } else {
        // Fallback for non-streaming sync responses
        const data = await response.json();
        onChunk(data);
        onComplete();
      }
    } catch (err) {
      if (onError) {
        onError(err);
      } else {
        console.error('SSE connection failed:', err);
      }
    }
  }
};
export default chatService;
