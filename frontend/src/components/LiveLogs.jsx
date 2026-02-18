import { useEffect, useRef } from 'react';
import useStore from '../store';

const LEVEL_STYLES = {
  info: { color: 'var(--accent-info)', icon: 'ℹ️' },
  success: { color: 'var(--accent-tertiary)', icon: '✅' },
  warning: { color: 'var(--accent-warning)', icon: '⚠️' },
  error: { color: 'var(--accent-secondary)', icon: '❌' },
  critical: { color: '#ff3366', icon: '🔴' },
  step: { color: 'var(--accent-primary)', icon: '🔧' },
};

const EVENT_LABELS = {
  trend_scan: 'TRENDS',
  plan_create: 'PLAN',
  game_build: 'BUILD',
  game_complete: 'DONE',
  game_error: 'ERROR',
  system: 'SYSTEM',
  monetization: 'MONEY',
};

export default function LiveLogs({ compact = false }) {
  const { logs } = useStore();
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const displayLogs = compact ? logs.slice(-15) : logs.slice(-100);

  return (
    <div className="card" style={{ height: compact ? '320px' : undefined }}>
      <div className="card-header">
        <div className="card-title">
          <span className="icon">📡</span>
          Live Activity
          {logs.length > 0 && (
            <span style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: 'var(--accent-tertiary)',
              display: 'inline-block',
              animation: 'pulse-glow 2s infinite',
            }} />
          )}
        </div>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{logs.length} events</span>
      </div>

      <div
        ref={scrollRef}
        style={{
          maxHeight: compact ? '240px' : '600px',
          overflow: 'auto',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '12px',
          lineHeight: 1.8,
          background: '#0a0a18',
          borderRadius: 'var(--radius-sm)',
          padding: '12px',
          border: '1px solid var(--border)',
        }}
      >
        {displayLogs.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '20px' }}>
            Waiting for activity...
          </div>
        ) : (
          displayLogs.map((log, i) => {
            const style = LEVEL_STYLES[log.level] || LEVEL_STYLES.info;
            const eventLabel = EVENT_LABELS[log.event_type] || log.event_type;
            const time = log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '';

            return (
              <div key={i} style={{
                display: 'flex',
                gap: '8px',
                padding: '2px 0',
                borderBottom: '1px solid rgba(42, 42, 90, 0.3)',
              }}>
                <span style={{ color: 'var(--text-muted)', minWidth: '70px' }}>{time}</span>
                <span style={{ fontSize: '12px' }}>{style.icon}</span>
                <span style={{
                  color: 'var(--accent-primary)',
                  minWidth: '60px',
                  fontWeight: 600,
                  fontSize: '10px',
                  padding: '1px 4px',
                  background: 'rgba(124, 92, 255, 0.1)',
                  borderRadius: '3px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>{eventLabel}</span>
                <span style={{ color: style.color, flex: 1 }}>{log.message}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
