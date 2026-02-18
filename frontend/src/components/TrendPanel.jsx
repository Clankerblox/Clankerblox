import { useState } from 'react';
import useStore from '../store';

export default function TrendPanel({ compact = false }) {
  const { trends, scanTrends, loading, buildGame, pipelineStatus } = useStore();
  const [expandedConcept, setExpandedConcept] = useState(null);

  const analysis = trends?.analysis || {};
  const concepts = analysis.game_concepts || [];
  const insights = analysis.trend_insights || [];
  const isBusy = pipelineStatus !== 'idle' && pipelineStatus !== 'complete' && pipelineStatus !== 'error';
  const isBuildLoading = loading.build;
  const isScanLoading = loading.trends;

  if (compact) {
    return (
      <div className="card">
        <div className="card-header">
          <div className="card-title"><span className="icon">🔥</span> Latest Trends</div>
          <button
            className={`btn btn-sm btn-primary ${isScanLoading ? 'btn-loading' : ''}`}
            onClick={scanTrends}
            disabled={isScanLoading || isBusy || isBuildLoading}
          >
            {isScanLoading ? <><div className="spinner" /> Scanning...</> : '🔍 Scan'}
          </button>
        </div>
        {concepts.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '13px', padding: '12px 0' }}>
            No trends yet. Click Scan to analyze.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {concepts.slice(0, 3).map((c, i) => (
              <div key={i} style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 12px',
                background: 'var(--bg-elevated)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border)',
              }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '14px' }}>{c.name}</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{c.game_type} • Viral: {c.viral_score}/10</div>
                </div>
                <button
                  className={`btn btn-sm btn-success ${loading.buildingSingle?.[i] ? 'btn-loading' : ''}`}
                  onClick={() => buildGame(i)}
                  disabled={isBusy || isBuildLoading}
                >
                  {loading.buildingSingle?.[i] ? 'Building...' : 'Build'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '24px', fontWeight: 700 }}>🔥 Trend Analysis</h2>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className={`btn btn-primary ${isScanLoading ? 'btn-loading' : ''}`}
            onClick={scanTrends}
            disabled={isScanLoading || isBusy || isBuildLoading}
          >
            {isScanLoading ? <><div className="spinner" /> Scanning...</> : '🔍 Scan Trends Now'}
          </button>
        </div>
      </div>

      {analysis.analysis_summary && (
        <div className="card" style={{ marginBottom: '20px' }}>
          <div className="card-title" style={{ marginBottom: '12px' }}>
            <span className="icon">📋</span> Analysis Summary
          </div>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>{analysis.analysis_summary}</p>
          {insights.length > 0 && (
            <div style={{ marginTop: '16px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {insights.map((insight, i) => (
                <span key={i} className="badge badge-info">💡 {insight}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {concepts.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {concepts.map((concept, i) => (
            <div key={i} className="card" style={{
              cursor: 'pointer',
              border: expandedConcept === i ? '1px solid var(--accent-primary)' : undefined,
              boxShadow: expandedConcept === i ? 'var(--shadow-glow)' : undefined,
            }}
              onClick={() => setExpandedConcept(expandedConcept === i ? null : i)}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                    <span style={{
                      fontSize: '24px',
                      fontWeight: 800,
                      background: 'var(--gradient-primary)',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                    }}>#{i + 1}</span>
                    <h3 style={{ fontSize: '20px', fontWeight: 700 }}>{concept.name}</h3>
                    <span className="badge badge-primary">{concept.game_type}</span>
                    <span className="badge badge-info">{concept.complexity}</span>
                  </div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '12px' }}>{concept.tagline}</p>

                  <div style={{ display: 'flex', gap: '24px', marginBottom: '8px' }}>
                    <div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>Viral Score</div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontWeight: 700, color: concept.viral_score >= 7 ? 'var(--accent-tertiary)' : 'var(--accent-warning)' }}>
                          {concept.viral_score}/10
                        </span>
                        <div className="score-bar" style={{ width: '80px' }}>
                          <div
                            className={`score-bar-fill ${concept.viral_score >= 7 ? 'high' : concept.viral_score >= 5 ? 'medium' : 'low'}`}
                            style={{ width: `${concept.viral_score * 10}%` }}
                          />
                        </div>
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>Revenue Score</div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontWeight: 700, color: concept.revenue_score >= 7 ? 'var(--accent-tertiary)' : 'var(--accent-warning)' }}>
                          {concept.revenue_score}/10
                        </span>
                        <div className="score-bar" style={{ width: '80px' }}>
                          <div
                            className={`score-bar-fill ${concept.revenue_score >= 7 ? 'high' : concept.revenue_score >= 5 ? 'medium' : 'low'}`}
                            style={{ width: `${concept.revenue_score * 10}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <button
                  className={`btn btn-primary ${loading.buildingSingle?.[i] ? 'btn-loading' : ''}`}
                  onClick={(e) => { e.stopPropagation(); buildGame(i); }}
                  disabled={isBusy || isBuildLoading}
                >
                  {loading.buildingSingle?.[i] ? <><div className="spinner" /> Building...</> : '🏗️ Build This Game'}
                </button>
              </div>

              {expandedConcept === i && (
                <div style={{
                  marginTop: '16px',
                  paddingTop: '16px',
                  borderTop: '1px solid var(--border)',
                  animation: 'slide-in 0.3s ease-out',
                }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    <div>
                      <h4 style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>Trend Connection</h4>
                      <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>{concept.trend_connection}</p>
                    </div>
                    <div>
                      <h4 style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>Core Loop</h4>
                      <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>{concept.core_loop}</p>
                    </div>
                    {concept.hooks?.length > 0 && (
                      <div>
                        <h4 style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>Retention Hooks</h4>
                        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          {concept.hooks.map((h, j) => (
                            <li key={j} style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>🪝 {h}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {concept.monetization?.length > 0 && (
                      <div>
                        <h4 style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>Monetization</h4>
                        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          {concept.monetization.map((m, j) => (
                            <li key={j} style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                              💰 {m.item} - <b style={{ color: 'var(--accent-warning)' }}>{m.robux_price}R$</b> ({m.type})
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {concepts.length === 0 && !loading.trends && (
        <div className="empty-state">
          <div className="icon">🔍</div>
          <p>No trend data yet. Click "Scan Trends Now" to analyze what's hot on Roblox!</p>
        </div>
      )}
    </div>
  );
}
