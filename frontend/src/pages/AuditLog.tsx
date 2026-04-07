import { useState, useEffect, useCallback } from 'react'
import { backendFetch } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import Sidebar from '../components/layout/Sidebar'
import Header from '../components/layout/Header'

// ── Types ──────────────────────────────────────────────────────────────────

interface AuditEntry {
  log_id: string
  event_type: string
  action_description: string
  user_id: string | null
  entity_type: string | null
  entity_id: string | null
  status: 'success' | 'failure' | 'partial'
  ip_address: string | null
  timestamp: string | null
}

interface AuditLogPageResponse {
  entries: AuditEntry[]
  total: number
  page: number
  page_size: number
}

// ── Helpers ────────────────────────────────────────────────────────────────

const EVENT_LABELS: Record<string, string> = {
  user_login:          'Login',
  user_logout:         'Logout',
  user_created:        'Account Created',
  user_modified:       'Account Modified',
  user_deleted:        'Account Deleted',
  alert_created:       'Alert Created',
  alert_modified:      'Alert Modified',
  alert_deleted:       'Alert Deleted',
  alert_triggered:     'Alert Triggered',
  alert_acknowledged:  'Alert Acknowledged',
  alert_verified:      'Alert Verified',
  alert_rejected:      'Alert Rejected',
  data_access:         'Data Access',
  api_request:         'API Request',
  permission_change:   'Permission Change',
  system_event:        'System Event',
  error_event:         'Error',
}

function formatTimestamp(ts: string | null): string {
  if (!ts) return '—'
  const d = new Date(ts)
  return d.toLocaleString('en-CA', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

function StatusBadge({ status }: { status: AuditEntry['status'] }) {
  const styles: Record<string, string> = {
    success: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30',
    failure: 'bg-red-500/10 text-red-400 border border-red-500/30',
    partial: 'bg-amber-500/10 text-amber-400 border border-amber-500/30',
  }
  return (
    <span
      className={`text-[10px] font-bold px-1.5 py-0.5 rounded-sm tracking-widest uppercase ${styles[status] ?? styles.partial}`}
      style={{ fontFamily: "'Space Grotesk', sans-serif" }}
    >
      {status}
    </span>
  )
}

function EventTypeBadge({ type }: { type: string }) {
  const isAlert   = type.startsWith('alert_')
  const isError   = type === 'error_event'
  const isAccount = type.startsWith('user_')

  const color = isError
    ? 'bg-red-500/10 text-red-400 border border-red-500/20'
    : isAlert
    ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
    : isAccount
    ? 'bg-zinc-700 text-zinc-300 border border-zinc-600'
    : 'bg-zinc-800 text-zinc-400 border border-zinc-700'

  return (
    <span
      className={`text-[10px] font-bold px-1.5 py-0.5 rounded-sm tracking-widest whitespace-nowrap ${color}`}
      style={{ fontFamily: "'Space Grotesk', sans-serif" }}
    >
      {EVENT_LABELS[type] ?? type}
    </span>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

export default function AuditLog() {
  const { profile } = useAuth()

  const [filterUserId, setFilterUserId] = useState('')
  const [inputUserId,  setInputUserId]  = useState('')

  const [page,     setPage]     = useState(1)
  const PAGE_SIZE = 20

  const [data,    setData]    = useState<AuditLogPageResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  const fetchLog = useCallback(async (userId: string, pageNum: number) => {
    setLoading(true)
    setError('')

    const params = new URLSearchParams({
      page:      String(pageNum),
      page_size: String(PAGE_SIZE),
    })
    if (userId.trim()) params.set('user_id', userId.trim())

    const res = await backendFetch(`/api/v1/audit?${params.toString()}`)
    if (!res.ok) {
      setError('Failed to fetch audit log.')
      setLoading(false)
      return
    }
    const json: AuditLogPageResponse = await res.json()
    setData(json)
    setLoading(false)
  }, [])

  // Initial load — if admin show all, otherwise default to own id
  useEffect(() => {
    const defaultId = profile?.role === 'System Administrator' ? '' : (profile?.accountinfo_id ?? '')
    setFilterUserId(defaultId)
    setInputUserId(defaultId)
    fetchLog(defaultId, 1)
  }, [profile, fetchLog])

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setPage(1)
    setFilterUserId(inputUserId)
    fetchLog(inputUserId, 1)
  }

  function handleClear() {
    setInputUserId('')
    setFilterUserId('')
    setPage(1)
    fetchLog('', 1)
  }

  function goToPage(p: number) {
    setPage(p)
    fetchLog(filterUserId, p)
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  return (
    <div className="flex h-screen bg-black overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <Header title="Audit Log" />

        <div className="flex-1 p-6 overflow-auto">
          <div className="max-w-5xl space-y-5">

            {/* Filter bar */}
            <div className="border border-zinc-800 rounded-sm p-5">
              <h2
                className="text-white text-xs font-bold uppercase tracking-widest mb-4"
                style={{ fontFamily: "'Space Grotesk', sans-serif" }}
              >
                Filter
              </h2>
              <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
                <div className="flex flex-col gap-1.5 flex-1">
                  <label className="text-zinc-400 text-xs uppercase tracking-widest font-medium">
                    Operator ID (UUID)
                  </label>
                  <input
                    type="text"
                    value={inputUserId}
                    onChange={(e) => setInputUserId(e.target.value)}
                    placeholder="Leave blank to show all events"
                    className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm px-3 py-2.5 rounded-sm outline-none focus:border-zinc-500 placeholder:text-zinc-600 transition-colors font-mono"
                  />
                </div>
                <div className="flex items-end gap-2">
                  <button
                    type="submit"
                    className="bg-white text-black text-xs font-bold px-5 py-2.5 rounded-sm hover:bg-zinc-200 transition-colors whitespace-nowrap"
                    style={{ fontFamily: "'Space Grotesk', sans-serif" }}
                  >
                    Search
                  </button>
                  {filterUserId && (
                    <button
                      type="button"
                      onClick={handleClear}
                      className="bg-zinc-800 text-zinc-300 text-xs font-bold px-4 py-2.5 rounded-sm hover:bg-zinc-700 border border-zinc-700 transition-colors whitespace-nowrap"
                      style={{ fontFamily: "'Space Grotesk', sans-serif" }}
                    >
                      Clear
                    </button>
                  )}
                </div>
              </form>
              {filterUserId && (
                <p className="text-zinc-500 text-xs mt-3 font-mono">
                  Showing events for: <span className="text-zinc-300">{filterUserId}</span>
                </p>
              )}
            </div>

            {/* Summary row */}
            {data && !loading && (
              <div className="flex items-center justify-between">
                <p className="text-zinc-500 text-xs">
                  <span className="text-zinc-300 font-medium">{data.total}</span> event{data.total !== 1 ? 's' : ''} found
                  {totalPages > 1 && (
                    <span> &mdash; page <span className="text-zinc-300">{page}</span> of <span className="text-zinc-300">{totalPages}</span></span>
                  )}
                </p>
                {/* Pagination controls */}
                {totalPages > 1 && (
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => goToPage(page - 1)}
                      disabled={page <= 1}
                      className="text-xs text-zinc-400 px-2.5 py-1.5 border border-zinc-700 rounded-sm hover:border-zinc-500 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      ← Prev
                    </button>
                    <button
                      onClick={() => goToPage(page + 1)}
                      disabled={page >= totalPages}
                      className="text-xs text-zinc-400 px-2.5 py-1.5 border border-zinc-700 rounded-sm hover:border-zinc-500 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      Next →
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* State: loading */}
            {loading && (
              <div className="border border-zinc-800 rounded-sm p-8 flex items-center justify-center">
                <p className="text-zinc-500 text-xs uppercase tracking-widest" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                  Loading…
                </p>
              </div>
            )}

            {/* State: error */}
            {error && !loading && (
              <p className="text-red-400 text-xs border border-red-500/30 bg-red-500/10 px-3 py-2 rounded-sm">
                {error}
              </p>
            )}

            {/* State: empty */}
            {!loading && !error && data && data.entries.length === 0 && (
              <div className="border border-zinc-800 rounded-sm p-8 flex items-center justify-center">
                <p className="text-zinc-500 text-xs uppercase tracking-widest" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                  No events found
                </p>
              </div>
            )}

            {/* Audit log table */}
            {!loading && !error && data && data.entries.length > 0 && (
              <div className="border border-zinc-800 rounded-sm overflow-hidden">
                <table className="w-full text-sm" style={{ tableLayout: 'fixed' }}>
                  <colgroup>
                    <col style={{ width: '180px' }} />
                    <col style={{ width: '140px' }} />
                    <col style={{ minWidth: '200px' }} />
                    <col style={{ width: '140px' }} />
                    <col style={{ width: '100px' }} />
                  </colgroup>
                  <thead>
                    <tr className="border-b border-zinc-800">
                      <th className="text-left text-zinc-500 text-[10px] font-bold uppercase tracking-widest px-4 py-3" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                        Timestamp
                      </th>
                      <th className="text-left text-zinc-500 text-[10px] font-bold uppercase tracking-widest px-4 py-3" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                        Event
                      </th>
                      <th className="text-left text-zinc-500 text-[10px] font-bold uppercase tracking-widest px-4 py-3" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                        Description
                      </th>
                      <th className="text-left text-zinc-500 text-[10px] font-bold uppercase tracking-widest px-4 py-3" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                        Entity
                      </th>
                      <th className="text-left text-zinc-500 text-[10px] font-bold uppercase tracking-widest px-4 py-3" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                        Status
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.entries.map((entry, i) => (
                      <tr
                        key={entry.log_id}
                        className={`border-b border-zinc-800/60 hover:bg-zinc-900/40 transition-colors ${
                          i === data.entries.length - 1 ? 'border-b-0' : ''
                        }`}
                      >
                        {/* Timestamp */}
                        <td className="px-4 py-3 align-top">
                          <span className="text-zinc-400 text-xs font-mono whitespace-nowrap">
                            {formatTimestamp(entry.timestamp)}
                          </span>
                        </td>

                        {/* Event type badge */}
                        <td className="px-4 py-3 align-top">
                          <EventTypeBadge type={entry.event_type} />
                        </td>

                        {/* Description + optional IP */}
                        <td className="px-4 py-3 align-top">
                          <p className="text-zinc-300 text-xs leading-relaxed break-words">
                            {entry.action_description}
                          </p>
                          {entry.ip_address && (
                            <p className="text-zinc-600 text-[10px] font-mono mt-1">
                              {entry.ip_address}
                            </p>
                          )}
                        </td>

                        {/* Entity type + id */}
                        <td className="px-4 py-3 align-top">
                          {entry.entity_type ? (
                            <div>
                              <p className="text-zinc-400 text-xs capitalize">{entry.entity_type}</p>
                              {entry.entity_id && (
                                <p className="text-zinc-600 text-[10px] font-mono mt-0.5 truncate" title={entry.entity_id}>
                                  {entry.entity_id.length > 12
                                    ? entry.entity_id.slice(0, 8) + '…'
                                    : entry.entity_id}
                                </p>
                              )}
                            </div>
                          ) : (
                            <span className="text-zinc-700 text-xs">—</span>
                          )}
                        </td>

                        {/* Status badge */}
                        <td className="px-4 py-3 align-top">
                          <StatusBadge status={entry.status} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Bottom pagination */}
            {!loading && data && totalPages > 1 && (
              <div className="flex items-center justify-between">
                <p className="text-zinc-600 text-xs">
                  Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, data.total)} of {data.total}
                </p>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => goToPage(1)}
                    disabled={page <= 1}
                    className="text-xs text-zinc-400 px-2.5 py-1.5 border border-zinc-700 rounded-sm hover:border-zinc-500 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    First
                  </button>
                  <button
                    onClick={() => goToPage(page - 1)}
                    disabled={page <= 1}
                    className="text-xs text-zinc-400 px-2.5 py-1.5 border border-zinc-700 rounded-sm hover:border-zinc-500 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    ← Prev
                  </button>
                  <button
                    onClick={() => goToPage(page + 1)}
                    disabled={page >= totalPages}
                    className="text-xs text-zinc-400 px-2.5 py-1.5 border border-zinc-700 rounded-sm hover:border-zinc-500 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    Next →
                  </button>
                  <button
                    onClick={() => goToPage(totalPages)}
                    disabled={page >= totalPages}
                    className="text-xs text-zinc-400 px-2.5 py-1.5 border border-zinc-700 rounded-sm hover:border-zinc-500 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    Last
                  </button>
                </div>
              </div>
            )}

          </div>
        </div>
      </div>
    </div>
  )
}