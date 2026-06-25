import axios, { AxiosError } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export interface Run {
  id: string;
  repo_url: string;
  branch: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  issues_count?: number;
}

export interface Issue {
  id: string;
  title: string;
  severity: string;
  description: string | null;
  file_path: string | null;
  line_number: number | null;
  code_snippet: string | null;
  created_at: string;
}

export interface RootCause {
  id: string;
  issue_title: string;
  cause: string;
  impact: string | null;
  confidence: number;
  reasoning: string | null;
}

export interface Fix {
  id: string;
  issue_title: string;
  patch: string;
  explanation: string | null;
  confidence: number;
  status: string;
  file_path: string | null;
}

export interface PullRequest {
  id: string;
  github_pr_number: number | null;
  pr_url: string | null;
  status: string;
  title: string | null;
}

export interface AgentExecution {
  id: string;
  agent_name: string;
  agent_order: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  progress: number;
  logs: string[];
}

export interface RunDetail {
  id: string;
  repo_url: string;
  branch: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
  issues: Issue[];
  root_causes: RootCause[];
  fixes: Fix[];
  pull_request: PullRequest | null;
  agent_executions: AgentExecution[];
}

export interface CreateRunResponse {
  run_id: string;
  status: string;
  message: string;
}

export interface Stats {
  total_runs: number;
  successful_runs: number;
  total_issues: number;
  total_prs: number;
  avg_issues_per_run: number;
}

export interface WebSocketMessage {
  agent: string;
  status: string;
  progress: number;
  message: string;
  timestamp: string;
  data?: Record<string, unknown>;
}

export interface RunListResponse {
  runs: Run[];
  total: number;
  page: number;
  page_size: number;
}

export async function startRun(repo_url: string, branch: string = 'main'): Promise<CreateRunResponse> {
  try {
    const response = await api.post('/runs', { repo_url, branch });
    return response.data;
  } catch (error) {
    throw error;
  }
}

export async function listRuns(page: number = 1, pageSize: number = 10, status?: string): Promise<RunListResponse> {
  try {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (status) params.append('status', status);
    const response = await api.get(`/runs?${params}`);
    return response.data;
  } catch (error) {
    throw error;
  }
}

export async function getRunDetails(runId: string): Promise<RunDetail> {
  try {
    const response = await api.get(`/runs/${runId}`);
    return response.data;
  } catch (error) {
    throw error;
  }
}

export async function cancelRun(runId: string): Promise<void> {
  try {
    await api.delete(`/runs/${runId}`);
  } catch (error) {
    throw error;
  }
}

export async function submitFeedback(runId: string, rating: number, comment?: string): Promise<void> {
  try {
    await api.post('/feedback', { run_id: runId, rating, comment });
  } catch (error) {
    throw error;
  }
}

export async function getStats(): Promise<Stats> {
  try {
    const response = await api.get('/stats');
    return response.data;
  } catch (error) {
    throw error;
  }
}

export async function getHealth(): Promise<{ status: string }> {
  try {
    const response = await api.get('/health');
    return response.data;
  } catch (error) {
    throw error;
  }
}

let wsInstance: WebSocket | null = null;
let reconnectAttempts = 0;
const MAX_RECONNECT = 5;

export function createWebSocketConnection(runId: string, onMessage?: (data: WebSocketMessage) => void, onStatusChange?: (connected: boolean) => void): WebSocket | null {
  if (typeof window === 'undefined') return null;

  const connect = () => {
    try {
      wsInstance = new WebSocket(`${WS_URL}/ws/runs/${runId}`);

      wsInstance.onopen = () => {
        console.log('WebSocket connected');
        reconnectAttempts = 0;
        onStatusChange?.(true);
      };

      wsInstance.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'ping' || data.type === 'pong') {
            wsInstance?.send(JSON.stringify({ type: 'pong' }));
            return;
          }
          onMessage?.(data);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      wsInstance.onclose = () => {
        console.log('WebSocket disconnected');
        onStatusChange?.(false);

        // Attempt reconnect
        if (reconnectAttempts < MAX_RECONNECT) {
          reconnectAttempts++;
          console.log(`Reconnecting... attempt ${reconnectAttempts}`);
          setTimeout(connect, 2000 * reconnectAttempts);
        }
      };

      wsInstance.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      onStatusChange?.(false);
    }
  };

  connect();
  return wsInstance;
}

export function closeWebSocket() {
  if (wsInstance) {
    wsInstance.close();
    wsInstance = null;
  }
}
