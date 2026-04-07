import { useState, useEffect, useCallback } from 'react'
import {
  AlertTriangle, CheckCircle, Clock, Loader2, Plus, X,
  Bell, BellOff, ShieldCheck, Eye, RefreshCw, Send,
} from 'lucide-react'
import { alertsFetch } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import Sidebar from '../components/layout/Sidebar'
import Header from '../components/layout/Header'

/* ── Types (mirror backend Pydantic models) ── */

type ConfiguredStatus = 'pending' | 'approved' | 'rejected'
type TriggeredStatus  = 'active' | 'acknowledged' | 'resolved' | 'dismissed'
type Severity         = 'Low' | 'Medium' | 'High' | 'Critical'
type Metric           = 'Air Quality' | 'Temperature' | 'Humidity' | 'Noise Levels' | 'UV Levels'
type Visibility       = 'Internal' | 'Public Facing'
type Condition        = 'ABOVE' | 'BELOW'

interface ConfiguredAlert {
  alert_id:            string
  operator_id:         string
  alert_name:          string
  environmental_metric: Metric
  geographic_area:     string
  threshold_value:     number
  threshold_value_max: number | null
  condition:           Condition
  timeframe_minutes:   number
  alert_visibility:    Visibility
  description:         string | null
  is_active:           boolean
  status:              ConfiguredStatus
  created_at:          string | null
  approved_by:         string | null
  approval_date:       string | null
}

interface TriggeredAlert {
  triggered_alert_id: string
  alert_id:           string
  triggered_value:    number
  sensor_id:          string | null
  region:             string | null
  alert_severity:     Severity | null
  is_public:          boolean
  status:             TriggeredStatus
  triggered_at:       string | null
  acknowledged_at:    string | null
  is_false_alarm:     boolean
  // joined from parent
  alert_name?:        string
  environmental_metric?: Metric
}

interface RuleForm {
  alert_name:           string
  environmental_metric: Metric
  geographic_area:      string
  threshold_value:      string
  condition:            Condition
  timeframe_minutes:    string
  alert_visibility:     Visibility
  description:          string
}

const EMPTY_FORM: RuleForm = {
  alert_name: '', environmental_metric: 'Air Quality',
  geographic_area: '', threshold_value: '', condition: 'ABOVE',
  timeframe_minutes: '15', alert_visibility: 'Internal', description: '',
}

const METRICS: Metric[] = ['Air Quality', 'Temperature', 'Humidity', 'Noise Levels', 'UV Levels']

/* ── Status styling ── */

const TRIGGERED_CFG: Record<TriggeredStatus, { badge: string; row: string; Icon: typeof AlertTriangle; label: string }> = {
  active:       { badge: 'bg-red-500/15 text-red-400 border border-red-500/30',       row: 'border-l-2 border-l-red-500/60',    Icon: AlertTriangle, label: 'ACTIVE'       },
  acknowledged: { badge: 'bg-sky-500/15 text-sky-400 border border-sky-500/30',       row: 'border-l-2 border-l-sky-500/40',    Icon: Loader2,       label: 'ACKNOWLEDGED' },
  resolved:     { badge: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30', row: 'border-l-2 border-l-emerald-500/30', Icon: CheckCircle,   label: 'RESOLVED'     },
  dismissed:    { badge: 'bg-zinc-700 text-zinc-400 border border-zinc-600',           row: 'border-l-2 border-l-zinc-700',      Icon: X,             label: 'DISMISSED'    },
}

const SEV_COLOR: Record<Severity, string> = {
  Low:      'text-zinc-400',
  Medium:   'text-amber-400',
  High:     'text-orange-400',
  Critical: 'text-red-400',
}

const RULE_STATUS_CFG: Record<ConfiguredStatus, { badge: string; label: string }> = {
  pending:  { badge: 'bg-amber-500/10 text-amber-400 border border-amber-500/30',   label: 'PENDING'  },
  approved: { badge: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30', label: 'APPROVED' },
  rejected: { badge: 'bg-red-500/10 text-red-400 border border-red-500/30',         label: 'REJECTED' },
}

type Tab = 'triggered' | 'rules' | 'pending'

export default function Alerts() {
  const { profile, role } = useAuth()
  const isAdmin = role === 'System Administrator'

  const [tab, setTab]                   = useState<Tab>('triggered')
  const [triggered, setTriggered]       = useState<TriggeredAlert[]>([])
  const [rules, setRules]               = useState<ConfiguredAlert[]>([])
  const [pending, setPending]           = useState<ConfiguredAlert[]>([])
  const [loading, setLoading]           = useState(false)
  const [error, setError]               = useState('')
  const [viewAlert, setViewAlert]       = useState<TriggeredAlert | null>(null)
  const [showRule, setShowRule]         = useState(false)
  const [editRule, setEditRule]         = useState<ConfiguredAlert | null>(null)
  const [ruleForm, setRuleForm]         = useState<RuleForm>(EMPTY_FORM)
  const [ruleLoading, setRuleLoading]   = useState(false)
  const [ruleError, setRuleError]       = useState('')
  const [rejectTarget, setRejectTarget] = useState<ConfiguredAlert | null>(null)

  /* ── Data fetching ── */

  const fetchTriggered = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res  = await alertsFetch('/api/v1/alerts/database/records?limit=200')
      const data = await res.json()
      if (!res.ok) { setError(data?.detail ?? 'Failed to load alerts'); setLoading(false); return }
      const flat: TriggeredAlert[] = []
      for (const record of data.records ?? []) {
        for (const t of record.triggered ?? []) {
          flat.push({ ...t, alert_name: record.alert.alert_name, environmental_metric: record.alert.environmental_metric })
        }
      }
      flat.sort((a, b) => new Date(b.triggered_at ?? 0).getTime() - new Date(a.triggered_at ?? 0).getTime())
      setTriggered(flat)
    } catch { setError('Could not reach alerts service (port 8004). Is Docker running?') }
    setLoading(false)
  }, [])

  const fetchRules = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res  = await alertsFetch('/api/v1/alerts/rules')
      const data = await res.json()
      if (!res.ok) { setError(data?.detail ?? 'Failed to load rules'); setLoading(false); return }
      setRules(Array.isArray(data) ? data : [])
    } catch { setError('Could not reach alerts service (port 8004). Is Docker running?') }
    setLoading(false)
  }, [])

  const fetchPending = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res  = await alertsFetch('/api/v1/alerts/approval/pending')
      const data = await res.json()
      if (!res.ok) { setError(data?.detail ?? 'Failed to load pending approvals'); setLoading(false); return }
      setPending(Array.isArray(data) ? data : [])
    } catch { setError('Could not reach alerts service (port 8004). Is Docker running?') }
    setLoading(false)
  }, [])

  useEffect(() => {
    if (tab === 'triggered') fetchTriggered()
    else if (tab === 'rules') fetchRules()
    else if (tab === 'pending') fetchPending()
  }, [tab, fetchTriggered, fetchRules, fetchPending])

  /* ── Actions ── */

  async function acknowledge(t: TriggeredAlert) {
    if (!profile) return
    const res  = await alertsFetch(`/api/v1/alerts/triggered/${t.triggered_alert_id}/acknowledge`, {
      method: 'POST',
      body: JSON.stringify({ operator_id: profile.accountinfo_id }),
    })
    if (res.ok) {
      setTriggered(prev => prev.map(x => x.triggered_alert_id === t.triggered_alert_id ? { ...x, status: 'acknowledged' } : x))
      if (viewAlert?.triggered_alert_id === t.triggered_alert_id) setViewAlert({ ...viewAlert, status: 'acknowledged' })
    }
  }

  async function submitForApproval(rule: ConfiguredAlert) {
    const res = await alertsFetch(`/api/v1/alerts/rules/${rule.alert_id}/submit`, { method: 'POST' })
    if (res.ok) fetchRules()
  }

  async function approveRule(rule: ConfiguredAlert) {
    if (!profile) return
    const res = await alertsFetch(`/api/v1/alerts/rules/${rule.alert_id}/approve?approver_id=${profile.accountinfo_id}`, { method: 'POST' })
    if (res.ok) fetchPending()
  }

  async function rejectRule(rule: ConfiguredAlert) {
    const res = await alertsFetch(`/api/v1/alerts/rules/${rule.alert_id}/reject`, { method: 'POST' })
    if (res.ok) { setRejectTarget(null); fetchPending() }
  }

  async function deleteRule(rule: ConfiguredAlert) {
    const res = await alertsFetch(`/api/v1/alerts/rules/${rule.alert_id}`, { method: 'DELETE' })
    if (res.ok) setRules(prev => prev.filter(r => r.alert_id !== rule.alert_id))
  }

  function openCreate() {
    setEditRule(null); setRuleForm(EMPTY_FORM); setRuleError(''); setShowRule(true)
  }
  function openEdit(rule: ConfiguredAlert) {
    setEditRule(rule)
    setRuleForm({
      alert_name: rule.alert_name, environmental_metric: rule.environmental_metric,
      geographic_area: rule.geographic_area, threshold_value: String(rule.threshold_value),
      condition: (rule.condition ?? 'ABOVE') as Condition,
      timeframe_minutes: String(rule.timeframe_minutes), alert_visibility: rule.alert_visibility,
      description: rule.description ?? '',
    })
    setRuleError(''); setShowRule(true)
  }

  async function saveRule(e: React.FormEvent) {
    e.preventDefault()
    if (!profile) return
    setRuleLoading(true); setRuleError('')

    const body = {
      operator_id:          profile.accountinfo_id,
      alert_name:           ruleForm.alert_name,
      environmental_metric: ruleForm.environmental_metric,
      geographic_area:      ruleForm.geographic_area,
      threshold_value:      Number(ruleForm.threshold_value),
      condition:            ruleForm.condition,
      timeframe_minutes:    Number(ruleForm.timeframe_minutes),
      alert_visibility:     ruleForm.alert_visibility,
      description:          ruleForm.description || null,
    }

    const res = editRule
      ? await alertsFetch(`/api/v1/alerts/rules/${editRule.alert_id}`, { method: 'PATCH', body: JSON.stringify(body) })
      : await alertsFetch('/api/v1/alerts/rules', { method: 'POST', body: JSON.stringify(body) })

    const data = await res.json()
    setRuleLoading(false)

    if (!res.ok) { setRuleError(data?.detail ?? data?.message ?? 'Failed to save rule'); return }
    setShowRule(false)
    fetchRules()
  }

  /* ── Summary counts ── */
  const activeCount  = triggered.filter(t => t.status === 'active').length
  const ackCount     = triggered.filter(t => t.status === 'acknowledged').length
  const approvedRules = rules.filter(r => r.status === 'approved' && r.is_active).length

  const availableTabs: { key: Tab; label: string }[] = [
    { key: 'triggered', label: 'Triggered Alerts' },
    { key: 'rules',     label: 'Alert Rules'       },
    ...(isAdmin ? [{ key: 'pending' as Tab, label: `Pending Approval${pending.length ? ` (${pending.length})` : ''}` }] : []),
  ]

  return (
    <div className="flex h-screen bg-black overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <Header title="Alert Management" />

        <div className="flex-1 p-6 overflow-auto">

          {/* Summary */}
          <div className="grid grid-cols-4 gap-3 mb-6">
            {[
              { label: 'Active',        value: activeCount,             color: 'text-red-400'     },
              { label: 'Acknowledged',  value: ackCount,                color: 'text-sky-400'     },
              { label: 'Active Rules',  value: approvedRules,           color: 'text-emerald-400' },
              { label: 'Pending Review',value: pending.length,          color: 'text-amber-400'   },
            ].map(s => (
              <div key={s.label} className="bg-zinc-900 border border-zinc-800 rounded-sm px-4 py-3 flex flex-col items-center">
                <span className={`text-2xl font-bold ${s.color}`} style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                  {s.value}
                </span>
                <span className="text-zinc-500 text-[10px] uppercase tracking-widest mt-0.5">{s.label}</span>
              </div>
            ))}
          </div>

          {/* Tabs */}
          <div className="flex gap-0 mb-4 border-b border-zinc-800">
            {availableTabs.map(t => (
              <button key={t.key} onClick={() => setTab(t.key)}
                className={`px-5 py-2.5 text-xs font-bold uppercase tracking-widest transition-colors border-b-2 -mb-px ${
                  tab === t.key ? 'text-white border-white' : 'text-zinc-500 border-transparent hover:text-zinc-300'
                }`}
                style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                {t.label}
              </button>
            ))}
            <button onClick={() => { if (tab === 'triggered') fetchTriggered(); else if (tab === 'rules') fetchRules(); else fetchPending() }}
              className="ml-auto mb-0.5 text-zinc-500 hover:text-white transition-colors">
              <RefreshCw size={14} strokeWidth={1.8} />
            </button>
          </div>

          {error && (
            <div className="mb-4 text-red-400 text-xs border border-red-500/30 bg-red-500/10 px-4 py-2 rounded-sm">{error}</div>
          )}

          {loading ? (
            <div className="flex justify-center py-16">
              <div className="w-5 h-5 border-2 border-zinc-700 border-t-white rounded-full animate-spin" />
            </div>
          ) : (
            <>
              {/* ── Triggered Alerts ── */}
              {tab === 'triggered' && (
                triggered.length === 0 ? (
                  <div className="text-center py-16 text-zinc-600 text-xs">No triggered alerts found.</div>
                ) : (
                  <div className="border border-zinc-800 rounded-sm overflow-hidden">
                    <table className="w-full text-sm border-collapse">
                      <thead className="bg-zinc-900">
                        <tr className="border-b border-zinc-800">
                          {['ID', 'Alert Name', 'Metric', 'Zone', 'Reading', 'Severity', 'Status', 'Time', 'Actions'].map(col => (
                            <th key={col} className="text-left px-4 py-2.5 text-zinc-500 font-semibold text-[10px] uppercase tracking-widest whitespace-nowrap"
                              style={{ fontFamily: "'Space Grotesk', sans-serif" }}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {triggered.map(t => {
                          const cfg = TRIGGERED_CFG[t.status]
                          return (
                            <tr key={t.triggered_alert_id} className={`border-b border-zinc-800/60 hover:bg-zinc-900/50 transition-colors ${cfg.row}`}>
                              <td className="px-4 py-3 text-zinc-400 font-mono text-[10px]">{t.triggered_alert_id?.slice(0, 8)}…</td>
                              <td className="px-4 py-3 text-zinc-300 text-xs font-medium max-w-[140px] truncate">{t.alert_name ?? '—'}</td>
                              <td className="px-4 py-3 text-zinc-400 text-xs">{t.environmental_metric ?? '—'}</td>
                              <td className="px-4 py-3 text-zinc-400 text-xs">{t.region ?? '—'}</td>
                              <td className="px-4 py-3 text-zinc-300 font-mono text-xs">{t.triggered_value}</td>
                              <td className="px-4 py-3 text-xs font-bold" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                                <span className={t.alert_severity ? SEV_COLOR[t.alert_severity] : 'text-zinc-600'}>
                                  {t.alert_severity ?? '—'}
                                </span>
                              </td>
                              <td className="px-4 py-3">
                                <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[10px] font-bold tracking-widest ${cfg.badge}`}
                                  style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                                  <cfg.Icon size={10} strokeWidth={2.5} />
                                  {cfg.label}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-zinc-500 text-xs font-mono whitespace-nowrap">
                                {t.triggered_at ? new Date(t.triggered_at).toLocaleString('en-CA', { hour12: false }).slice(0, 16) : '—'}
                              </td>
                              <td className="px-4 py-3">
                                <div className="flex items-center gap-2">
                                  <button onClick={() => setViewAlert(t)} className="text-zinc-500 hover:text-white transition-colors" title="View details">
                                    <Eye size={13} strokeWidth={1.8} />
                                  </button>
                                  {(t.status === 'active') && (
                                    <button onClick={() => acknowledge(t)} className="text-zinc-500 hover:text-sky-400 transition-colors" title="Acknowledge">
                                      <Bell size={13} strokeWidth={1.8} />
                                    </button>
                                  )}
                                  {(t.status === 'active' || t.status === 'acknowledged') && (
                                    <button onClick={async () => {
                                      const res = await alertsFetch(`/api/v1/alerts/triggered/${t.triggered_alert_id}/acknowledge`, {
                                        method: 'POST',
                                        body: JSON.stringify({ operator_id: profile?.accountinfo_id }),
                                      })
                                      if (res.ok) fetchTriggered()
                                    }} className="text-zinc-500 hover:text-emerald-400 transition-colors" title="Resolve">
                                      <ShieldCheck size={13} strokeWidth={1.8} />
                                    </button>
                                  )}
                                </div>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )
              )}

              {/* ── Alert Rules ── */}
              {tab === 'rules' && (
                <>
                  <div className="flex justify-end mb-3">
                    <button onClick={openCreate}
                      className="flex items-center gap-2 bg-white text-black text-xs font-bold px-4 py-2 rounded-sm hover:bg-zinc-200 transition-colors"
                      style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                      <Plus size={13} strokeWidth={2} /> New Rule
                    </button>
                  </div>
                  {rules.length === 0 ? (
                    <div className="text-center py-16 text-zinc-600 text-xs">No alert rules found. Create one to get started.</div>
                  ) : (
                    <div className="border border-zinc-800 rounded-sm overflow-hidden">
                      <table className="w-full text-sm border-collapse">
                        <thead className="bg-zinc-900">
                          <tr className="border-b border-zinc-800">
                            {['Rule Name', 'Metric', 'Zone', 'Threshold', 'Timeframe', 'Visibility', 'Status', ''].map(col => (
                              <th key={col} className="text-left px-4 py-2.5 text-zinc-500 font-semibold text-[10px] uppercase tracking-widest"
                                style={{ fontFamily: "'Space Grotesk', sans-serif" }}>{col}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {rules.filter(r => r.is_active).map(r => {
                            const scfg = RULE_STATUS_CFG[r.status]
                            return (
                              <tr key={r.alert_id} className="border-b border-zinc-800/60 hover:bg-zinc-900/50 transition-colors">
                                <td className="px-4 py-3 text-white text-xs font-medium">{r.alert_name}</td>
                                <td className="px-4 py-3 text-zinc-300 text-xs">{r.environmental_metric}</td>
                                <td className="px-4 py-3 text-zinc-400 text-xs">{r.geographic_area}</td>
                                <td className="px-4 py-3 text-zinc-300 font-mono text-xs">
                                  <span className={`text-[9px] font-bold mr-1 ${(r.condition ?? 'ABOVE') === 'BELOW' ? 'text-sky-400' : 'text-amber-400'}`}>
                                    {r.condition ?? 'ABOVE'}
                                  </span>
                                  {r.threshold_value}{r.threshold_value_max ? `–${r.threshold_value_max}` : ''}
                                </td>
                                <td className="px-4 py-3 text-zinc-400 text-xs">{r.timeframe_minutes} min</td>
                                <td className="px-4 py-3">
                                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-sm tracking-widest border ${
                                    r.alert_visibility === 'Public Facing'
                                      ? 'bg-sky-500/10 text-sky-400 border-sky-500/30'
                                      : 'bg-zinc-700 text-zinc-400 border-zinc-600'
                                  }`} style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                                    {r.alert_visibility === 'Public Facing' ? 'PUBLIC' : 'INTERNAL'}
                                  </span>
                                </td>
                                <td className="px-4 py-3">
                                  <span className={`inline-flex items-center px-2 py-0.5 rounded-sm text-[10px] font-bold tracking-widest border ${scfg.badge}`}
                                    style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                                    {scfg.label}
                                  </span>
                                </td>
                                <td className="px-4 py-3">
                                  <div className="flex items-center gap-3">
                                    {r.status === 'pending' && (
                                      <button onClick={() => submitForApproval(r)}
                                        className="text-zinc-500 hover:text-amber-400 transition-colors flex items-center gap-1 text-xs" title="Send for approval">
                                        <Send size={11} strokeWidth={1.8} /> Submit
                                      </button>
                                    )}
                                    <button onClick={() => openEdit(r)} className="text-zinc-500 hover:text-white transition-colors text-xs">Edit</button>
                                    <button onClick={() => deleteRule(r)} className="text-zinc-600 hover:text-red-400 transition-colors text-xs">Delete</button>
                                  </div>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              )}

              {/* ── Pending Approval (Admin only) ── */}
              {tab === 'pending' && isAdmin && (
                pending.length === 0 ? (
                  <div className="text-center py-16 text-zinc-600 text-xs">No rules awaiting approval.</div>
                ) : (
                  <div className="border border-zinc-800 rounded-sm overflow-hidden">
                    <table className="w-full text-sm border-collapse">
                      <thead className="bg-zinc-900">
                        <tr className="border-b border-zinc-800">
                          {['Rule Name', 'Metric', 'Zone', 'Threshold', 'Visibility', 'Created', 'Actions'].map(col => (
                            <th key={col} className="text-left px-4 py-2.5 text-zinc-500 font-semibold text-[10px] uppercase tracking-widest"
                              style={{ fontFamily: "'Space Grotesk', sans-serif" }}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {pending.map(r => (
                          <tr key={r.alert_id} className="border-b border-zinc-800/60 hover:bg-zinc-900/50 transition-colors border-l-2 border-l-amber-500/50">
                            <td className="px-4 py-3 text-white text-xs font-medium">{r.alert_name}</td>
                            <td className="px-4 py-3 text-zinc-300 text-xs">{r.environmental_metric}</td>
                            <td className="px-4 py-3 text-zinc-400 text-xs">{r.geographic_area}</td>
                            <td className="px-4 py-3 text-zinc-300 font-mono text-xs">
                              <span className={`text-[9px] font-bold mr-1 ${(r.condition ?? 'ABOVE') === 'BELOW' ? 'text-sky-400' : 'text-amber-400'}`}>
                                {r.condition ?? 'ABOVE'}
                              </span>
                              {r.threshold_value}
                            </td>
                            <td className="px-4 py-3 text-zinc-400 text-xs">{r.alert_visibility}</td>
                            <td className="px-4 py-3 text-zinc-500 text-xs font-mono">
                              {r.created_at ? new Date(r.created_at).toLocaleDateString('en-CA') : '—'}
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-3">
                                <button onClick={() => approveRule(r)}
                                  className="flex items-center gap-1 text-emerald-400 hover:text-emerald-300 transition-colors text-xs font-bold">
                                  <CheckCircle size={11} strokeWidth={2} /> Approve
                                </button>
                                <button onClick={() => setRejectTarget(r)}
                                  className="text-zinc-500 hover:text-red-400 transition-colors text-xs">
                                  Reject
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )
              )}
            </>
          )}
        </div>
      </div>

      {/* View Triggered Alert Detail Modal */}
      {viewAlert && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-sm w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-white text-sm font-bold tracking-wide uppercase" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                Triggered Alert
              </h3>
              <button onClick={() => setViewAlert(null)} className="text-zinc-500 hover:text-white transition-colors"><X size={16} strokeWidth={1.8} /></button>
            </div>
            <div className="space-y-3 text-xs">
              {[
                ['Alert Rule',   viewAlert.alert_name ?? viewAlert.alert_id.slice(0, 8)],
                ['Metric',       viewAlert.environmental_metric ?? '—'],
                ['Zone',         viewAlert.region ?? '—'],
                ['Sensor',       viewAlert.sensor_id ?? '—'],
                ['Reading',      String(viewAlert.triggered_value)],
                ['Severity',     viewAlert.alert_severity ?? '—'],
                ['Status',       viewAlert.status],
                ['Triggered',    viewAlert.triggered_at ? new Date(viewAlert.triggered_at).toLocaleString('en-CA', { hour12: false }) : '—'],
                ['False Alarm',  viewAlert.is_false_alarm ? 'Yes' : 'No'],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between border-b border-zinc-800 pb-2 last:border-0">
                  <span className="text-zinc-500 uppercase tracking-widest">{k}</span>
                  <span className="text-zinc-300 font-mono">{v}</span>
                </div>
              ))}
            </div>
            {(viewAlert.status === 'active' || viewAlert.status === 'acknowledged') && (
              <div className="flex gap-3 mt-5">
                {viewAlert.status === 'active' && (
                  <button onClick={() => { acknowledge(viewAlert); setViewAlert({ ...viewAlert, status: 'acknowledged' }) }}
                    className="flex-1 border border-sky-500/50 text-sky-400 text-xs font-bold py-2.5 rounded-sm hover:bg-sky-500/10 transition-colors"
                    style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                    Acknowledge
                  </button>
                )}
                <button onClick={() => setViewAlert(null)}
                  className="flex-1 bg-white text-black text-xs font-bold py-2.5 rounded-sm hover:bg-zinc-200 transition-colors"
                  style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                  Close
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Reject Confirmation Modal */}
      {rejectTarget && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-sm w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white text-sm font-bold tracking-wide uppercase" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                Reject Rule
              </h3>
              <button onClick={() => setRejectTarget(null)} className="text-zinc-500 hover:text-white"><X size={16} strokeWidth={1.8} /></button>
            </div>
            <p className="text-zinc-400 text-xs mb-5">
              Reject <span className="text-white font-medium">"{rejectTarget.alert_name}"</span>? This cannot be undone.
            </p>
            <div className="flex gap-3">
              <button onClick={() => setRejectTarget(null)}
                className="flex-1 border border-zinc-700 text-zinc-400 text-xs font-bold py-2.5 rounded-sm hover:border-zinc-500 hover:text-white transition-colors"
                style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                Cancel
              </button>
              <button onClick={() => rejectRule(rejectTarget)}
                className="flex-1 bg-red-500/20 border border-red-500/40 text-red-400 text-xs font-bold py-2.5 rounded-sm hover:bg-red-500/30 transition-colors"
                style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                Reject
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create / Edit Rule Modal */}
      {showRule && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-sm w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-white text-sm font-bold tracking-wide uppercase" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                {editRule ? 'Edit Alert Rule' : 'New Alert Rule'}
              </h3>
              <button onClick={() => setShowRule(false)} className="text-zinc-500 hover:text-white"><X size={16} strokeWidth={1.8} /></button>
            </div>
            <form onSubmit={saveRule} className="flex flex-col gap-4">
              {[
                { label: 'Rule Name', key: 'alert_name', type: 'text', placeholder: 'e.g. Downtown AQI Alert', required: true },
                { label: 'Geographic Area', key: 'geographic_area', type: 'text', placeholder: 'e.g. Zone A', required: true },
                { label: 'Threshold Value', key: 'threshold_value', type: 'number', placeholder: 'e.g. 35', required: true },
                { label: 'Timeframe (minutes)', key: 'timeframe_minutes', type: 'number', placeholder: 'e.g. 15', required: true },
              ].map(f => (
                <div key={f.key} className="flex flex-col gap-1.5">
                  <label className="text-zinc-400 text-xs uppercase tracking-widest font-medium">{f.label}</label>
                  <input type={f.type} required={f.required} placeholder={f.placeholder}
                    value={ruleForm[f.key as keyof RuleForm]}
                    onChange={e => setRuleForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                    className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm px-3 py-2.5 rounded-sm outline-none focus:border-zinc-500 placeholder:text-zinc-600 transition-colors"
                  />
                </div>
              ))}
              <div className="flex flex-col gap-1.5">
                <label className="text-zinc-400 text-xs uppercase tracking-widest font-medium">Environmental Metric</label>
                <select value={ruleForm.environmental_metric}
                  onChange={e => setRuleForm(prev => ({ ...prev, environmental_metric: e.target.value as Metric }))}
                  className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm px-3 py-2.5 rounded-sm outline-none focus:border-zinc-500 transition-colors">
                  {METRICS.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-zinc-400 text-xs uppercase tracking-widest font-medium">Condition</label>
                <div className="flex gap-2">
                  {(['ABOVE', 'BELOW'] as Condition[]).map(c => (
                    <button key={c} type="button" onClick={() => setRuleForm(prev => ({ ...prev, condition: c }))}
                      className={`flex-1 py-2.5 text-xs font-bold uppercase tracking-widest rounded-sm border transition-colors ${
                        ruleForm.condition === c
                          ? 'bg-white text-black border-white'
                          : 'text-zinc-400 border-zinc-700 hover:border-zinc-500 hover:text-white'
                      }`} style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                      {c === 'ABOVE' ? 'Above threshold' : 'Below threshold'}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-zinc-400 text-xs uppercase tracking-widest font-medium">Visibility</label>
                <select value={ruleForm.alert_visibility}
                  onChange={e => setRuleForm(prev => ({ ...prev, alert_visibility: e.target.value as Visibility }))}
                  className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm px-3 py-2.5 rounded-sm outline-none focus:border-zinc-500 transition-colors">
                  <option value="Internal">Internal</option>
                  <option value="Public Facing">Public Facing</option>
                </select>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-zinc-400 text-xs uppercase tracking-widest font-medium">Description (optional)</label>
                <input type="text" placeholder="Brief description"
                  value={ruleForm.description}
                  onChange={e => setRuleForm(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm px-3 py-2.5 rounded-sm outline-none focus:border-zinc-500 placeholder:text-zinc-600 transition-colors"
                />
              </div>
              {ruleError && <p className="text-red-400 text-xs border border-red-500/30 bg-red-500/10 px-3 py-2 rounded-sm">{ruleError}</p>}
              <div className="flex gap-3 mt-1">
                <button type="button" onClick={() => setShowRule(false)}
                  className="flex-1 border border-zinc-700 text-zinc-400 text-xs font-bold py-2.5 rounded-sm hover:text-white hover:border-zinc-500 transition-colors"
                  style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                  Cancel
                </button>
                <button type="submit" disabled={ruleLoading}
                  className="flex-1 bg-white text-black text-xs font-bold py-2.5 rounded-sm hover:bg-zinc-200 transition-colors disabled:opacity-50"
                  style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                  {ruleLoading ? 'Saving…' : editRule ? 'Save Changes' : 'Create Rule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
