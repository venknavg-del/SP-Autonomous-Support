import React, { useState, useEffect, useRef } from 'react';
import './index.css';

const API_BASE = 'http://localhost:8000';

function App() {
  const [incidents, setIncidents] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [agentEvents, setAgentEvents] = useState([]);
  const [liveStatus, setLiveStatus] = useState('');
  const [metrics, setMetrics] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [approving, setApproving] = useState(false);
  const [activeTab, setActiveTab] = useState('incidents');
  const [config, setConfig] = useState({
    LLM_PROVIDER: 'copilot',
    ANTHROPIC_API_KEY: '',
    OPENAI_API_KEY: ''
  });
  const [savingEnv, setSavingEnv] = useState(false);
  const wsRef = useRef(null);

  // ── Fetch incidents list ────────────────────────────────────────
  const fetchIncidents = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/incidents`);
      const data = await res.json();
      setIncidents(data.incidents || []);
    } catch (e) {
      console.error('Failed to fetch incidents:', e);
    }
  };

  // ── Fetch metrics ───────────────────────────────────────────────
  const fetchMetrics = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/metrics`);
      setMetrics(await res.json());
    } catch (e) { /* silent */ }
  };

  // Auto-refresh incidents list
  useEffect(() => {
    fetchIncidents();
    fetchMetrics();
    const interval = setInterval(() => { fetchIncidents(); fetchMetrics(); }, 3000);
    return () => clearInterval(interval);
  }, []);

  // ── Fetch & Save Env Config ─────────────────────────────────────
  const fetchEnv = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/config/json`);
      const data = await res.json();
      setConfig(prev => ({ ...prev, ...data }));
    } catch (e) {
      console.error('Failed to fetch env:', e);
    }
  };

  const saveEnv = async () => {
    setSavingEnv(true);
    try {
      await fetch(`${API_BASE}/api/v1/config/json`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      alert('Configuration saved successfully! Note: Backend might need a restart if provider changed.');
    } catch (e) {
      console.error('Failed to save env:', e);
      alert('Failed to save configuration');
    }
    setSavingEnv(false);
  };

  useEffect(() => {
    if (activeTab === 'config') {
      fetchEnv();
    }
  }, [activeTab]);

  // ── Select an incident ──────────────────────────────────────────
  const selectIncident = async (id) => {
    setSelectedId(id);
    setAgentEvents([]);
    setLiveStatus('');

    // Close existing WebSocket
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }

    // Fetch full detail
    try {
      const res = await fetch(`${API_BASE}/api/v1/incidents/${id}`);
      const data = await res.json();
      setDetail(data);
      setAgentEvents(data.agent_events || []);
      setLiveStatus(data.status || '');
    } catch (e) {
      console.error('Failed to fetch detail:', e);
      return;
    }

    // Connect WebSocket for live updates
    const ws = new WebSocket(`ws://localhost:8000/ws/incidents/${id}`);
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'agent_event') {
        setAgentEvents(prev => {
          const exists = prev.some(e => e.timestamp === msg.data.timestamp && e.agent === msg.data.agent);
          return exists ? prev : [...prev, msg.data];
        });
      } else if (msg.type === 'status_update') {
        setLiveStatus(msg.data.status);
        setDetail(prev => prev ? { ...prev, status: msg.data.status } : prev);
        fetchIncidents(); // Refresh sidebar
      }
    };
    ws.onerror = () => console.error('WebSocket error');
    ws.onclose = () => console.log('WebSocket closed');
    wsRef.current = ws;
  };

  // Auto-select first incident
  useEffect(() => {
    if (incidents.length > 0 && !selectedId) {
      selectIncident(incidents[0].incident_id);
    }
  }, [incidents]);

  // ── Submit new incident ─────────────────────────────────────────
  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/incidents/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: 'dashboard',
          scenario_id: 'scenario1_payment_bug',
          raw_description: 'New incident submitted from dashboard'
        })
      });
      const data = await res.json();
      setTimeout(() => {
        fetchIncidents();
        selectIncident(data.incident_id);
      }, 500);
    } catch (e) {
      console.error('Submit failed:', e);
    }
    setSubmitting(false);
  };

  // ── Approve fix ─────────────────────────────────────────────────
  const handleApprove = async () => {
    if (!selectedId) return;
    setApproving(true);
    try {
      await fetch(`${API_BASE}/api/v1/incidents/${selectedId}/approve`, { method: 'POST' });
      fetchIncidents();
      selectIncident(selectedId);
    } catch (e) {
      console.error('Approve failed:', e);
    }
    setApproving(false);
  };

  const selected = detail;
  const statusClass = liveStatus?.includes('Resolved') ? 'resolved'
    : liveStatus?.includes('Approved') ? 'approved'
      : liveStatus?.includes('Pending') ? 'pending'
        : liveStatus?.includes('Failed') ? 'failed'
          : 'processing';

  return (
    <div className="dashboard-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo">
          <div className="logo-icon">▲</div>
          SP Agentic AI
        </div>
        <ul className="nav-menu">
          <li className={`nav-item ${activeTab === 'incidents' ? 'active' : ''}`} onClick={() => setActiveTab('incidents')}>
            <span>🔴</span> Active Incidents
          </li>
          <li className="nav-item"><span>📊</span> Telemetry Insights</li>
          <li className="nav-item"><span>📚</span> Knowledge Base RAG</li>
          <li className={`nav-item ${activeTab === 'config' ? 'active' : ''}`} onClick={() => setActiveTab('config')}>
            <span>⚙️</span> System Config
          </li>
        </ul>

        {/* Metrics Panel */}
        {metrics && (
          <div className="metrics-panel">
            <h4>System Metrics</h4>
            <div className="metric-row"><span>Total</span><strong>{metrics.total_incidents}</strong></div>
            <div className="metric-row"><span>Resolved</span><strong>{metrics.resolved_count}</strong></div>
            <div className="metric-row"><span>Auto-fixed</span><strong>{metrics.auto_remediated_count}</strong></div>
            <div className="metric-row"><span>Avg Time</span><strong>{metrics.avg_resolution_time_ms}ms</strong></div>
          </div>
        )}
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="header">
          <h1>Production Support Orchestrator</h1>
          <div className="header-actions">
            <button className="btn btn-submit" onClick={handleSubmit} disabled={submitting}>
              {submitting ? '⏳ Submitting...' : '+ New Incident'}
            </button>
            <div className="system-status">
              <div className="status-dot"></div>
              All MCP Agents Active
            </div>
          </div>
        </header>

        {activeTab === 'incidents' ? (
          <div className="dashboard-grid">
            {/* Column 1: Incident Queue */}
            <div className="card delay-1">
              <h2 className="card-title">🚨 Incident Queue</h2>
              <div className="incident-list">
                {incidents.length === 0 && (
                  <div className="empty-state">No incidents yet. Click "+ New Incident" to submit one.</div>
                )}
                {incidents.map(inc => (
                  <div
                    key={inc.incident_id}
                    className={`incident-item ${selectedId === inc.incident_id ? 'selected' : ''}`}
                    onClick={() => selectIncident(inc.incident_id)}
                  >
                    <div className="incident-header">
                      <span className="incident-id">{inc.incident_id}</span>
                      <span className={`tag ${inc.severity || 'processing'}`}>{inc.severity || '...'}</span>
                    </div>
                    <div className="incident-desc">{inc.desc || 'Processing...'}</div>
                    <div className={`incident-status ${inc.status?.toLowerCase().replace(/\s/g, '-') || ''}`}>
                      {inc.status || 'Processing'}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Column 2: AI Reasoning Chain */}
            <div className="card analysis-panel delay-2">
              <h2 className="card-title">🤖 AI Reasoning Chain</h2>

              {!selected && (
                <div className="empty-state">Select an incident to view the AI analysis</div>
              )}

              {selected && (
                <>
                  {/* Live Status Banner */}
                  <div className={`status-banner ${statusClass}`}>
                    {liveStatus || selected.status || 'Processing...'}
                    {selected.jira_ticket_key && (
                      <span className="jira-badge">JIRA: {selected.jira_ticket_key}</span>
                    )}
                  </div>

                  {/* Agent Trace */}
                  <div className="agent-trace">
                    {agentEvents.map((step, idx) => (
                      <div className="agent-step" key={idx}>
                        <div className="step-icon">✓</div>
                        <div className="step-content">
                          <h4>{step.agent} <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>via {step.source}</span></h4>
                          <p>{step.action}</p>
                        </div>
                      </div>
                    ))}
                    {agentEvents.length === 0 && liveStatus !== 'Failed' && (
                      <div className="loading-dots">
                        <span>⏳ Agents analyzing incident</span>
                        <div className="dots"><span></span><span></span><span></span></div>
                      </div>
                    )}
                  </div>

                  {/* Resolution Box */}
                  {selected.suggested_resolution && (
                    <div className="action-box delay-3">
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.75rem' }}>
                        <span className="confidence">{(selected.confidence_score * 100).toFixed(0)}% Confidence</span>
                        {selected.jira_ticket_key && (
                          <span className="jira-tag">Linked: {selected.jira_ticket_key}</span>
                        )}
                      </div>
                      <p className="proposed-fix">
                        <strong>Suggested Resolution:</strong><br />
                        {selected.suggested_resolution}
                      </p>
                      {selected.root_cause_analysis && (
                        <p className="rca-detail" style={{ marginBottom: '1rem' }}>
                          <strong>Root Cause:</strong> {selected.root_cause_analysis}
                        </p>
                      )}

                      {selected.workaround && (
                        <div className="info-card workaround-card">
                          <strong>💡 Temporary Workaround:</strong>
                          <p>{selected.workaround}</p>
                        </div>
                      )}

                      {selected.recommended_runbook && (
                        <div className="info-card runbook-card">
                          <strong>📚 Recommended Runbook:</strong>
                          <p>{selected.recommended_runbook}</p>
                        </div>
                      )}

                      {selected.jira_context?.fields && (
                        <div className="info-card jira-context-card">
                          <strong>🎫 Jira Context [{selected.jira_ticket_key}]:</strong>
                          <p className="margin-top-sm"><strong>Summary:</strong> {selected.jira_context.fields.summary}</p>
                          <p><strong>Assignee:</strong> {selected.jira_context.fields.assignee?.displayName || 'Unassigned'}</p>
                        </div>
                      )}
                      <div className="btn-group">
                        {selected.requires_human_approval && !selected.human_approved && (
                          <button className="btn btn-approve" onClick={handleApprove} disabled={approving}>
                            {approving ? 'Approving...' : 'Approve & Execute Fix'}
                          </button>
                        )}
                        {selected.human_approved && (
                          <button className="btn btn-approved" disabled>✅ Approved</button>
                        )}
                        <button className="btn btn-escalate">Escalate L2</button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ) : (
          <div className="card delay-1 config-panel" style={{ flex: 1 }}>
            <h2 className="card-title">⚙️ Backend Environment Configuration (.env)</h2>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '2rem' }}>
              Configure your LLM AI provider and API keys directly. Changes are saved to the backend `.env` file.
            </p>

            <div className="config-form">
              {/* LLM Provider Selection */}
              <div className="form-group">
                <label className="form-label">LLM Provider (Reasoning Engine)</label>
                <div className="radio-group">
                  <label className="radio-label">
                    <input
                      type="radio"
                      name="llm_provider"
                      value="copilot"
                      checked={config.LLM_PROVIDER === 'copilot'}
                      onChange={(e) => setConfig({ ...config, LLM_PROVIDER: e.target.value })}
                    />
                    GitHub Copilot (VSCode Proxy)
                  </label>
                  <label className="radio-label">
                    <input
                      type="radio"
                      name="llm_provider"
                      value="anthropic"
                      checked={config.LLM_PROVIDER === 'anthropic'}
                      onChange={(e) => setConfig({ ...config, LLM_PROVIDER: e.target.value })}
                    />
                    Anthropic (Claude)
                  </label>
                  <label className="radio-label">
                    <input
                      type="radio"
                      name="llm_provider"
                      value="openai"
                      checked={config.LLM_PROVIDER === 'openai'}
                      onChange={(e) => setConfig({ ...config, LLM_PROVIDER: e.target.value })}
                    />
                    OpenAI (ChatGPT)
                  </label>
                </div>
              </div>

              {/* API Keys */}
              <div className="form-group" style={{ marginTop: '1rem' }}>
                <label className="form-label">Anthropic API Key</label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="sk-ant-api03-..."
                  value={config.ANTHROPIC_API_KEY || ''}
                  onChange={(e) => setConfig({ ...config, ANTHROPIC_API_KEY: e.target.value })}
                  disabled={config.LLM_PROVIDER !== 'anthropic'}
                />
              </div>

              <div className="form-group">
                <label className="form-label">OpenAI API Key</label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="sk-proj-..."
                  value={config.OPENAI_API_KEY || ''}
                  onChange={(e) => setConfig({ ...config, OPENAI_API_KEY: e.target.value })}
                  disabled={config.LLM_PROVIDER !== 'openai'}
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-start', marginTop: '2.5rem' }}>
              <button
                className="btn btn-approve"
                onClick={saveEnv}
                disabled={savingEnv}
                style={{ padding: '0.75rem 2rem', fontSize: '1rem' }}
              >
                {savingEnv ? 'Saving...' : 'Save Configuration'}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
