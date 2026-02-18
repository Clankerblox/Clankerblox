import useStore from '../store';

const STATUS_CONFIG = {
  idle: { label: 'Ready', color: 'var(--accent-tertiary)', icon: '✅', bg: 'rgba(92, 255, 177, 0.1)' },
  scanning_trends: { label: 'Scanning Trends', color: 'var(--accent-info)', icon: '🔍', bg: 'rgba(92, 184, 255, 0.1)' },
  creating_plan: { label: 'Creating Game Plan', color: 'var(--accent-primary)', icon: '📝', bg: 'rgba(124, 92, 255, 0.1)' },
  generating_scripts: { label: 'Generating Lua Scripts', color: 'var(--accent-warning)', icon: '⚡', bg: 'rgba(255, 180, 92, 0.1)' },
  building_rbxlx: { label: 'Building Game File', color: 'var(--accent-secondary)', icon: '🏗️', bg: 'rgba(255, 92, 138, 0.1)' },
  validating: { label: 'Validating Game', color: 'var(--accent-info)', icon: '🔎', bg: 'rgba(92, 184, 255, 0.1)' },
  complete: { label: 'Game Complete!', color: 'var(--accent-tertiary)', icon: '🎮', bg: 'rgba(92, 255, 177, 0.1)' },
  error: { label: 'Error', color: 'var(--accent-secondary)', icon: '❌', bg: 'rgba(255, 92, 138, 0.1)' },
  fixing_errors: { label: 'Auto-fixing...', color: 'var(--accent-warning)', icon: '🔧', bg: 'rgba(255, 180, 92, 0.1)' },
};

export default function StatusBar() {
  const { pipelineStatus, currentGame, gamesToday, lastScan, agentStats } = useStore();
  const config = STATUS_CONFIG[pipelineStatus] || STATUS_CONFIG.idle;
  const isActive = pipelineStatus !== 'idle' && pipelineStatus !== 'complete' && pipelineStatus !== 'error';
  const onlineAgents = agentStats?.total_online || 0;

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '10px 24px',
      background: config.bg,
      borderBottom: '1px solid var(--border)',
      fontSize: '13px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: config.color,
          fontWeight: 600,
        }}>
          <span>{config.icon}</span>
          <span>{config.label}</span>
          {isActive && <div className="spinner" style={{ width: 14, height: 14, borderWidth: 2, borderTopColor: config.color }} />}
        </div>
        {currentGame && (
          <span style={{ color: 'var(--text-muted)' }}>
            Working on: <span style={{ color: 'var(--text-secondary)' }}>{currentGame}</span>
          </span>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '20px', color: 'var(--text-muted)' }}>
        <span>Games today: <b style={{ color: 'var(--accent-primary)' }}>{gamesToday}/3</b></span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: onlineAgents > 0 ? 'var(--accent-tertiary)' : 'var(--accent-secondary)',
            display: 'inline-block',
          }} />
          Agents: <b style={{ color: onlineAgents > 0 ? 'var(--accent-tertiary)' : 'var(--accent-secondary)' }}>{onlineAgents}</b>
        </span>
        {lastScan && (
          <span>Last scan: <b style={{ color: 'var(--text-secondary)' }}>{new Date(lastScan).toLocaleTimeString()}</b></span>
        )}
      </div>
    </div>
  );
}
