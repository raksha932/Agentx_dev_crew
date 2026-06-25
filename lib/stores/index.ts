import { create } from 'zustand';

export interface WebSocketMessage {
  agent: string;
  status: string;
  progress: number;
  message: string;
  timestamp: string;
  data?: Record<string, unknown>;
}

interface RunState {
  runs: Run[];
  currentRun: RunDetail | null;
  isLoading: boolean;
  error: string | null;
  pagination: {
    total: number;
    page: number;
    pageSize: number;
  };
  wsConnected: boolean;
  wsMessages: WebSocketMessage[];

  fetchRuns: (page?: number, pageSize?: number, status?: string) => Promise<void>;
  fetchRunDetails: (runId: string) => Promise<void>;
  clearCurrentRun: () => void;
  addWsMessage: (message: WebSocketMessage) => void;
  setWsConnected: (connected: boolean) => void;
  clearWsMessages: () => void;
}

export const useRunStore = create<RunState>((set) => ({
  runs: [],
  currentRun: null,
  isLoading: false,
  error: null,
  pagination: { total: 0, page: 1, pageSize: 10 },
  wsConnected: false,
  wsMessages: [],

  fetchRuns: async (page = 1, pageSize = 10, status?: string) => {
    set({ isLoading: true, error: null });
    try {
      const data = await listRuns(page, pageSize, status);
      set({
        runs: data.runs,
        pagination: { total: data.total, page: data.page, pageSize: data.page_size },
        isLoading: false,
      });
    } catch (error) {
      set({ error: 'Failed to fetch runs', isLoading: false });
    }
  },

  fetchRunDetails: async (runId: string) => {
    set({ isLoading: true, error: null });
    try {
      const data = await getRunDetails(runId);
      set({ currentRun: data, isLoading: false });
    } catch (error) {
      set({ error: 'Failed to fetch run details', isLoading: false });
    }
  },

  clearCurrentRun: () => set({ currentRun: null }),

  addWsMessage: (message) =>
    set((state) => ({ wsMessages: [...state.wsMessages, message] })),

  setWsConnected: (connected) => set({ wsConnected: connected }),

  clearWsMessages: () => set({ wsMessages: [] }),
}));

interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark';
  notifications: Notification[];

  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
  addNotification: (notification: Omit<Notification, 'id'>) => void;
  removeNotification: (id: string) => void;
}

interface Notification {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title: string;
  message?: string;
  duration?: number;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  theme: 'dark',
  notifications: [],

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  setTheme: (theme) => set({ theme }),

  addNotification: (notification) => {
    const id = Math.random().toString(36).substring(7);
    set((state) => ({
      notifications: [...state.notifications, { ...notification, id }],
    }));
    setTimeout(() => {
      set((state) => ({
        notifications: state.notifications.filter((n) => n.id !== id),
      }));
    }, notification.duration || 5000);
  },

  removeNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),
}));

import { Run, RunDetail, listRuns, getRunDetails } from '../api';
