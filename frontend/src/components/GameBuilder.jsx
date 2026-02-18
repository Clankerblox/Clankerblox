import { useState } from 'react';
import useStore from '../store';

const GAME_TYPES = [
  { value: 'obby', label: 'Obby', icon: '🏃', desc: 'Obstacle course' },
  { value: 'tycoon', label: 'Tycoon', icon: '🏭', desc: 'Build & earn' },
  { value: 'simulator', label: 'Simulator', icon: '⚡', desc: 'Click & upgrade' },
  { value: 'survival', label: 'Survival', icon: '🏕️', desc: 'Stay alive' },
  { value: 'pvp', label: 'PvP', icon: '⚔️', desc: 'Player vs Player' },
  { value: 'roleplay', label: 'Roleplay', icon: '🎭', desc: 'Act & explore' },
  { value: 'minigame', label: 'Minigames', icon: '🎯', desc: 'Quick rounds' },
  { value: 'story', label: 'Story', icon: '📖', desc: 'Narrative driven' },
];

export default function GameBuilder() {
  const { buildCustomGame, buildAllGames, scanTrends, loading, pipelineStatus, trends, agentStats } = useStore();
  const [customName, setCustomName] = useState('');
  const [customType, setCustomType] = useState('obby');
  const [customDesc, setCustomDesc] = useState('');
  const isBusy = pipelineStatus !== 'idle' && pipelineStatus !== 'complete' && pipelineStatus !== 'error';
  const isBuildLoading = loading.build;
  const isScanLoading = loading.trends;
  const onlineAgents = agentStats?.total_online || 0;

  const handleCustomBuild = () => {
    if (!customName.trim() || !customDesc.trim()) return;
    buildCustomGame({
      name: customName,
      game_type: customType,
      description: customDesc,
    });
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '24px', fontWeight: 700 }}>🏗️ Game Builder</h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {onlineAgents > 0 && (
            <span className="badge badge-success" style={{ marginRight: '4px' }}>
              🤖 {onlineAgents} agents helping
            </span>
          )}
          <button
            className={`btn btn-primary ${isBuildLoading ? 'btn-loading' : ''}`}
            onClick={buildAllGames}
            disabled={isBusy || isBuildLoading || !trends}
          >
            {isBusy || isBuildLoading ? <><div className="spinner" /> Building...</> : '🚀 Build All 3 Games'}
          </button>
          <button
            className={`btn btn-secondary ${isScanLoading ? 'btn-loading' : ''}`}
            onClick={scanTrends}
            disabled={isScanLoading || isBusy || isBuildLoading}
          >
            {isScanLoading ? <><div className="spinner" /> Scanning...</> : '🔍 Scan First'}
          </button>
        </div>
      </div>

      {/* Auto Build Section */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <div className="card-title"><span className="icon">🤖</span> Auto Build from Trends</div>
        </div>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '14px' }}>
          Click "Build All 3 Games" to scan trends and automatically build 3 games. Or scan trends first and pick individual concepts from the Trends tab.
        </p>
        <div style={{
          display: 'flex',
          gap: '16px',
          padding: '16px',
          background: 'var(--bg-elevated)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border)',
        }}>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ fontSize: '28px', marginBottom: '4px' }}>1️⃣</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Scan Trends</div>
          </div>
          <div style={{ color: 'var(--text-muted)', alignSelf: 'center' }}>→</div>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ fontSize: '28px', marginBottom: '4px' }}>2️⃣</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Create Plans</div>
          </div>
          <div style={{ color: 'var(--text-muted)', alignSelf: 'center' }}>→</div>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ fontSize: '28px', marginBottom: '4px' }}>3️⃣</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Generate Code</div>
          </div>
          <div style={{ color: 'var(--text-muted)', alignSelf: 'center' }}>→</div>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ fontSize: '28px', marginBottom: '4px' }}>4️⃣</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Build .rbxlx</div>
          </div>
          <div style={{ color: 'var(--text-muted)', alignSelf: 'center' }}>→</div>
          <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ fontSize: '28px', marginBottom: '4px' }}>5️⃣</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Ready!</div>
          </div>
        </div>
      </div>

      {/* Custom Build Section */}
      <div className="card">
        <div className="card-header">
          <div className="card-title"><span className="icon">✏️</span> Custom Game</div>
        </div>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '14px' }}>
          Have a specific game idea? Describe it and Clankerblox will build it.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '6px', display: 'block' }}>
              Game Name
            </label>
            <input
              type="text"
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              placeholder="e.g., Speed Run Champions"
              style={{
                width: '100%',
                padding: '10px 14px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-primary)',
                fontSize: '14px',
                fontFamily: 'Space Grotesk, sans-serif',
                outline: 'none',
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '6px', display: 'block' }}>
              Game Type
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
              {GAME_TYPES.map((type) => (
                <button
                  key={type.value}
                  onClick={() => setCustomType(type.value)}
                  style={{
                    padding: '12px',
                    background: customType === type.value ? 'rgba(124, 92, 255, 0.15)' : 'var(--bg-elevated)',
                    border: `1px solid ${customType === type.value ? 'var(--accent-primary)' : 'var(--border)'}`,
                    borderRadius: 'var(--radius-sm)',
                    cursor: 'pointer',
                    textAlign: 'center',
                    color: 'var(--text-primary)',
                    fontFamily: 'Space Grotesk, sans-serif',
                  }}
                >
                  <div style={{ fontSize: '24px', marginBottom: '4px' }}>{type.icon}</div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>{type.label}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{type.desc}</div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <label style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '6px', display: 'block' }}>
              Game Description
            </label>
            <textarea
              value={customDesc}
              onChange={(e) => setCustomDesc(e.target.value)}
              placeholder="Describe what makes this game unique. What do players do? What's the core loop? What's fun about it?"
              rows={4}
              style={{
                width: '100%',
                padding: '10px 14px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-primary)',
                fontSize: '14px',
                fontFamily: 'Space Grotesk, sans-serif',
                outline: 'none',
                resize: 'vertical',
              }}
            />
          </div>

          <button
            className={`btn btn-primary ${isBuildLoading ? 'btn-loading' : ''}`}
            onClick={handleCustomBuild}
            disabled={isBusy || isBuildLoading || !customName.trim() || !customDesc.trim()}
            style={{ alignSelf: 'flex-start' }}
          >
            {isBuildLoading ? <><div className="spinner" /> Building...</> : '🏗️ Build Custom Game'}
          </button>
        </div>
      </div>
    </div>
  );
}
