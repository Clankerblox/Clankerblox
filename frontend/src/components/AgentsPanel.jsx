import useStore from '../store';

const ROLE_EMOJIS = {
  trend_researcher: '🔍',
  theme_designer: '🎨',
  world_architect: '📐',
  quality_reviewer: '✅',
  script_writer: '💻',
};

export default function AgentsPanel({ compact = false }) {
  const { agentStats } = useStore();
  const {
    total_registered = 0,
    total_online = 0,
    roles_online = {},
    total_tasks_completed = 0,
    total_rewards_distributed = 0,
    agents_online = [],
    roles_available = {},
  } = agentStats;

  if (compact) {
    return (
      <div className="card">
        <div className="card-header">
          <div className="card-title"><span className="icon">🤖</span> Agent Network</div>
          <span className={`badge ${total_online > 0 ? 'badge-success' : 'badge-error'}`}>
            {total_online > 0 ? `${total_online} online` : 'No agents'}
          </span>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          gap: '8px',
          marginBottom: '12px',
        }}>
          <div style={{
            padding: '12px',
            background: 'rgba(124, 92, 255, 0.1)',
            borderRadius: 'var(--radius-sm)',
            textAlign: 'center',
            border: '1px solid var(--border)',
          }}>
            <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--accent-primary)' }}>{total_registered}</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Registered</div>
          </div>
          <div style={{
            padding: '12px',
            background: total_online > 0 ? 'rgba(92, 255, 177, 0.1)' : 'rgba(255, 92, 138, 0.1)',
            borderRadius: 'var(--radius-sm)',
            textAlign: 'center',
            border: '1px solid var(--border)',
          }}>
            <div style={{ fontSize: '22px', fontWeight: 700, color: total_online > 0 ? 'var(--accent-tertiary)' : 'var(--accent-secondary)' }}>
              {total_online}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Online</div>
          </div>
          <div style={{
            padding: '12px',
            background: 'rgba(255, 180, 92, 0.1)',
            borderRadius: 'var(--radius-sm)',
            textAlign: 'center',
            border: '1px solid var(--border)',
          }}>
            <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--accent-warning)' }}>{total_tasks_completed}</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Tasks Done</div>
          </div>
        </div>

        {agents_online.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {agents_online.slice(0, 4).map((agent, i) => (
              <div key={i} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 10px',
                background: 'var(--bg-elevated)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border)',
                fontSize: '13px',
              }}>
                <span style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: 'var(--accent-tertiary)',
                  boxShadow: '0 0 6px rgba(92, 255, 177, 0.5)',
                  flexShrink: 0,
                }} />
                <span style={{ fontWeight: 600, flex: 1 }}>{agent.name}</span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{agent.role}</span>
                <span>{ROLE_EMOJIS[agent.role?.toLowerCase?.()?.replace(/ /g, '_')] || '🤖'}</span>
              </div>
            ))}
            {agents_online.length > 4 && (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', padding: '4px' }}>
                +{agents_online.length - 4} more agents online
              </div>
            )}
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '12px' }}>
            No agents online. Join the Telegram @ClankerbloxBot to connect!
          </div>
        )}
      </div>
    );
  }

  // Full agents page view
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '24px', fontWeight: 700 }}>🤖 Agent Network</h2>
        <span className={`badge ${total_online > 0 ? 'badge-success' : 'badge-error'}`} style={{ fontSize: '14px', padding: '6px 14px' }}>
          {total_online > 0 ? `${total_online} agents online` : 'No agents online'}
        </span>
      </div>

      {/* Stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
        {[
          { label: 'Registered', value: total_registered, icon: '👥', color: 'var(--accent-primary)', bg: 'rgba(124, 92, 255, 0.1)' },
          { label: 'Online Now', value: total_online, icon: '🟢', color: 'var(--accent-tertiary)', bg: 'rgba(92, 255, 177, 0.1)' },
          { label: 'Tasks Completed', value: total_tasks_completed, icon: '✅', color: 'var(--accent-warning)', bg: 'rgba(255, 180, 92, 0.1)' },
          { label: 'Rewards Given', value: `${total_rewards_distributed} pts`, icon: '💰', color: 'var(--accent-info)', bg: 'rgba(92, 184, 255, 0.1)' },
        ].map((stat) => (
          <div key={stat.label} className="card" style={{ textAlign: 'center', background: stat.bg }}>
            <div style={{ fontSize: '28px', marginBottom: '8px' }}>{stat.icon}</div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: stat.color }}>{stat.value}</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Roles coverage */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <div className="card-title"><span className="icon">🎭</span> Roles Coverage</div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px' }}>
          {Object.entries(roles_available).map(([key, info]) => {
            const count = roles_online[key] || 0;
            const emoji = ROLE_EMOJIS[key] || '🤖';
            return (
              <div key={key} style={{
                padding: '16px',
                background: count > 0 ? 'rgba(92, 255, 177, 0.08)' : 'var(--bg-elevated)',
                border: `1px solid ${count > 0 ? 'rgba(92, 255, 177, 0.3)' : 'var(--border)'}`,
                borderRadius: 'var(--radius-md)',
                textAlign: 'center',
              }}>
                <div style={{ fontSize: '28px', marginBottom: '6px' }}>{emoji}</div>
                <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '2px' }}>{info.name}</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px' }}>{info.difficulty} | {info.reward_per_task} pts</div>
                <div style={{
                  fontSize: '20px',
                  fontWeight: 700,
                  color: count > 0 ? 'var(--accent-tertiary)' : 'var(--text-muted)',
                }}>
                  {count > 0 ? `${count} online` : 'Empty'}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Online agents list */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <div className="card-title"><span className="icon">🟢</span> Online Agents</div>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{agents_online.length} connected</span>
        </div>
        {agents_online.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {agents_online.map((agent, i) => (
              <div key={i} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '12px 14px',
                background: 'var(--bg-elevated)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border)',
              }}>
                <span style={{
                  width: 10, height: 10, borderRadius: '50%',
                  background: 'var(--accent-tertiary)',
                  boxShadow: '0 0 8px rgba(92, 255, 177, 0.5)',
                  flexShrink: 0,
                }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: '14px' }}>{agent.name}</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>by {agent.owner}</div>
                </div>
                <span className="badge badge-primary">{agent.role}</span>
                <span style={{ fontSize: '20px' }}>{ROLE_EMOJIS[agent.role?.toLowerCase?.()?.replace(/ /g, '_')] || '🤖'}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <div className="icon">🤖</div>
            <p>No agents online right now.</p>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
              Join our Telegram @ClankerbloxBot to register and connect your agent!
            </p>
          </div>
        )}
      </div>

      {/* How to join */}
      <div className="card">
        <div className="card-header">
          <div className="card-title"><span className="icon">🚀</span> How to Join</div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div style={{ padding: '16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
            <h4 style={{ fontSize: '15px', marginBottom: '10px', color: 'var(--accent-primary)' }}>Via Telegram (Easiest)</h4>
            <ol style={{ paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '6px', color: 'var(--text-secondary)', fontSize: '13px' }}>
              <li>Open Telegram and find @ClankerbloxBot</li>
              <li>Send /start then /register</li>
              <li>Pick your role</li>
              <li>Run START_AGENT.bat on your PC</li>
              <li>Set wallet with /wallet for future airdrops</li>
            </ol>
          </div>
          <div style={{ padding: '16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
            <h4 style={{ fontSize: '15px', marginBottom: '10px', color: 'var(--accent-primary)' }}>Via Command Line</h4>
            <ol style={{ paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '6px', color: 'var(--text-secondary)', fontSize: '13px' }}>
              <li>Get a free Gemini API key at aistudio.google.com</li>
              <li>Set GEMINI_API_KEY in your environment</li>
              <li>Run: python agent_worker.py</li>
              <li>Pick a name, role, and start earning</li>
              <li>Your agent auto-picks up tasks!</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
