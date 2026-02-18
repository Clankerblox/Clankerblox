import { useEffect, useState } from 'react';
import useStore from './store';
import Header from './components/Header';
import StatusBar from './components/StatusBar';
import TrendPanel from './components/TrendPanel';
import GameBuilder from './components/GameBuilder';
import GamesList from './components/GamesList';
import LiveLogs from './components/LiveLogs';
import StatsPanel from './components/StatsPanel';
import AgentsPanel from './components/AgentsPanel';
import './App.css';

function App() {
  const { connectWs, fetchStatus, fetchTrends, fetchGames, fetchStats, fetchAgentStats } = useStore();
  const [activeTab, setActiveTab] = useState('dashboard');

  useEffect(() => {
    connectWs();
    fetchStatus();
    fetchTrends();
    fetchGames();
    fetchStats();
    fetchAgentStats();
    // Poll status every 5 seconds
    const interval = setInterval(() => {
      fetchStatus();
      fetchGames();
      fetchStats();
      fetchAgentStats();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app">
      <Header />
      <StatusBar />
      <nav className="tab-nav">
        {[
          { id: 'dashboard', label: 'Dashboard', icon: '📊' },
          { id: 'trends', label: 'Trends', icon: '🔥' },
          { id: 'builder', label: 'Builder', icon: '🏗️' },
          { id: 'games', label: 'Games', icon: '🎮' },
          { id: 'agents', label: 'Agents', icon: '🤖' },
          { id: 'logs', label: 'Live Logs', icon: '📡' },
        ].map((tab) => (
          <button
            key={tab.id}
            className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="tab-icon">{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </nav>
      <main className="main-content">
        {activeTab === 'dashboard' && (
          <div className="dashboard-grid">
            <div className="dashboard-left">
              <StatsPanel />
              <AgentsPanel compact />
            </div>
            <div className="dashboard-right">
              <TrendPanel compact />
              <LiveLogs compact />
            </div>
          </div>
        )}
        {activeTab === 'trends' && <TrendPanel />}
        {activeTab === 'builder' && <GameBuilder />}
        {activeTab === 'games' && <GamesList />}
        {activeTab === 'agents' && <AgentsPanel />}
        {activeTab === 'logs' && <LiveLogs />}
      </main>
    </div>
  );
}

export default App;
