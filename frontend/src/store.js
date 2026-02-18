import { create } from 'zustand';

const API_BASE = '/api';

const useStore = create((set, get) => ({
  // Theme
  theme: 'dark',
  toggleTheme: () => {
    const newTheme = get().theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    set({ theme: newTheme });
  },

  // Pipeline state
  pipelineStatus: 'idle',
  currentGame: null,
  gamesToday: 0,
  lastScan: null,
  stats: {},

  // Trends
  trends: null,
  trendHistory: [],

  // Games
  games: [],
  selectedGame: null,

  // Live logs
  logs: [],
  wsConnected: false,

  // Agent network state
  agentStats: {
    total_registered: 0,
    total_online: 0,
    roles_online: {},
    total_tasks_completed: 0,
    total_rewards_distributed: 0,
    agents_online: [],
    roles_available: {},
  },

  // Loading states — tracks in-progress operations for button disabling
  loading: { trends: false, build: false, games: false, buildingSingle: {} },

  // WebSocket
  ws: null,
  connectWs: () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      set({ wsConnected: true });
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'history') {
          set({ logs: data.events || [] });
        } else if (data.type === 'state') {
          const s = data.data;
          set({
            pipelineStatus: s.status,
            currentGame: s.current_game,
            gamesToday: s.games_today,
            lastScan: s.last_scan,
            stats: s.stats || {},
          });
        } else if (data.timestamp) {
          // It's a log event
          set((state) => ({
            logs: [...state.logs.slice(-200), data],
            pipelineStatus: data.event_type === 'system' && data.data?.status ? data.data.status : state.pipelineStatus,
          }));
        }
      } catch (e) {
        console.error('WS parse error:', e);
      }
    };

    ws.onclose = () => {
      set({ wsConnected: false });
      // Auto-reconnect after 3 seconds
      setTimeout(() => get().connectWs(), 3000);
    };

    ws.onerror = () => {
      ws.close();
    };

    // Keepalive ping
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 30000);

    set({ ws, _pingInterval: pingInterval });
  },

  // API calls
  fetchStatus: async () => {
    try {
      const res = await fetch(`${API_BASE}/status`);
      const data = await res.json();
      set({
        pipelineStatus: data.pipeline?.status || 'idle',
        currentGame: data.pipeline?.current_game,
        gamesToday: data.pipeline?.games_today || 0,
        lastScan: data.pipeline?.last_scan,
        stats: data.pipeline?.stats || {},
      });
    } catch (e) { console.error('Failed to fetch status:', e); }
  },

  scanTrends: async () => {
    set((s) => ({ loading: { ...s.loading, trends: true } }));
    try {
      const res = await fetch(`${API_BASE}/trends/scan`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        console.error('Trend scan rejected:', err);
        set((s) => ({ loading: { ...s.loading, trends: false } }));
        return;
      }
      // Poll until pipeline goes back to idle
      const pollUntilDone = async () => {
        for (let i = 0; i < 120; i++) {
          await new Promise((r) => setTimeout(r, 2000));
          const status = get().pipelineStatus;
          if (status === 'idle' || status === 'complete' || status === 'error') {
            await get().fetchTrends();
            set((s) => ({ loading: { ...s.loading, trends: false } }));
            return;
          }
        }
        set((s) => ({ loading: { ...s.loading, trends: false } }));
      };
      pollUntilDone();
    } catch (e) {
      console.error('Trend scan failed:', e);
      set((s) => ({ loading: { ...s.loading, trends: false } }));
    }
  },

  fetchTrends: async () => {
    try {
      const res = await fetch(`${API_BASE}/trends/latest`);
      if (res.ok) {
        const data = await res.json();
        set({ trends: data });
      }
    } catch (e) { console.error('Failed to fetch trends:', e); }
  },

  buildGame: async (conceptIndex = 0) => {
    set((s) => ({
      loading: {
        ...s.loading,
        build: true,
        buildingSingle: { ...s.loading.buildingSingle, [conceptIndex]: true },
      },
    }));
    try {
      const res = await fetch(`${API_BASE}/build/single`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ concept_index: conceptIndex }),
      });
      if (!res.ok) {
        set((s) => ({
          loading: { ...s.loading, build: false, buildingSingle: { ...s.loading.buildingSingle, [conceptIndex]: false } },
        }));
        return;
      }
      // Poll until pipeline returns to idle/complete/error
      const poll = async () => {
        for (let i = 0; i < 300; i++) {
          await new Promise((r) => setTimeout(r, 2000));
          const status = get().pipelineStatus;
          if (status === 'idle' || status === 'complete' || status === 'error') {
            await get().fetchGames();
            set((s) => ({
              loading: { ...s.loading, build: false, buildingSingle: {} },
            }));
            return;
          }
        }
        set((s) => ({ loading: { ...s.loading, build: false, buildingSingle: {} } }));
      };
      poll();
    } catch (e) {
      console.error('Build failed:', e);
      set((s) => ({ loading: { ...s.loading, build: false, buildingSingle: {} } }));
    }
  },

  buildAllGames: async () => {
    set((s) => ({ loading: { ...s.loading, build: true } }));
    try {
      const res = await fetch(`${API_BASE}/build/all`, { method: 'POST' });
      if (!res.ok) {
        set((s) => ({ loading: { ...s.loading, build: false } }));
        return;
      }
      // Poll until pipeline returns to idle/complete/error
      const poll = async () => {
        for (let i = 0; i < 600; i++) {
          await new Promise((r) => setTimeout(r, 2000));
          const status = get().pipelineStatus;
          if (status === 'idle' || status === 'complete' || status === 'error') {
            await get().fetchGames();
            set((s) => ({ loading: { ...s.loading, build: false } }));
            return;
          }
        }
        set((s) => ({ loading: { ...s.loading, build: false } }));
      };
      poll();
    } catch (e) {
      console.error('Build all failed:', e);
      set((s) => ({ loading: { ...s.loading, build: false } }));
    }
  },

  buildCustomGame: async (concept) => {
    set((s) => ({ loading: { ...s.loading, build: true } }));
    try {
      const res = await fetch(`${API_BASE}/build/custom`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(concept),
      });
      if (!res.ok) {
        set((s) => ({ loading: { ...s.loading, build: false } }));
        return;
      }
      const poll = async () => {
        for (let i = 0; i < 300; i++) {
          await new Promise((r) => setTimeout(r, 2000));
          const status = get().pipelineStatus;
          if (status === 'idle' || status === 'complete' || status === 'error') {
            await get().fetchGames();
            set((s) => ({ loading: { ...s.loading, build: false } }));
            return;
          }
        }
        set((s) => ({ loading: { ...s.loading, build: false } }));
      };
      poll();
    } catch (e) {
      console.error('Custom build failed:', e);
      set((s) => ({ loading: { ...s.loading, build: false } }));
    }
  },

  fetchGames: async () => {
    set((s) => ({ loading: { ...s.loading, games: true } }));
    try {
      const res = await fetch(`${API_BASE}/games`);
      if (res.ok) {
        const data = await res.json();
        set({ games: data.games || [] });
      }
    } catch (e) { console.error('Failed to fetch games:', e); }
    set((s) => ({ loading: { ...s.loading, games: false } }));
  },

  fetchGameDetail: async (gameId) => {
    try {
      const res = await fetch(`${API_BASE}/games/${gameId}`);
      if (res.ok) {
        const data = await res.json();
        set({ selectedGame: data });
        return data;
      }
    } catch (e) { console.error('Failed to fetch game detail:', e); }
    return null;
  },

  fetchStats: async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`);
      if (res.ok) {
        const data = await res.json();
        set({ stats: data });
      }
    } catch (e) { console.error('Failed to fetch stats:', e); }
  },

  fetchAgentStats: async () => {
    try {
      const res = await fetch(`${API_BASE}/agents/stats`);
      if (res.ok) {
        const data = await res.json();
        set({ agentStats: data });
      }
    } catch (e) { /* Agent API may not be reachable */ }
  },
}));

export default useStore;
