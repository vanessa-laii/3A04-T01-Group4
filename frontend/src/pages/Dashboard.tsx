import { useEffect, useState } from 'react'
import { Clock, AlertTriangle, Wifi, Thermometer, Wind, Droplets, Sun, Volume2, Activity } from 'lucide-react'
import { alertsFetch, dataFetch } from '../lib/api'
import Sidebar from '../components/layout/Sidebar'
import Header from '../components/layout/Header'
import StatCard from '../components/dashboard/StatCard'
import MapView from '../components/dashboard/MapView'
import AlertsTable from '../components/dashboard/AlertsTable'

type MetricType = 'Air Quality' | 'Temperature' | 'Humidity' | 'Noise Levels' | 'UV Levels'

interface TriggeredAlert {
  triggered_alert_id: string
  status: 'active' | 'acknowledged' | 'resolved' | 'dismissed'
}

interface DatabaseRecord {
  triggered: TriggeredAlert[]
}

interface SensorReading {
  sensor_id: string
  metric_type: MetricType
  metric_value: number
  unit: string
  geographic_zone: string
  recorded_at: string
}

const METRIC_CFG: Record<MetricType, { label: string; Icon: React.ElementType; thresholds: { warn: number; crit: number } }> = {
  'Temperature':  { label: 'Temperature', Icon: Thermometer, thresholds: { warn: 35, crit: 40  } },
  'Air Quality':  { label: 'Air Quality', Icon: Wind,        thresholds: { warn: 35, crit: 55  } },
  'UV Levels':    { label: 'UV Index',    Icon: Sun,         thresholds: { warn: 8,  crit: 11  } },
  'Humidity':     { label: 'Humidity',    Icon: Droplets,    thresholds: { warn: 70, crit: 85  } },
  'Noise Levels': { label: 'Noise',       Icon: Volume2,     thresholds: { warn: 70, crit: 90  } },
}

function valueColor(metric: MetricType, value: number): string {
  const t = METRIC_CFG[metric]?.thresholds
  if (!t) return 'text-zinc-300'
  if (value >= t.crit) return 'text-red-400'
  if (value >= t.warn) return 'text-amber-400'
  return 'text-emerald-400'
}

export default function Dashboard() {
  const [pendingCount, setPendingCount]   = useState<number | null>(null)
  const [activeCount, setActiveCount]     = useState<number | null>(null)
  const [sensorCount, setSensorCount]     = useState<number | null>(null)
  const [latestReadings, setLatestReadings] = useState<Map<MetricType, SensorReading>>(new Map())

  useEffect(() => {
    // Fetch triggered alert counts
    alertsFetch('/api/v1/alerts/database/records?limit=500')
      .then(r => r.json())
      .then(data => {
        const all: TriggeredAlert[] = (data.records ?? []).flatMap((rec: DatabaseRecord) => rec.triggered ?? [])
        setPendingCount(all.filter(t => t.status === 'active').length)
        setActiveCount(all.filter(t => t.status === 'active' || t.status === 'acknowledged').length)
      })
      .catch(() => { /* backend offline — keep null */ })

    // Fetch sensor readings
    dataFetch('/api/v1/database/records?limit=500')
      .then(r => r.json())
      .then(data => {
        const readings: SensorReading[] = data.readings ?? []
        // Count unique sensors
        const sensors = new Set(readings.map((r: SensorReading) => r.sensor_id))
        setSensorCount(sensors.size)
        // Latest reading per metric type
        const latest = new Map<MetricType, SensorReading>()
        for (const r of readings) {
          const existing = latest.get(r.metric_type)
          if (!existing || new Date(r.recorded_at) > new Date(existing.recorded_at)) {
            latest.set(r.metric_type, r)
          }
        }
        setLatestReadings(latest)
      })
      .catch(() => { /* backend offline — keep null */ })
  }, [])

  const ORDERED_METRICS: MetricType[] = ['Temperature', 'Air Quality', 'UV Levels', 'Humidity', 'Noise Levels']

  const stats = [
    {
      label: 'Pending',
      value: pendingCount ?? '—',
      Icon: Clock,
      iconColor: 'text-amber-400',
      valueColor: 'text-amber-400',
    },
    {
      label: 'Active Alerts',
      value: activeCount ?? '—',
      Icon: AlertTriangle,
      iconColor: 'text-red-400',
      valueColor: 'text-red-400',
    },
    {
      label: 'Sensors Online',
      value: sensorCount ?? '—',
      Icon: Wifi,
      iconColor: 'text-emerald-400',
      valueColor: 'text-white',
    },
  ]

  return (
    <div className="flex h-screen bg-black overflow-hidden">
      <Sidebar />

      <div className="flex flex-col flex-1 min-w-0">
        <Header title="311 Operations Center Dashboard" />

        {/* Sensor readings strip */}
        <div className="flex border-b border-zinc-800 bg-zinc-950 shrink-0">
          {ORDERED_METRICS.map((metric) => {
            const cfg     = METRIC_CFG[metric]
            const reading = latestReadings.get(metric)
            const Icon    = cfg.Icon
            const display = reading
              ? `${reading.metric_value.toFixed(1)} ${reading.unit}`
              : '— —'
            const zone    = reading?.geographic_zone ?? '…'
            const color   = reading ? valueColor(metric, reading.metric_value) : 'text-zinc-600'
            return (
              <div key={metric} className="flex-1 flex items-center gap-2 px-4 py-2.5 border-r border-zinc-800 last:border-r-0">
                <Icon size={14} strokeWidth={1.8} className={`shrink-0 ${color}`} />
                <div className="min-w-0">
                  <div className={`text-sm font-bold leading-none ${color}`} style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                    {display}
                  </div>
                  <div className="text-zinc-600 text-[9px] uppercase tracking-widest mt-0.5">
                    {cfg.label} · {zone}
                  </div>
                </div>
              </div>
            )
          })}
          {/* CO₂ — not a MetricType in backend but show if exists */}
          <div className="flex-1 flex items-center gap-2 px-4 py-2.5">
            <Activity size={14} strokeWidth={1.8} className="shrink-0 text-zinc-600" />
            <div className="min-w-0">
              <div className="text-sm font-bold leading-none text-zinc-600" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                — —
              </div>
              <div className="text-zinc-700 text-[9px] uppercase tracking-widest mt-0.5">CO₂ · —</div>
            </div>
          </div>
        </div>

        {/* Map + stat cards */}
        <div className="flex flex-1 min-h-0">
          <div className="flex flex-1 min-h-0 min-w-0">
            <div className="flex-1 min-w-0">
              <MapView />
            </div>

            <div className="w-44 shrink-0 bg-black border-l border-zinc-800 flex flex-col gap-2 p-3 pt-4">
              {stats.map((s) => (
                <StatCard
                  key={s.label}
                  label={s.label}
                  value={s.value}
                  Icon={s.Icon}
                  iconColor={s.iconColor}
                  valueColor={s.valueColor}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Alerts table */}
        <div className="h-56 border-t border-zinc-800 bg-black shrink-0">
          <div className="px-4 py-2 border-b border-zinc-800 flex items-center justify-between">
            <span className="text-zinc-300 text-xs uppercase tracking-widest font-semibold"
              style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
              Recent Alerts
            </span>
            <span className="text-zinc-600 text-xs">Latest readings · live data</span>
          </div>
          <div className="h-[calc(100%-33px)]">
            <AlertsTable />
          </div>
        </div>
      </div>
    </div>
  )
}
