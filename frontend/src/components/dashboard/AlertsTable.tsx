import { AlertTriangle, CheckCircle, Clock, Loader } from 'lucide-react'

type AlertStatus = 'PENDING' | 'ACTIVE' | 'RESOLVED' | 'WAITING'

interface AlertRow {
  id: string
  sensorId: string
  category: string
  description: string
  zone: string
  reading: string
  status: AlertStatus
  timestamp: string
}

const MOCK_ALERTS: AlertRow[] = [
  { id: 'A1001', sensorId: 'S002', category: 'AIR_QUALITY',  description: 'PM2.5 above threshold',       zone: 'Zone B', reading: '42 µg/m³',  status: 'PENDING',  timestamp: '2026-04-02 08:14' },
  { id: 'A1002', sensorId: 'S004', category: 'UV_INDEX',     description: 'UV index critically high',     zone: 'Zone D', reading: '11.2 UV',   status: 'ACTIVE',   timestamp: '2026-04-02 08:02' },
  { id: 'A1003', sensorId: 'S006', category: 'TEMPERATURE',  description: 'Temperature spike detected',   zone: 'Zone F', reading: '38.4 °C',  status: 'WAITING',  timestamp: '2026-04-02 07:55' },
  { id: 'A1004', sensorId: 'S001', category: 'HUMIDITY',     description: 'Humidity nominal',             zone: 'Zone A', reading: '62%',       status: 'RESOLVED', timestamp: '2026-04-02 07:30' },
  { id: 'A1005', sensorId: 'S003', category: 'NOISE',        description: 'Noise level elevated',         zone: 'Zone C', reading: '78 dB',     status: 'PENDING',  timestamp: '2026-04-02 07:20' },
  { id: 'A1006', sensorId: 'S005', category: 'AIR_QUALITY',  description: 'CO2 level rising',             zone: 'Zone E', reading: '1200 ppm',  status: 'ACTIVE',   timestamp: '2026-04-02 07:10' },
]

interface StatusConfig {
  label: string
  badge: string
  row: string
  Icon: typeof AlertTriangle
  iconClass: string
}

const STATUS_CONFIG: Record<AlertStatus, StatusConfig> = {
  PENDING:  {
    label: 'PENDING',
    badge: 'bg-amber-500/15 text-amber-400 border border-amber-500/30',
    row:   'border-l-2 border-l-amber-500/50',
    Icon: Clock,
    iconClass: 'text-amber-400',
  },
  ACTIVE: {
    label: 'ACTIVE',
    badge: 'bg-red-500/15 text-red-400 border border-red-500/30',
    row:   'border-l-2 border-l-red-500/60',
    Icon: AlertTriangle,
    iconClass: 'text-red-400',
  },
  WAITING: {
    label: 'WAITING',
    badge: 'bg-sky-500/15 text-sky-400 border border-sky-500/30',
    row:   'border-l-2 border-l-sky-500/40',
    Icon: Loader,
    iconClass: 'text-sky-400',
  },
  RESOLVED: {
    label: 'RESOLVED',
    badge: 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30',
    row:   'border-l-2 border-l-emerald-500/30',
    Icon: CheckCircle,
    iconClass: 'text-emerald-500',
  },
}

const COLUMNS = ['Alert ID', 'Sensor', 'Category', 'Description', 'Zone', 'Reading', 'Status', 'Time']

export default function AlertsTable() {
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
          {MOCK_ALERTS.map((row) => {
            const cfg = STATUS_CONFIG[row.status]
            return (
              <tr
                key={row.id}
                className={`border-b border-zinc-800/60 hover:bg-zinc-800/40 transition-colors cursor-pointer ${cfg.row}`}
              >
                <td className="px-4 py-2.5 text-zinc-300 font-mono text-xs font-semibold">{row.id}</td>
                <td className="px-4 py-2.5 text-zinc-400 font-mono text-xs">{row.sensorId}</td>
                <td className="px-4 py-2.5 text-xs">
                  <span className="text-zinc-300 font-medium tracking-wide" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                    {row.category}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-zinc-400 text-xs max-w-[200px] truncate">{row.description}</td>
                <td className="px-4 py-2.5 text-zinc-400 text-xs">{row.zone}</td>
                <td className="px-4 py-2.5 text-zinc-300 font-mono text-xs">{row.reading}</td>
                <td className="px-4 py-2.5">
                  <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[10px] font-bold tracking-wider ${cfg.badge}`}
                    style={{ fontFamily: "'Space Grotesk', sans-serif" }}
                  >
                    <cfg.Icon size={10} strokeWidth={2.5} className={cfg.iconClass} />
                    {cfg.label}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-zinc-500 text-xs whitespace-nowrap font-mono">{row.timestamp}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
