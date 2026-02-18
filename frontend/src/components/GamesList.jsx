import { useEffect, useState } from 'react';
import useStore from '../store';

export default function GamesList() {
  const { games, fetchGames, fetchGameDetail, selectedGame, loading } = useStore();
  const [viewingGame, setViewingGame] = useState(null);
  const [activeScript, setActiveScript] = useState(null);

  useEffect(() => {
    fetchGames();
  }, []);

  const handleViewGame = async (gameId) => {
    const detail = await fetchGameDetail(gameId);
    if (detail) {
      setViewingGame(detail);
      const scriptNames = Object.keys(detail.scripts || {});
      if (scriptNames.length > 0) setActiveScript(scriptNames[0]);
    }
  };

  if (viewingGame) {
    const plan = viewingGame.plan || {};
    const scripts = viewingGame.scripts || {};
    const scriptNames = Object.keys(scripts);

    return (
      <div>
        <button className="btn btn-secondary" onClick={() => setViewingGame(null)} style={{ marginBottom: '16px' }}>
          ← Back to Games
        </button>

        <div className="card" style={{ marginBottom: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <h2 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '8px' }}>{plan.name || 'Game'}</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '12px' }}>{plan.tagline}</p>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <span className="badge badge-primary">{plan.game_type}</span>
                <span className="badge badge-success">Ready to Publish</span>
                {plan.seo_keywords?.map((kw, i) => (
                  <span key={i} className="badge badge-info">{kw}</span>
                ))}
              </div>
            </div>
            <a
              href={`/api/games/${plan.game_id}/download`}
              className="btn btn-success"
              style={{ textDecoration: 'none', whiteSpace: 'nowrap' }}
              download
            >
              📥 Download .rbxlx
            </a>
          </div>
        </div>

        {/* Roblox Page Info */}
        <div className="card" style={{ marginBottom: '20px' }}>
          <div className="card-title" style={{ marginBottom: '12px' }}>
            <span className="icon">📋</span> Roblox Page Copy
          </div>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Title</label>
            <div style={{
              padding: '8px 12px',
              background: 'var(--bg-elevated)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border)',
              fontSize: '14px',
              marginTop: '4px',
            }}>{plan.roblox_title}</div>
          </div>
          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Description</label>
            <div style={{
              padding: '8px 12px',
              background: 'var(--bg-elevated)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border)',
              fontSize: '13px',
              marginTop: '4px',
              whiteSpace: 'pre-wrap',
              lineHeight: 1.6,
            }}>{plan.roblox_description}</div>
          </div>
        </div>

        {/* Monetization */}
        {plan.monetization && (
          <div className="card" style={{ marginBottom: '20px' }}>
            <div className="card-title" style={{ marginBottom: '12px' }}>
              <span className="icon">💰</span> Monetization
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              {(plan.monetization.game_passes || []).map((gp, i) => (
                <div key={i} style={{
                  padding: '12px',
                  background: 'var(--bg-elevated)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border)',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 600, fontSize: '14px' }}>{gp.name}</span>
                    <span style={{ fontWeight: 700, color: 'var(--accent-warning)' }}>R$ {gp.robux_price}</span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{gp.description}</div>
                  <span className="badge badge-primary" style={{ marginTop: '8px' }}>Game Pass</span>
                </div>
              ))}
              {(plan.monetization.dev_products || []).map((dp, i) => (
                <div key={i} style={{
                  padding: '12px',
                  background: 'var(--bg-elevated)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border)',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 600, fontSize: '14px' }}>{dp.name}</span>
                    <span style={{ fontWeight: 700, color: 'var(--accent-warning)' }}>R$ {dp.robux_price}</span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{dp.description}</div>
                  <span className="badge badge-warning" style={{ marginTop: '8px' }}>Dev Product</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Scripts */}
        {scriptNames.length > 0 && (
          <div className="card">
            <div className="card-title" style={{ marginBottom: '12px' }}>
              <span className="icon">📜</span> Scripts ({scriptNames.length})
            </div>
            <div style={{ display: 'flex', gap: '4px', marginBottom: '12px', flexWrap: 'wrap' }}>
              {scriptNames.map((name) => (
                <button
                  key={name}
                  className={`btn btn-sm ${activeScript === name ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveScript(name)}
                >
                  {name}
                </button>
              ))}
            </div>
            {activeScript && (
              <pre style={{
                background: '#0d0d2b',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                padding: '16px',
                overflow: 'auto',
                maxHeight: '400px',
                fontSize: '12px',
                fontFamily: 'JetBrains Mono, monospace',
                color: 'var(--accent-tertiary)',
                lineHeight: 1.6,
              }}>
                {scripts[activeScript]}
              </pre>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '24px', fontWeight: 700 }}>🎮 Built Games</h2>
        <button className="btn btn-secondary" onClick={fetchGames}>🔄 Refresh</button>
      </div>

      {games.length === 0 ? (
        <div className="empty-state">
          <div className="icon">🎮</div>
          <p>No games built yet. Go to the Builder tab or Trends tab to create your first game!</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
          {games.map((game, i) => (
            <div key={i} className="card" style={{ cursor: 'pointer' }} onClick={() => handleViewGame(game.game_id)}>
              <div style={{
                width: '100%',
                height: '120px',
                background: `linear-gradient(135deg, hsl(${(i * 60) % 360}, 70%, 25%) 0%, hsl(${(i * 60 + 60) % 360}, 70%, 15%) 100%)`,
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '12px',
                fontSize: '48px',
              }}>
                {{'obby': '🏃', 'tycoon': '🏭', 'simulator': '⚡', 'survival': '🏕️', 'pvp': '⚔️', 'roleplay': '🎭', 'minigame': '🎯', 'story': '📖'}[game.game_type] || '🎮'}
              </div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '4px' }}>{game.name}</h3>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>{game.tagline}</p>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                <span className="badge badge-primary">{game.game_type}</span>
                <span className="badge badge-success">{game.scripts?.length || 0} scripts</span>
                <span className="badge badge-info">{game.parts_count || 0} parts</span>
              </div>
              <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--text-muted)' }}>
                {new Date(game.created_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
