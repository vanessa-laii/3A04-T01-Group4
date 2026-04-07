import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle, Clock, Loader, X } from 'lucide-react'
import { alertsFetch } from '../../lib/api'

type TriggeredStatus = 'active' | 'acknowledged' | 'resolved' | 'dismissed'

interface AlertRow {
  triggered_alert_id: string
  sensor_id:          string | null
  environmental_metric: string
  alert_name:         string
  region:             string | null
  triggered_value:    number
  status:             TriggeredStatus
  triggered_at:       string | null
}

interface StatusConfig {
  label: string
  badge: string
  row:   string
  Icon:  typeof AlertTriangle
  iconClass: string
}

const STATUS_CONFIG: Record<TriggeredStatus, StatusConfig> = {
  active: {
    label: 'ACTIVE',
    badge: 'bg-red-500/15 text-red-400 border border-red-500/30',
    row:   'border-l-2 border-l-red-500/60',
    Icon: AlertTriangle,
    iconClass: 'text-red-400',
  },
  acknowledged: {
    label: 'ACKNOWLEDGED',
    badge: 'bg-sky-500/15 text-sky-400 border border-sky-500/30',
    row:   'border-l-2 border-l-sky-500/40',
    Icon: Loader,
    iconClass: 'text-sky-400',
  },
  resolved: {
    label: 'RESOLVED',
    badge: 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30',
    row:   'border-l-2 border-l-emerald-500/30',
    Icon: CheckCircle,
    iconClass: 'text-emerald-500',
  },
  dismissed: {
    label: 'DISMISSED',
    badge: 'bg-zinc-700 text-zinc-400 border border-zinc-600',
    row:   'border-l-2 border-l-zinc-700',
    Icon: X,
    iconClass: 'text-zinc-400',
  },
}

const COLUMNS = ['Alert ID', 'Sensor', 'Metric', 'Alert Name', 'Zone', 'Reading', 'Status', 'Time']

export default function AlertsTable() {
  const [rows, setRows]       = useState<AlertRow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    alertsFetch('/api/v1/alerts/database/records?limit=50')
      .then(r => r.json())
      .then(data => {
        const flat: AlertRow[] = []
        for (const record of data.records ?? []) {
          for (const t of record.triggered ?? []) {
            flat.push({
              triggered_alert_id: t.triggered_alert_id,
              sensor_id:          t.sensor_id,
              environmental_metric: record.alert.environmental_metric,
              alert_name:         record.alert.alert_name,
              region:             t.region,
              triggered_value:    t.triggered_value,
              status:             t.status,
              triggered_at:       t.triggered_at,
            })
          }
        }
        flat.sort((a, b) => new Date(b.triggered_at ?? 0).getTime() - new Date(a.triggered_at ?? 0).getTime())
        setRows(flat)
      })
      .catch(() => { /* backend offline */ })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex justify-center items-center h-full">
        <div className="w-4 h-4 border-2 border-zinc-700 border-t-white rounded-full animate-spin" />
      </div>
    )
  }

  if (rows.length === 0) {
    return (
      <div className="flex justify-center items-center h-full text-zinc-600 text-xs">
        No triggered alerts yet.
      </div>
    )
  }

  return (
    <div className="overflow-auto h-full">
      <table className="w-full text-sm border-collapse">
        <thead className="sticky top-0 bg-zinc-950 z-10">
          <tr className="border-b border-zinc-800">
            {COLUMNS.map((col) => (
              <th
                key={col}
                className="text-left px-4 py-2 text-zinc-500 font-semibold text-[10px] uppercase tracking-widest whitespace-nowrap"
                style={{ fontFamily: "'Space Grotesk', sans-serif" }}
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const cfg = STATUS_CONFIG[row.status] ?? STATUS_CONFIG.active
            return (
              <tr
                key={row.triggered_alert_id}
                className={`border-b border-zinc-800/60 hover:bg-zinc-800/40 transition-colors cursor-pointer ${cfg.row}`}
              >
                <td className="px-4 py-2.5 text-zinc-300 font-mono text-xs font-semibold">
                  {row.triggered_alert_id?.slice(0, 8)}…
                </td>
                <td className="px-4 py-2.5 text-zinc-400 font-mono text-xs">{row.sensor_id ?? '—'}</td>
                <td className="px-4 py-2.5 text-xs">
                  <span className="text-zinc-300 font-medium tracking-wide" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                    {row.environmental_metric}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-zinc-400 text-xs max-w-[160px] truncate">{row.alert_name}</td>
                <td className="px-4 py-2.5 text-zinc-400 text-xs">{row.region ?? '—'}</td>
                <td className="px-4 py-2.5 text-zinc-300 font-mono text-xs">{row.triggered_value}</td>
                <td className="px-4 py-2.5">
                  <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[10px] font-bold tracking-wider ${cfg.badge}`}
                    style={{ fontFamily: "'Space Grotesk', sans-serif" }}
                  >
                    <cfg.Icon size={10} strokeWidth={2.5} className={cfg.iconClass} />
                    {cfg.label}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-zinc-500 text-xs whitespace-nowrap font-mono">
                  {row.triggered_at
                    ? new Date(row.triggered_at).toLocaleString('en-CA', { hour12: false }).slice(0, 16)
                    : '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
