import useStore from '../store';

export default function StatsPanel() {
  const { stats, gamesToday, pipelineStatus, agentStats } = useStore();
  const onlineAgents = agentStats?.total_online || 0;

  const statCards = [
    {
      label: 'Games Built',
      value: stats.games_built ?? stats.total_games_built ?? 0,
      icon: '🎮',
      color: 'var(--accent-primary)',
      bg: 'rgba(124, 92, 255, 0.1)',
    },
    {
      label: 'Scripts Generated',
      value: stats.total_scripts_generated ?? 0,
      icon: '📜',
      color: 'var(--accent-tertiary)',
      bg: 'rgba(92, 255, 177, 0.1)',
    },
    {
      label: 'Agents Online',
      value: onlineAgents,
      icon: '🤖',
      color: onlineAgents > 0 ? 'var(--accent-tertiary)' : 'var(--accent-secondary)',
      bg: onlineAgents > 0 ? 'rgba(92, 255, 177, 0.1)' : 'rgba(255, 92, 138, 0.1)',
    },
    {
      label: 'Today',
      value: `${gamesToday}/3`,
      icon: '📅',
      color: 'var(--accent-info)',
      bg: 'rgba(92, 184, 255, 0.1)',
    },
  ];

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          <span className="icon">📊</span>
          Stats Overview
        </div>
        <span className="badge badge-primary">{pipelineStatus}</span>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '12px',
        marginBottom: '24px',
      }}>
        {statCards.map((stat) => (
          <div key={stat.label} style={{
            background: stat.bg,
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            padding: '20px',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '28px', marginBottom: '8px' }}>{stat.icon}</div>
            <div style={{ fontSize: '32px', fontWeight: 700, color: stat.color }}>{stat.value}</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>{stat.label}</div>
          </div>
        ))}
      </div>

      <div style={{
        background: 'var(--bg-elevated)',
        borderRadius: 'var(--radius-md)',
        padding: '16px',
        border: '1px solid var(--border)',
      }}>
        <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>Pipeline Progress</div>
        <div style={{
          display: 'flex',
          gap: '4px',
        }}>
          {['Scan', 'Plan', 'Code', 'Build', 'Check'].map((step, i) => {
            const steps = ['scanning_trends', 'creating_plan', 'generating_scripts', 'building_rbxlx', 'validating'];
            const currentIdx = steps.indexOf(pipelineStatus);
            const isActive = i === currentIdx;
            const isDone = currentIdx > i || pipelineStatus === 'complete' || pipelineStatus === 'idle';

            return (
              <div key={step} style={{ flex: 1, textAlign: 'center' }}>
                <div style={{
                  height: '4px',
                  borderRadius: '2px',
                  background: isDone ? 'var(--accent-tertiary)' : isActive ? 'var(--accent-primary)' : 'var(--border)',
                  marginBottom: '6px',
                  transition: 'all 0.3s',
                  ...(isActive ? { animation: 'pulse-glow 1.5s infinite' } : {}),
                }} />
                <span style={{
                  fontSize: '10px',
                  color: isActive ? 'var(--accent-primary)' : isDone ? 'var(--accent-tertiary)' : 'var(--text-muted)',
                  fontWeight: isActive ? 600 : 400,
                }}>{step}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
