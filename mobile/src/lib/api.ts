import { fetch as streamingFetch } from 'expo/fetch';

import { API_URL } from './config';
import { SSEParser, type ServerEvent } from './sse';
import type { Conversation, ConversationDetail, User } from './types';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

let authToken: string | null = null;
let onUnauthorized: (() => void) | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler;
}

export function authHeaders(): Record<string, string> {
  return authToken ? { Authorization: `Bearer ${authToken}` } : {};
}

async function errorFrom(response: Response): Promise<ApiError> {
  if (response.status === 401) onUnauthorized?.();
  let detail = `Request failed (${response.status})`;
  try {
    const body = await response.json();
    if (typeof body.detail === 'string') detail = body.detail;
    else if (Array.isArray(body.detail) && body.detail[0]?.msg) detail = body.detail[0].msg;
  } catch {
    // Non-JSON error body; keep the generic message.
  }
  return new ApiError(response.status, detail);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...authHeaders(), ...(init.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, `Can't reach the AuraFarm server at ${API_URL}`);
  }
  if (!response.ok) throw await errorFrom(response);
  return response.status === 204 ? (undefined as T) : response.json();
}

type AuthResponse = { access_token: string; user: User };

export const api = {
  register: (email: string, name: string, password: string) =>
    request<AuthResponse>('/auth/register', { method: 'POST', body: JSON.stringify({ email, name, password }) }),
  login: (email: string, password: string) =>
    request<AuthResponse>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  me: () => request<User>('/auth/me'),

  listConversations: () => request<Conversation[]>('/conversations'),
  createConversation: () => request<Conversation>('/conversations', { method: 'POST', body: '{}' }),
  getConversation: (id: string) => request<ConversationDetail>(`/conversations/${id}`),
  renameConversation: (id: string, title: string) =>
    request<Conversation>(`/conversations/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) }),
  deleteConversation: (id: string) => request<void>(`/conversations/${id}`, { method: 'DELETE' }),

  async uploadImage(uri: string, mimeType: string): Promise<string> {
    const form = new FormData();
    const extension = mimeType.split('/')[1] ?? 'jpg';
    // React Native's FormData accepts a { uri, name, type } file descriptor.
    form.append('image', { uri, name: `leaf.${extension}`, type: mimeType } as any);
    let response: Response;
    try {
      response = await fetch(`${API_URL}/uploads`, { method: 'POST', headers: authHeaders(), body: form });
    } catch {
      throw new ApiError(0, `Can't reach the AuraFarm server at ${API_URL}`);
    }
    if (!response.ok) throw await errorFrom(response);
    return (await response.json()).id;
  },

  /** Sends a message and calls onEvent for each server-sent event as the agent works. */
  async sendMessage(
    conversationId: string,
    body: { text: string; image_id?: string | null; lat?: number; lon?: number },
    onEvent: (event: ServerEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    let response;
    try {
      response = await streamingFetch(`${API_URL}/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream', ...authHeaders() },
        body: JSON.stringify(body),
        signal,
      });
    } catch (e) {
      if (signal?.aborted) return;
      throw new ApiError(0, `Can't reach the AuraFarm server at ${API_URL}`);
    }
    if (!response.ok) throw await errorFrom(response as unknown as Response);
    if (!response.body) throw new ApiError(0, 'The server did not stream a response');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const parser = new SSEParser();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const event of parser.push(decoder.decode(value, { stream: true }))) onEvent(event);
    }
  },
};
