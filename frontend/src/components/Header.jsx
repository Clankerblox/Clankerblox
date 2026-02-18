import useStore from '../store';

export default function Header() {
  const { theme, toggleTheme, wsConnected } = useStore();

  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '16px 24px',
      background: 'var(--bg-secondary)',
      borderBottom: '1px solid var(--border)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          fontSize: '28px',
          fontWeight: 700,
          background: 'var(--gradient-primary)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          letterSpacing: '-0.5px',
        }}>
          Clankerblox
        </div>
        <span style={{
          fontSize: '11px',
          padding: '3px 8px',
          background: 'rgba(124, 92, 255, 0.15)',
          color: 'var(--accent-primary)',
          borderRadius: '6px',
          fontWeight: 600,
        }}>
          AI Game Builder
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '12px',
          color: wsConnected ? 'var(--accent-tertiary)' : 'var(--accent-secondary)',
        }}>
          <div style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: wsConnected ? 'var(--accent-tertiary)' : 'var(--accent-secondary)',
            boxShadow: wsConnected ? '0 0 8px rgba(92, 255, 177, 0.5)' : 'none',
          }} />
          {wsConnected ? 'Live' : 'Disconnected'}
        </div>

        <button
          onClick={toggleTheme}
          style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '8px 12px',
            cursor: 'pointer',
            fontSize: '16px',
            color: 'var(--text-primary)',
          }}
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      </div>
    </header>
  );
}
