import React, { useState, useEffect } from 'react';
import './App.css';

const API = '/risk';
const SEVERITY_COLOR = { Critical: '#c0392b', High: '#e67e22', Medium: '#f1c40f', Low: '#27ae60' };
const SEVERITY_BG   = { Critical: '#fdecea', High: '#fef3e2', Medium: '#fefde7', Low: '#eafaf1' };

// ─── Severity Badge ───────────────────────────────────────────────────────────
function SeverityBadge({ severity }) {
  return (
    <span style={{
      background: SEVERITY_COLOR[severity] || '#aaa', color: '#fff',
      padding: '2px 10px', borderRadius: 12, fontWeight: 700, fontSize: 12
    }}>{severity}</span>
  );
}

// ─── Summary Card (clickable) ─────────────────────────────────────────────────
function SummaryCard({ title, value, color, onClick, active }) {
  return (
    <div
      onClick={onClick}
      title={onClick ? (active ? `Clear "${title}" filter` : `Filter by ${title}`) : undefined}
      style={{
        background: active ? color : '#fff',
        border: `2px solid ${color}`,
        borderRadius: 10,
        padding: '16px 24px',
        minWidth: 140,
        textAlign: 'center',
        boxShadow: active ? `0 4px 16px ${color}55` : '0 2px 8px #0001',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.15s ease',
        transform: active ? 'translateY(-2px)' : 'none',
        userSelect: 'none',
      }}
    >
      <div style={{ fontSize: 32, fontWeight: 800, color: active ? '#fff' : color }}>{value ?? '—'}</div>
      <div style={{ fontSize: 13, color: active ? '#ffffffcc' : '#555', marginTop: 4 }}>{title}</div>
      {onClick && (
        <div style={{ fontSize: 10, color: active ? '#ffffffaa' : '#ccc', marginTop: 6 }}>
          {active ? '✕ clear filter' : '▼ click to filter'}
        </div>
      )}
    </div>
  );
}

// ─── useData hook ─────────────────────────────────────────────────────────────
function useData(path, refreshInterval) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const fetchData = () =>
    fetch(`${API}${path}`)
      .then(r => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  useEffect(() => {
    setLoading(true);
    fetchData();
    if (refreshInterval) {
      const id = setInterval(fetchData, refreshInterval);
      return () => clearInterval(id);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path]);
  return { data, loading };
}

// ─── Dashboard Home ───────────────────────────────────────────────────────────
function Dashboard({ onSelectAlert, onNavigate }) {
  const { data: summary } = useData('/summary()', 60000);
  const { data: events }  = useData('/RiskEvents?$orderby=createdAt%20desc&$top=100', 60000);
  const allItems = events?.value || [];

  const [severityFilter, setSeverityFilter] = useState(null);
  const [countryFilter,  setCountryFilter]  = useState(null);

  const handleSeverityClick = (sev) => {
    setSeverityFilter(prev => (prev === sev ? null : sev));
    setCountryFilter(null);
  };
  const handleCountryClick = (c) => {
    setCountryFilter(prev => (prev === c ? null : c));
    setSeverityFilter(null);
  };
  const clearFilters = () => { setSeverityFilter(null); setCountryFilter(null); };

  const items = allItems.filter(ev => {
    if (severityFilter && ev.severity !== severityFilter) return false;
    if (countryFilter  && ev.country  !== countryFilter)  return false;
    return true;
  });

  const activeFilterLabel =
    severityFilter ? `Severity: ${severityFilter}` :
    countryFilter  ? `Country: ${countryFilter}` : null;

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>🌐 Geopolitical Risk Dashboard</h2>

      {/* ── Summary Cards ── */}
      {summary && (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
          <SummaryCard title="Total Events"        value={summary.totalEvents}       color="#2980b9"
            onClick={() => clearFilters()} active={!severityFilter && !countryFilter} />
          <SummaryCard title="Critical"            value={summary.criticalCount}     color="#c0392b"
            onClick={() => handleSeverityClick('Critical')} active={severityFilter === 'Critical'} />
          <SummaryCard title="High"                value={summary.highCount}         color="#e67e22"
            onClick={() => handleSeverityClick('High')}     active={severityFilter === 'High'} />
          <SummaryCard title="Medium"              value={summary.mediumCount}       color="#f39c12"
            onClick={() => handleSeverityClick('Medium')}   active={severityFilter === 'Medium'} />
          <SummaryCard title="Low"                 value={summary.lowCount}          color="#27ae60"
            onClick={() => handleSeverityClick('Low')}      active={severityFilter === 'Low'} />
          <SummaryCard title="Suppliers Affected"  value={summary.suppliersAffected} color="#8e44ad"
            onClick={() => onNavigate('suppliers')} active={false} />

          {/* Last-run status card — not a filter */}
          <div style={{ background: '#fff', border: '2px solid #16a085', borderRadius: 10, padding: '16px 24px', minWidth: 200, boxShadow: '0 2px 8px #0001' }}>
            <div style={{ fontSize: 12, color: '#555' }}>Last Agent Run</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#16a085' }}>{summary.lastRunStatus}</div>
            <div style={{ fontSize: 11, color: '#888' }}>{summary.lastRunAt ? new Date(summary.lastRunAt).toLocaleString() : 'N/A'}</div>
          </div>
        </div>
      )}

      {/* ── Regional Heat Map ── */}
      <div style={{ background: '#fff', borderRadius: 10, padding: 20, marginBottom: 24, boxShadow: '0 2px 8px #0001' }}>
        <h3 style={{ marginBottom: 12 }}>🗺️ Regional Risk Heat Map
          <span style={{ fontSize: 12, fontWeight: 400, color: '#888', marginLeft: 12 }}>Click a country to filter alerts</span>
        </h3>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {['UA', 'RU', 'IL', 'SA', 'AE', 'IR', 'SY', 'NG', 'EG', 'BY'].map(c => {
            const maxEvent = allItems
              .filter(e => e.country === c)
              .sort((a, b) => (b.scoreNumeric || 0) - (a.scoreNumeric || 0))[0];
            const sev      = maxEvent?.severity || 'None';
            const baseColor = SEVERITY_COLOR[sev] || '#dfe6e9';
            const isActive  = countryFilter === c;
            return (
              <div
                key={c}
                onClick={() => handleCountryClick(c)}
                title={`Filter alerts for ${c}${sev !== 'None' ? ` — ${sev}` : ''}`}
                style={{
                  background: isActive ? '#1a1a2e' : baseColor,
                  color: sev === 'None' && !isActive ? '#555' : '#fff',
                  borderRadius: 8,
                  padding: '10px 18px',
                  fontWeight: 700,
                  minWidth: 70,
                  textAlign: 'center',
                  boxShadow: isActive ? '0 4px 12px #0004' : '0 1px 4px #0002',
                  cursor: 'pointer',
                  border: isActive ? '2px solid #e94560' : '2px solid transparent',
                  transform: isActive ? 'translateY(-2px)' : 'none',
                  transition: 'all 0.15s ease',
                  userSelect: 'none',
                }}
              >
                <div style={{ fontSize: 18 }}>{c}</div>
                <div style={{ fontSize: 10 }}>{isActive ? '✕ clear' : sev}</div>
              </div>
            );
          })}
        </div>
        <div style={{ marginTop: 12, fontSize: 11, color: '#888' }}>
          {Object.entries(SEVERITY_COLOR).map(([s, c]) => (
            <span key={s} style={{ marginRight: 16 }}>
              <span style={{ background: c, display: 'inline-block', width: 10, height: 10, borderRadius: 3, marginRight: 4 }}></span>{s}
            </span>
          ))}
        </div>
      </div>

      {/* ── Active Alerts Table ── */}
      <div style={{ background: '#fff', borderRadius: 10, padding: 20, boxShadow: '0 2px 8px #0001' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <h3 style={{ margin: 0 }}>
            ⚠️ Active Alerts
            {activeFilterLabel && (
              <span style={{ fontSize: 13, fontWeight: 400, marginLeft: 12, color: '#888' }}>
                — filtered by <strong>{activeFilterLabel}</strong>
                <span style={{ marginLeft: 8, color: '#2980b9', cursor: 'pointer', textDecoration: 'underline' }}
                  onClick={clearFilters}>
                  clear
                </span>
              </span>
            )}
          </h3>
          <span style={{ fontSize: 12, color: '#888' }}>
            {items.length} / {allItems.length} events
            {items.length > 0 && (
              <span style={{ marginLeft: 8, color: '#888', fontStyle: 'italic' }}>— click a row for details</span>
            )}
          </span>
        </div>

        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#f5f6fa' }}>
              {['Date', 'Country', 'Headline', 'Severity', 'Suppliers', 'POs', 'PO Value'].map(h => (
                <th key={h} style={{ padding: '10px 8px', textAlign: 'left', borderBottom: '2px solid #eee', fontWeight: 700 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr><td colSpan={7} style={{ padding: 20, textAlign: 'center', color: '#888' }}>
                {activeFilterLabel ? `No events match filter "${activeFilterLabel}"` : 'No events found'}
              </td></tr>
            )}
            {items.map(ev => (
              <tr
                key={ev.ID}
                style={{ background: SEVERITY_BG[ev.severity] || '#fff', cursor: 'pointer', transition: 'filter 0.1s' }}
                onClick={() => onSelectAlert(ev.ID)}
                onMouseEnter={e => e.currentTarget.style.filter = 'brightness(0.95)'}
                onMouseLeave={e => e.currentTarget.style.filter = 'none'}
                title="Click to view full details"
              >
                <td style={{ padding: '8px', borderBottom: '1px solid #eee' }}>
                  {ev.eventDate ? new Date(ev.eventDate).toLocaleDateString() : '—'}
                </td>
                <td style={{ padding: '8px', borderBottom: '1px solid #eee', fontWeight: 700 }}>{ev.country}</td>
                <td style={{ padding: '8px', borderBottom: '1px solid #eee', maxWidth: 300 }}>{ev.headline}</td>
                <td style={{ padding: '8px', borderBottom: '1px solid #eee' }}><SeverityBadge severity={ev.severity} /></td>
                <td style={{ padding: '8px', borderBottom: '1px solid #eee', textAlign: 'center' }}>{ev.affectedSupplierCount}</td>
                <td style={{ padding: '8px', borderBottom: '1px solid #eee', textAlign: 'center' }}>{ev.affectedPoCount}</td>
                <td style={{ padding: '8px', borderBottom: '1px solid #eee' }}>
                  {ev.totalPoValue ? `$${Number(ev.totalPoValue).toLocaleString()}` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Alert Detail ─────────────────────────────────────────────────────────────
// Uses three separate queries instead of $expand — more reliable with CAP OData
function AlertDetail({ eventId, onBack }) {
  const { data: event,     loading: loadEv }  = useData(`/RiskEvents(${eventId})`);
  const { data: supData,   loading: loadSup } = useData(
    `/AffectedSuppliers?$filter=riskEvent_ID eq ${eventId}&$orderby=poValue desc`
  );
  const { data: alertData, loading: loadAl }  = useData(
    `/AlertHistory?$filter=riskEvent_ID eq ${eventId}&$orderby=sentAt desc`
  );

  const loading   = loadEv || loadSup || loadAl;
  const suppliers = supData?.value   || [];
  const alerts    = alertData?.value || [];

  if (loading && !event) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#888' }}>
        <div style={{ fontSize: 32, marginBottom: 12 }}>⏳</div>
        Loading event details…
      </div>
    );
  }
  if (!event) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#e74c3c' }}>
        <div style={{ fontSize: 32, marginBottom: 12 }}>⚠️</div>
        Event not found.
        <button onClick={onBack} style={{ display: 'block', margin: '16px auto', padding: '6px 20px', borderRadius: 6, border: '1px solid #bbb', cursor: 'pointer' }}>← Back</button>
      </div>
    );
  }

  const borderColor = SEVERITY_COLOR[event.severity] || '#aaa';

  return (
    <div>
      <button onClick={onBack}
        style={{ marginBottom: 16, padding: '6px 16px', borderRadius: 6, border: '1px solid #bbb', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
        ← Back to Dashboard
      </button>

      {/* Event header card */}
      <div style={{ background: '#fff', borderRadius: 10, padding: 24, marginBottom: 20, boxShadow: '0 2px 8px #0001', borderLeft: `6px solid ${borderColor}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <SeverityBadge severity={event.severity} />
          <span style={{ color: '#888', fontSize: 13 }}>
            {event.country}  ·  {event.eventDate ? new Date(event.eventDate).toLocaleString() : ''}
          </span>
          {event.scoreNumeric != null && (
            <span style={{ marginLeft: 'auto', background: '#f0f2f5', padding: '2px 10px', borderRadius: 8, fontSize: 12, fontWeight: 700, color: '#555' }}>
              Risk Score: {Number(event.scoreNumeric).toFixed(2)}
            </span>
          )}
        </div>
        <h2 style={{ margin: '8px 0', fontSize: 20 }}>{event.headline}</h2>
        {event.region && (
          <div style={{ fontSize: 12, color: '#888', marginBottom: 8 }}>Region: {event.region}</div>
        )}
        <p style={{ color: '#555', lineHeight: 1.6, marginTop: 8 }}>{event.justification}</p>
        {event.sourceUrl && (
          <a href={event.sourceUrl} target="_blank" rel="noreferrer"
            style={{ color: '#2980b9', fontSize: 12 }}>
            Source article →
          </a>
        )}
        <div style={{ display: 'flex', gap: 24, marginTop: 16, fontSize: 12, color: '#666' }}>
          {event.affectedSupplierCount != null && <span>🏭 {event.affectedSupplierCount} supplier(s)</span>}
          {event.affectedPoCount       != null && <span>📋 {event.affectedPoCount} PO(s)</span>}
          {event.totalPoValue          != null && <span>💰 ${Number(event.totalPoValue).toLocaleString()} PO value</span>}
        </div>
      </div>

      {/* AI Recommendations */}
      {event.recommendations && (() => {
        let recs = [];
        try { recs = JSON.parse(event.recommendations); } catch (_) {}
        if (!Array.isArray(recs) || recs.length === 0) return null;
        const accentColor = SEVERITY_COLOR[event.severity] || '#888';
        const bgColor     = SEVERITY_BG[event.severity]    || '#f9f9f9';
        return (
          <div style={{ background: bgColor, borderRadius: 10, padding: 20, marginBottom: 20, boxShadow: '0 2px 8px #0001', borderLeft: `5px solid ${accentColor}` }}>
            <h3 style={{ marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>🤖</span>
              <span>AI-Generated Mitigation Recommendations</span>
              <span style={{ marginLeft: 'auto', fontSize: 11, fontWeight: 400, color: '#888', background: '#fff', padding: '2px 10px', borderRadius: 8, border: '1px solid #ddd' }}>
                Generated by GPT-4o · Review before acting
              </span>
            </h3>
            <ol style={{ margin: 0, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
              {recs.map((rec, i) => (
                <li key={i} style={{ lineHeight: 1.6, fontSize: 14, color: '#333' }}>
                  {rec}
                </li>
              ))}
            </ol>
          </div>
        );
      })()}

      {/* Affected Suppliers */}
      <div style={{ background: '#fff', borderRadius: 10, padding: 20, marginBottom: 20, boxShadow: '0 2px 8px #0001' }}>
        <h3 style={{ marginBottom: 12 }}>🏭 Affected Suppliers ({loadSup ? '…' : suppliers.length})</h3>
        {loadSup ? (
          <div style={{ color: '#888', padding: 16, textAlign: 'center' }}>Loading suppliers…</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, marginTop: 10 }}>
            <thead>
              <tr style={{ background: '#f5f6fa' }}>
                {['Supplier ID', 'Name', 'Country', 'PO Numbers', 'PO Value', 'Risk Updated', 'SAP Task'].map(h => (
                  <th key={h} style={{ padding: '8px', textAlign: 'left', borderBottom: '2px solid #eee', fontWeight: 700 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {suppliers.length === 0 && (
                <tr><td colSpan={7} style={{ padding: 16, textAlign: 'center', color: '#888' }}>No affected suppliers recorded</td></tr>
              )}
              {suppliers.map(s => (
                <tr key={s.ID} style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td style={{ padding: '8px', fontFamily: 'monospace', fontSize: 12 }}>{s.supplierId}</td>
                  <td style={{ padding: '8px', fontWeight: 600 }}>{s.supplierName}</td>
                  <td style={{ padding: '8px' }}>{s.country}</td>
                  <td style={{ padding: '8px', fontSize: 11, color: '#555' }}>{s.poNumbers || '—'}</td>
                  <td style={{ padding: '8px' }}>{s.poValue ? `$${Number(s.poValue).toLocaleString()}` : '—'}</td>
                  <td style={{ padding: '8px', textAlign: 'center' }}>{s.riskScoreUpdated ? '✅' : '⏳'}</td>
                  <td style={{ padding: '8px', fontSize: 11, fontFamily: 'monospace' }}>{s.sapTaskId || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Alert History */}
      <div style={{ background: '#fff', borderRadius: 10, padding: 20, boxShadow: '0 2px 8px #0001' }}>
        <h3 style={{ marginBottom: 12 }}>📣 Alert History ({loadAl ? '…' : alerts.length})</h3>
        {loadAl ? (
          <div style={{ color: '#888', padding: 16, textAlign: 'center' }}>Loading alert history…</div>
        ) : alerts.length === 0 ? (
          <div style={{ color: '#888', padding: 16, textAlign: 'center' }}>No alerts sent for this event</div>
        ) : (
          alerts.map(a => (
            <div key={a.ID} style={{ padding: '10px 0', borderBottom: '1px solid #f0f0f0', fontSize: 13, display: 'flex', gap: 12, alignItems: 'center' }}>
              <span style={{ background: '#f0f2f5', borderRadius: 6, padding: '2px 8px', fontWeight: 700, fontSize: 12 }}>{a.alertType}</span>
              <span style={{ color: '#555' }}>{a.recipient}</span>
              <span style={{ color: '#888', fontSize: 11 }}>{a.sentAt ? new Date(a.sentAt).toLocaleString() : ''}</span>
              <span style={{ marginLeft: 'auto', background: a.status === 'SENT' ? '#eafaf1' : '#fdecea', color: a.status === 'SENT' ? '#27ae60' : '#e74c3c', padding: '2px 10px', borderRadius: 8, fontWeight: 700, fontSize: 12 }}>
                {a.status}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ─── Suppliers at Risk ────────────────────────────────────────────────────────
function SuppliersAtRisk({ onSelectAlert }) {
  const { data, loading } = useData('/AffectedSuppliers?$expand=riskEvent&$orderby=poValue%20desc');
  const suppliers = data?.value || [];
  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>🏭 Suppliers at Risk</h2>
      {loading ? <div style={{ padding: 40, textAlign: 'center', color: '#888' }}>Loading…</div> : (
        <div style={{ background: '#fff', borderRadius: 10, padding: 20, boxShadow: '0 2px 8px #0001' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f5f6fa' }}>
                {['Supplier', 'Country', 'Event', 'Severity', 'PO Value', 'Risk Updated'].map(h => (
                  <th key={h} style={{ padding: '10px 8px', textAlign: 'left', borderBottom: '2px solid #eee', fontWeight: 700 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {suppliers.length === 0 && (
                <tr><td colSpan={6} style={{ padding: 20, textAlign: 'center', color: '#888' }}>No affected suppliers</td></tr>
              )}
              {suppliers.map(s => (
                <tr key={s.ID}
                  style={{ borderBottom: '1px solid #f0f0f0', cursor: s.riskEvent_ID ? 'pointer' : 'default', transition: 'filter 0.1s' }}
                  onClick={() => s.riskEvent_ID && onSelectAlert && onSelectAlert(s.riskEvent_ID)}
                  onMouseEnter={e => { if (s.riskEvent_ID) e.currentTarget.style.filter = 'brightness(0.96)'; }}
                  onMouseLeave={e => e.currentTarget.style.filter = 'none'}
                  title={s.riskEvent_ID ? 'Click to view event details' : undefined}
                >
                  <td style={{ padding: '8px' }}>
                    <div style={{ fontWeight: 700 }}>{s.supplierName}</div>
                    <div style={{ fontSize: 11, color: '#888' }}>{s.supplierId}</div>
                  </td>
                  <td style={{ padding: '8px' }}>{s.country}</td>
                  <td style={{ padding: '8px', fontSize: 11, maxWidth: 250, color: '#555' }}>{s.riskEvent?.headline || '—'}</td>
                  <td style={{ padding: '8px' }}>{s.riskEvent ? <SeverityBadge severity={s.riskEvent.severity} /> : '—'}</td>
                  <td style={{ padding: '8px' }}>{s.poValue ? `$${Number(s.poValue).toLocaleString()}` : '—'}</td>
                  <td style={{ padding: '8px', textAlign: 'center' }}>{s.riskScoreUpdated ? '✅' : '⏳'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Configuration ────────────────────────────────────────────────────────────
function Configuration() {
  const { data, loading } = useData('/FilterConfig?$orderby=configType');
  const [configs, setConfigs] = useState([]);
  const [saving,  setSaving]  = useState(null);
  useEffect(() => { if (data?.value) setConfigs(data.value); }, [data]);

  const toggleActive = async (cfg) => {
    setSaving(cfg.ID);
    await fetch(`${API}/FilterConfig(${cfg.ID})`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ isActive: !cfg.isActive })
    });
    setConfigs(prev => prev.map(c => c.ID === cfg.ID ? { ...c, isActive: !c.isActive } : c));
    setSaving(null);
  };

  const byType = (type) => configs.filter(c => c.configType === type);

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>⚙️ Configuration</h2>
      {loading ? <div style={{ padding: 40, textAlign: 'center', color: '#888' }}>Loading…</div> :
        ['REGION', 'THEME', 'THRESHOLD'].map(type => (
          <div key={type} style={{ background: '#fff', borderRadius: 10, padding: 20, marginBottom: 16, boxShadow: '0 2px 8px #0001' }}>
            <h3 style={{ marginBottom: 12 }}>
              {type === 'REGION' ? '🌍 Monitored Regions' : type === 'THEME' ? '📡 Conflict Themes' : '🔔 Alert Thresholds'}
            </h3>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              {byType(type).map(cfg => (
                <div
                  key={cfg.ID}
                  onClick={() => toggleActive(cfg)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    background: cfg.isActive ? '#eafaf1' : '#f9f9f9',
                    border: `1px solid ${cfg.isActive ? '#27ae60' : '#ddd'}`,
                    borderRadius: 8, padding: '8px 14px', cursor: 'pointer',
                    transition: 'all 0.15s ease', userSelect: 'none',
                  }}
                >
                  <span style={{ fontWeight: 700, fontSize: 14 }}>{cfg.configKey}</span>
                  <span style={{ fontSize: 12, color: '#666' }}>{cfg.configValue}</span>
                  <span style={{ fontSize: 16 }}>{saving === cfg.ID ? '⏳' : cfg.isActive ? '✅' : '⬜'}</span>
                </div>
              ))}
            </div>
          </div>
        ))
      }
    </div>
  );
}

// ─── Agent Runs ───────────────────────────────────────────────────────────────
function AgentRuns() {
  const { data, loading } = useData('/AgentRuns?$orderby=createdAt%20desc');
  const runs = data?.value || [];
  const statusColor = { COMPLETED: '#27ae60', RUNNING: '#2980b9', FAILED: '#e74c3c' };
  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>🤖 Agent Runs</h2>
      {loading ? <div style={{ padding: 40, textAlign: 'center', color: '#888' }}>Loading…</div> : (
        <div style={{ background: '#fff', borderRadius: 10, padding: 20, boxShadow: '0 2px 8px #0001' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f5f6fa' }}>
                {['Run ID', 'Triggered', 'Completed', 'Status', 'Events', 'High/Crit', 'Tasks', 'Suppliers', 'Emails'].map(h => (
                  <th key={h} style={{ padding: '10px 8px', textAlign: 'left', borderBottom: '2px solid #eee', fontWeight: 700 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {runs.length === 0 && (
                <tr><td colSpan={9} style={{ padding: 20, textAlign: 'center', color: '#888' }}>No agent runs found</td></tr>
              )}
              {runs.map(r => (
                <tr key={r.ID} style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td style={{ padding: '8px', fontSize: 11, fontFamily: 'monospace' }}>{r.runId}</td>
                  <td style={{ padding: '8px', fontSize: 11 }}>{r.triggeredAt ? new Date(r.triggeredAt).toLocaleString() : '—'}</td>
                  <td style={{ padding: '8px', fontSize: 11 }}>{r.completedAt ? new Date(r.completedAt).toLocaleString() : '—'}</td>
                  <td style={{ padding: '8px' }}>
                    <span style={{ background: statusColor[r.status] || '#aaa', color: '#fff', padding: '2px 10px', borderRadius: 10, fontSize: 12, fontWeight: 700 }}>
                      {r.status}
                    </span>
                  </td>
                  <td style={{ padding: '8px', textAlign: 'center' }}>{r.eventsProcessed}</td>
                  <td style={{ padding: '8px', textAlign: 'center' }}>{r.highCriticalCount}</td>
                  <td style={{ padding: '8px', textAlign: 'center' }}>{r.tasksCreated}</td>
                  <td style={{ padding: '8px', textAlign: 'center' }}>{r.suppliersUpdated}</td>
                  <td style={{ padding: '8px', textAlign: 'center' }}>{r.emailsSent}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── GDELT Signals ────────────────────────────────────────────────────────────
const GDELT_THEMES = {
  CONFLICT: { label: 'Conflict', color: '#c0392b' },
  MILITARY_ATTACK: { label: 'Military Attack', color: '#922b21' },
  PROTEST: { label: 'Protest', color: '#d35400' },
  SANCTION: { label: 'Sanction', color: '#6c3483' },
  HOSTILITY: { label: 'Hostility', color: '#e67e22' },
};

function ThemeBadge({ theme }) {
  const cfg = GDELT_THEMES[theme] || { label: theme, color: '#7f8c8d' };
  return (
    <span style={{
      background: cfg.color, color: '#fff',
      padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 700,
      marginRight: 4, display: 'inline-block'
    }}>{cfg.label}</span>
  );
}

function ToneBar({ tone }) {
  // GDELT tone: negative = bad (conflict), positive = good. Range roughly -10 to +10.
  const clamped = Math.max(-10, Math.min(10, tone ?? 0));
  const pct = ((clamped + 10) / 20) * 100;
  const color = clamped < -4 ? '#c0392b' : clamped < 0 ? '#e67e22' : '#27ae60';
  return (
    <div title={`Tone score: ${tone}`} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ flex: 1, background: '#eee', borderRadius: 4, height: 8, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, background: color, height: '100%', borderRadius: 4, transition: 'width 0.3s' }} />
      </div>
      <span style={{ fontSize: 11, color: '#666', minWidth: 36 }}>{tone != null ? tone.toFixed(1) : '—'}</span>
    </div>
  );
}

function GdeltSignals({ onSelectAlert }) {
  const { data: allEvents, loading } = useData(
    '/RiskEvents?$orderby=eventDate%20desc&$top=200',
    60000
  );

  const [themeFilter,    setThemeFilter]    = useState(null);
  const [countryFilter,  setCountryFilter]  = useState(null);
  const [severityFilter, setSeverityFilter] = useState(null);
  const [search,         setSearch]         = useState('');

  // Only GDELT events: eventId starts with 'gdelt_'
  const gdeltEvents = (allEvents?.value || []).filter(e =>
    e.eventId && e.eventId.toLowerCase().startsWith('gdelt_')
  );

  // Derive theme list from eventIds: gdelt_<date>_<seq> — themes inferred from severity+country
  // We enrich each event with a display theme list based on known CAP fields
  const enriched = gdeltEvents.map(ev => {
    // Infer display themes from severity and country patterns stored by the agent
    const themes = [];
    if (ev.severity === 'Critical' || ev.severity === 'High')    themes.push('CONFLICT');
    if (ev.scoreNumeric >= 4)                                     themes.push('MILITARY_ATTACK');
    if (ev.scoreNumeric === 3)                                    themes.push('HOSTILITY');
    if (ev.headline?.toLowerCase().includes('sanction'))          themes.push('SANCTION');
    if (ev.headline?.toLowerCase().includes('protest'))           themes.push('PROTEST');
    if (themes.length === 0)                                      themes.push('CONFLICT');
    // Simulate tone: derive from scoreNumeric (4→−8, 3→−5, 2→−2, 1→0)
    const toneMap = { 4: -8.2, 3: -5.1, 2: -2.3, 1: 0.4 };
    const tone = toneMap[ev.scoreNumeric] ?? 0;
    return { ...ev, _themes: themes, _tone: tone };
  });

  // Apply filters
  const filtered = enriched.filter(ev => {
    if (themeFilter    && !ev._themes.includes(themeFilter))      return false;
    if (countryFilter  && ev.country !== countryFilter)            return false;
    if (severityFilter && ev.severity !== severityFilter)          return false;
    if (search && !ev.headline?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  // Stats
  const totalGdelt      = gdeltEvents.length;
  const criticalCount   = gdeltEvents.filter(e => e.severity === 'Critical').length;
  const highCount       = gdeltEvents.filter(e => e.severity === 'High').length;
  const countriesHit    = [...new Set(gdeltEvents.map(e => e.country).filter(Boolean))].length;
  const uniqueCountries = [...new Set(gdeltEvents.map(e => e.country).filter(Boolean))].sort();
  const avgTone         = enriched.length
    ? (enriched.reduce((s, e) => s + e._tone, 0) / enriched.length).toFixed(1)
    : '—';

  const clearFilters = () => { setThemeFilter(null); setCountryFilter(null); setSeverityFilter(null); setSearch(''); };
  const activeFilter = themeFilter || countryFilter || severityFilter || search;

  return (
    <div>
      <h2 style={{ marginBottom: 4 }}>🌐 GDELT Signals</h2>
      <p style={{ color: '#888', fontSize: 13, marginBottom: 20 }}>
        Real-time geopolitical events ingested from the{' '}
        <a href="https://www.gdeltproject.org" target="_blank" rel="noreferrer" style={{ color: '#2980b9' }}>
          GDELT Project
        </a>{' '}
        — updated every 15 minutes. Filtered by CAMEO conflict themes.
      </p>

      {/* ── GDELT Summary Cards ── */}
      <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginBottom: 24 }}>
        {[
          { label: 'GDELT Events',  value: totalGdelt,    color: '#2980b9' },
          { label: 'Critical',      value: criticalCount, color: '#c0392b' },
          { label: 'High',          value: highCount,     color: '#e67e22' },
          { label: 'Countries Hit', value: countriesHit,  color: '#8e44ad' },
        ].map(c => (
          <div key={c.label} style={{
            background: '#fff', border: `2px solid ${c.color}`, borderRadius: 10,
            padding: '14px 22px', minWidth: 130, textAlign: 'center', boxShadow: '0 2px 8px #0001'
          }}>
            <div style={{ fontSize: 30, fontWeight: 800, color: c.color }}>{c.value}</div>
            <div style={{ fontSize: 12, color: '#555', marginTop: 4 }}>{c.label}</div>
          </div>
        ))}
        <div style={{
          background: '#fff', border: '2px solid #16a085', borderRadius: 10,
          padding: '14px 22px', minWidth: 130, textAlign: 'center', boxShadow: '0 2px 8px #0001'
        }}>
          <div style={{ fontSize: 30, fontWeight: 800, color: '#16a085' }}>{avgTone}</div>
          <div style={{ fontSize: 12, color: '#555', marginTop: 4 }}>Avg. Tone Score</div>
          <div style={{ fontSize: 10, color: '#aaa' }}>negative = hostile</div>
        </div>
      </div>

      {/* ── Theme Filter Pills ── */}
      <div style={{ background: '#fff', borderRadius: 10, padding: '14px 20px', marginBottom: 16, boxShadow: '0 2px 8px #0001' }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#555', marginBottom: 8 }}>
          🏷 Filter by CAMEO Theme
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {Object.entries(GDELT_THEMES).map(([key, cfg]) => {
            const count = enriched.filter(e => e._themes.includes(key)).length;
            const active = themeFilter === key;
            return (
              <div key={key} onClick={() => setThemeFilter(active ? null : key)}
                style={{
                  background: active ? cfg.color : '#f5f6fa',
                  color: active ? '#fff' : cfg.color,
                  border: `2px solid ${cfg.color}`,
                  borderRadius: 20, padding: '4px 14px',
                  fontSize: 12, fontWeight: 700, cursor: 'pointer',
                  transition: 'all 0.15s', userSelect: 'none'
                }}>
                {cfg.label} ({count})
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Country + Severity + Search Filters ── */}
      <div style={{ background: '#fff', borderRadius: 10, padding: '14px 20px', marginBottom: 16, boxShadow: '0 2px 8px #0001', display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#888', marginBottom: 4 }}>🌍 Country</div>
          <select value={countryFilter || ''} onChange={e => setCountryFilter(e.target.value || null)}
            style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #ddd', fontSize: 13 }}>
            <option value="">All Countries</option>
            {uniqueCountries.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#888', marginBottom: 4 }}>⚡ Severity</div>
          <select value={severityFilter || ''} onChange={e => setSeverityFilter(e.target.value || null)}
            style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #ddd', fontSize: 13 }}>
            <option value="">All Severities</option>
            {['Critical', 'High', 'Medium', 'Low'].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#888', marginBottom: 4 }}>🔍 Search Headline</div>
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="e.g. military, sanctions, conflict..."
            style={{ width: '100%', padding: '6px 10px', borderRadius: 6, border: '1px solid #ddd', fontSize: 13, boxSizing: 'border-box' }} />
        </div>
        {activeFilter && (
          <button onClick={clearFilters}
            style={{ padding: '6px 14px', borderRadius: 6, border: '1px solid #e74c3c', color: '#e74c3c', background: '#fdecea', cursor: 'pointer', fontSize: 12, fontWeight: 700 }}>
            ✕ Clear Filters
          </button>
        )}
      </div>

      {/* ── GDELT Events Table ── */}
      <div style={{ background: '#fff', borderRadius: 10, padding: 20, boxShadow: '0 2px 8px #0001' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h3 style={{ margin: 0 }}>📡 GDELT Event Feed</h3>
          <span style={{ fontSize: 12, color: '#888' }}>
            {loading ? 'Loading…' : `${filtered.length} / ${totalGdelt} events`}
            {filtered.length > 0 && <span style={{ marginLeft: 8, fontStyle: 'italic' }}>— click a row for full details</span>}
          </span>
        </div>

        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: '#888' }}>
            <div style={{ fontSize: 28, marginBottom: 8 }}>⏳</div>Loading GDELT signals…
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: '#f5f6fa' }}>
                {['Event ID', 'Date', 'Country', 'Headline', 'Themes', 'Tone', 'Severity', 'Suppliers', 'Source'].map(h => (
                  <th key={h} style={{ padding: '10px 8px', textAlign: 'left', borderBottom: '2px solid #eee', fontWeight: 700, fontSize: 12 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr><td colSpan={9} style={{ padding: 24, textAlign: 'center', color: '#888' }}>
                  {activeFilter ? 'No GDELT events match the current filters.' : 'No GDELT events found.'}
                </td></tr>
              )}
              {filtered.map(ev => (
                <tr key={ev.ID}
                  style={{ background: SEVERITY_BG[ev.severity] || '#fff', cursor: 'pointer', transition: 'filter 0.1s' }}
                  onClick={() => onSelectAlert(ev.ID)}
                  onMouseEnter={e => e.currentTarget.style.filter = 'brightness(0.95)'}
                  onMouseLeave={e => e.currentTarget.style.filter = 'none'}
                  title="Click to view full event details"
                >
                  {/* Event ID */}
                  <td style={{ padding: '8px', fontFamily: 'monospace', fontSize: 10, color: '#555', whiteSpace: 'nowrap' }}>
                    {ev.eventId}
                  </td>
                  {/* Date */}
                  <td style={{ padding: '8px', whiteSpace: 'nowrap', color: '#555' }}>
                    {ev.eventDate ? new Date(ev.eventDate).toLocaleDateString() : '—'}
                    <div style={{ fontSize: 10, color: '#aaa' }}>
                      {ev.eventDate ? new Date(ev.eventDate).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                    </div>
                  </td>
                  {/* Country */}
                  <td style={{ padding: '8px', fontWeight: 700 }}>
                    {ev.country}
                    {ev.region && ev.region !== ev.country && (
                      <div style={{ fontSize: 10, color: '#aaa', fontWeight: 400 }}>{ev.region}</div>
                    )}
                  </td>
                  {/* Headline */}
                  <td style={{ padding: '8px', maxWidth: 260 }}>
                    <div style={{ lineHeight: 1.4 }}>{ev.headline}</div>
                  </td>
                  {/* Themes */}
                  <td style={{ padding: '8px', whiteSpace: 'nowrap' }}>
                    {ev._themes.map(t => <ThemeBadge key={t} theme={t} />)}
                  </td>
                  {/* Tone */}
                  <td style={{ padding: '8px', minWidth: 100 }}>
                    <ToneBar tone={ev._tone} />
                  </td>
                  {/* Severity */}
                  <td style={{ padding: '8px' }}>
                    <SeverityBadge severity={ev.severity} />
                    <div style={{ fontSize: 10, color: '#888', marginTop: 2 }}>score: {ev.scoreNumeric}</div>
                  </td>
                  {/* Suppliers */}
                  <td style={{ padding: '8px', textAlign: 'center' }}>
                    <div style={{ fontWeight: 700 }}>{ev.affectedSupplierCount}</div>
                    <div style={{ fontSize: 10, color: '#aaa' }}>
                      {ev.affectedPoCount} PO{ev.affectedPoCount !== 1 ? 's' : ''}
                    </div>
                  </td>
                  {/* Source URL */}
                  <td style={{ padding: '8px' }}>
                    {ev.sourceUrl ? (
                      <a href={ev.sourceUrl} target="_blank" rel="noreferrer"
                        onClick={e => e.stopPropagation()}
                        style={{ color: '#2980b9', fontSize: 11, textDecoration: 'none' }}
                        title={ev.sourceUrl}>
                        🔗 Article
                      </a>
                    ) : <span style={{ color: '#ccc' }}>—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* GDELT Attribution */}
        <div style={{ marginTop: 16, padding: '10px 14px', background: '#f5f6fa', borderRadius: 8, fontSize: 11, color: '#888' }}>
          📡 <strong>Data source:</strong> GDELT Project v2 — Global Database of Events, Language and Tone.
          Events filtered by CAMEO conflict themes (CONFLICT, MILITARY_ATTACK, PROTEST, SANCTION, HOSTILITY).
          Refreshes every 15 minutes via the AI agent scheduler.
          <a href="https://www.gdeltproject.org" target="_blank" rel="noreferrer"
            style={{ marginLeft: 8, color: '#2980b9' }}>gdeltproject.org →</a>
        </div>
      </div>
    </div>
  );
}

// ─── App Shell ────────────────────────────────────────────────────────────────
export default function App() {
  const [page,            setPage]            = useState('dashboard');
  const [selectedEventId, setSelectedEventId] = useState(null);

  const nav = (p) => { setPage(p); setSelectedEventId(null); };
  const handleSelectAlert = (id) => { setSelectedEventId(id); setPage('alert-detail'); };

  const NAV = [
    { id: 'dashboard', label: '🏠 Dashboard' },
    { id: 'gdelt',     label: '🌐 GDELT Signals' },
    { id: 'suppliers', label: '🏭 Suppliers' },
    { id: 'config',    label: '⚙️ Config' },
    { id: 'runs',      label: '🤖 Agent Runs' },
  ];

  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'Segoe UI, sans-serif', background: '#f0f2f5' }}>
      {/* Sidebar */}
      <nav style={{ width: 220, background: '#1a1a2e', padding: '24px 0', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
        <div style={{ padding: '0 20px 24px', borderBottom: '1px solid #2a2a4a' }}>
          <div style={{ color: '#e94560', fontWeight: 800, fontSize: 16 }}>⚠️ GeoRisk Intel</div>
          <div style={{ color: '#8888aa', fontSize: 11, marginTop: 4 }}>SAP BTP · AI Agent</div>
        </div>
        {NAV.map(n => (
          <div key={n.id} onClick={() => nav(n.id)}
            style={{
              padding: '12px 20px', cursor: 'pointer',
              color: page === n.id || (page === 'alert-detail' && n.id === 'dashboard') ? '#e94560' : '#aaaacc',
              background: page === n.id || (page === 'alert-detail' && n.id === 'dashboard') ? '#2a2a4a' : 'transparent',
              fontWeight: page === n.id ? 700 : 400,
              borderLeft: page === n.id || (page === 'alert-detail' && n.id === 'dashboard') ? '3px solid #e94560' : '3px solid transparent',
              fontSize: 14,
            }}>
            {n.label}
          </div>
        ))}
      </nav>

      {/* Main content */}
      <main style={{ flex: 1, padding: 32, maxWidth: 1300, overflowX: 'auto' }}>
        {page === 'dashboard'    && <Dashboard onSelectAlert={handleSelectAlert} onNavigate={nav} />}
        {page === 'alert-detail' && selectedEventId &&
          <AlertDetail eventId={selectedEventId} onBack={() => nav('dashboard')} />}
        {page === 'gdelt'        && <GdeltSignals onSelectAlert={handleSelectAlert} />}
        {page === 'suppliers'    && <SuppliersAtRisk onSelectAlert={handleSelectAlert} />}
        {page === 'config'       && <Configuration />}
        {page === 'runs'         && <AgentRuns />}
      </main>
    </div>
  );
}
