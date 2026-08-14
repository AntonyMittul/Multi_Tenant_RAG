export const API_BASE_URL = '/api/v1';

export class RAGClient {
  private apiKey: string;

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  private get headers() {
    return {
      'Content-Type': 'application/json',
      ...(this.apiKey ? { 'X-API-Key': this.apiKey } : {}),
    };
  }

  // Tenant API
  static async createTenant(name: string): Promise<{ api_key: string; name: string; id: string }> {
    const response = await fetch(`${API_BASE_URL}/tenants/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    if (!response.ok) {
      let errText = '';
      try { errText = await response.text(); } catch(e) {}
      throw new Error(`Failed to create tenant: [${response.status} ${response.statusText}] ${errText}`);
    }
    return response.json();
  }

  async getTenantMe(): Promise<{ id: string; name: string }> {
    const response = await fetch(`${API_BASE_URL}/tenants/me`, {
      method: 'GET',
      headers: this.headers,
    });
    if (!response.ok) {
      throw new Error('Invalid API Key or Tenant');
    }
    return response.json();
  }

  async uploadDocument(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: 'POST',
      headers: {
        'X-API-Key': this.apiKey,
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }
    return response.json();
  }

  async generateAnswer(query: string, stream: boolean = false, filename?: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/generate/`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ query, top_k: 5, temperature: 0.2, stream, filename }),
    });

    if (!response.ok) {
      throw new Error(`Generation failed: ${response.statusText}`);
    }
    return response.json();
  }

  async generateAnswerStream(query: string, filename?: string, onUpdate?: (text: string, sources: any[]) => void): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/generate/`, {
      method: 'POST',
      headers: { ...this.headers, 'Accept': 'text/event-stream' },
      body: JSON.stringify({ query, top_k: 5, temperature: 0.2, stream: true, filename }),
    });

    if (!response.ok) {
      throw new Error(`Generation failed: ${response.statusText}`);
    }

    if (!response.body) throw new Error('No response body');

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let text = '';
    let sources: any[] = [];
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.substring(6);
          if (dataStr.trim() === '[DONE]') break;
          try {
            const data = JSON.parse(dataStr);
            if (data.sources) {
              sources = data.sources;
            }
            if (data.text) {
              text += data.text;
            }
            if (onUpdate) {
              onUpdate(text, sources);
            }
          } catch (e) {
            console.error('Failed to parse SSE data', e);
          }
        }
      }
    }
  }
}


// Cache buster
