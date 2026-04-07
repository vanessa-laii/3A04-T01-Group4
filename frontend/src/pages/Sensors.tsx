import { useState, useEffect, useCallback } from 'react'
import {
  Thermometer, Droplets, Wind, Sun, Volume2, Activity,
  Wifi, RefreshCw,
} from 'lucide-react'
import { dataFetch } from '../lib/api'
import Sidebar from '../components/layout/Sidebar'
import Header from '../components/layout/Header'

/* ── Types ── */

type MetricType    = 'Air Quality' | 'Temperature' | 'Humidity' | 'Noise Levels' | 'UV Levels'
type QualityFlag   = 'valid' | 'questionable' | 'invalid'

interface SensorReading {
  data_id:           string | null
  sensor_id:         string
  metric_type:       MetricType
  metric_value:      number
  unit:              string
  recorded_at:       string
  geographic_zone:   string
  data_quality_flag: QualityFlag
}

interface SensorDatabaseResponse {
  readings: SensorReading[]
  total:    number
}

/* ── Derived sensor row: one per sensor_id + metric_type ── */
interface SensorRow {
  key:             string
  sensor_id:       string
  zone:            string
  category:        MetricType
  value:           number
  unit:            string
  quality:         QualityFlag
  lastUpdated:     string
}

/* ── Styling ── */

const QUALITY_CFG: Record<QualityFlag, { badge: string; label: string }> = {
  valid:        { badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30', label: 'VALID'        },
  questionable: { badge: 'bg-amber-500/10  text-amber-400  border-amber-500/30',  label: 'QUESTIONABLE' },
  invalid:      { badge: 'bg-red-500/10    text-red-400    border-red-500/30',    label: 'INVALID'      },
}

const CATEGORY_ICON: Record<MetricType, React.ElementType> = {
  'Humidity':    Droplets,
  'Air Quality': Wind,
  'Noise Levels':Volume2,
  'UV Levels':   Sun,
  'Temperature': Thermometer,
}

type FilterQuality = 'ALL' | QualityFlag
const FILTERS: FilterQuality[] = ['ALL', 'valid', 'questionable', 'invalid']

export default function Sensors() {
  const [rows, setRows]           = useState<SensorRow[]>([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState('')
  const [filter, setFilter]       = useState<FilterQuality>('ALL')
  const [metricFilter, setMetricFilter] = useState<MetricType | 'ALL'>('ALL')

  const fetchData = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res  = await dataFetch('/api/v1/database/records?limit=500')
      const data: SensorDatabaseResponse = await res.json()
      if (!res.ok) { setError((data as unknown as { detail?: string })?.detail ?? 'Failed to load sensor data'); setLoading(false); return }

      // Group by sensor_id + metric_type, keep latest per group
      const map = new Map<string, SensorReading>()
      for (const r of data.readings ?? []) {
        const key = `${r.sensor_id}||${r.metric_type}`
        const existing = map.get(key)
        if (!existing || new Date(r.recorded_at) > new Date(existing.recorded_at)) {
          map.set(key, r)
        }
      }

      const sensorRows: SensorRow[] = Array.from(map.entries()).map(([key, r]) => ({
        key,
        sensor_id:   r.sensor_id,
        zone:        r.geographic_zone,
        category:    r.metric_type,
        value:       r.metric_value,
        unit:        r.unit,
        quality:     r.data_quality_flag,
        lastUpdated: r.recorded_at,
      }))
      sensorRows.sort((a, b) => a.sensor_id.localeCompare(b.sensor_id))
      setRows(sensorRows)
    } catch { setError('Could not reach data processing service (port 8003). Is Docker running?') }
    setLoading(false)
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  /* ── Derived counts ── */
  const total       = rows.length
  const validCount  = rows.filter(r => r.quality === 'valid').length
  const questCount  = rows.filter(r => r.quality === 'questionable').length
  const invalidCount= rows.filter(r => r.quality === 'invalid').length
  const uniqueSensors = new Set(rows.map(r => r.sensor_id)).size

  const allMetrics: (MetricType | 'ALL')[] = ['ALL', 'Air Quality', 'Temperature', 'Humidity', 'Noise Levels', 'UV Levels']

  const visible = rows.filter(r => {
    if (filter !== 'ALL' && r.quality !== filter) return false
    if (metricFilter !== 'ALL' && r.category !== metricFilter) return false
    return true
  })

  function BarGauge({ value, unit }: { value: number; unit: string }) {
    return (
      <span className="text-zinc-300 font-mono text-xs">
        {value.toFixed(2)} {unit}
      </span>
    )
  }

  return (
    <div className="flex h-screen bg-black overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <Header title="Sensor Network" />

        <div className="flex-1 p-6 overflow-auto">

          {/* Summary strip */}
          <div className="grid grid-cols-5 gap-3 mb-6">
            {[
              { label: 'Unique Sensors', value: uniqueSensors, color: 'text-white'       },
              { label: 'Total Readings', value: total,         color: 'text-zinc-300'    },
              { label: 'Valid',          value: validCount,    color: 'text-emerald-400' },
              { label: 'Questionable',   value: questCount,    color: 'text-amber-400'   },
              { label: 'Invalid',        value: invalidCount,  color: 'text-red-400'     },
            ].map(s => (
              <div key={s.label} className="bg-zinc-900 border border-zinc-800 rounded-sm px-4 py-3 flex flex-col items-center">
                <span className={`text-2xl font-bold ${s.color}`} style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                  {s.value}
                </span>
                <span className="text-zinc-500 text-[10px] uppercase tracking-widest mt-0.5">{s.label}</span>
              </div>
            ))}
          </div>

          {/* Filters */}
          <div className="flex items-center gap-4 mb-4 flex-wrap">
            <div className="flex gap-2">
              {FILTERS.map(f => (
                <button key={f} onClick={() => setFilter(f)}
                  className={`px-3 py-1 text-[10px] uppercase tracking-widest font-bold rounded-sm border transition-colors ${
                    filter === f ? 'bg-white text-black border-white' : 'text-zinc-400 border-zinc-700 hover:border-zinc-500 hover:text-white'
                  }`} style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                  {f}
                </button>
              ))}
            </div>
            <div className="flex gap-2 flex-wrap">
              {allMetrics.map(m => (
                <button key={m} onClick={() => setMetricFilter(m)}
                  className={`px-3 py-1 text-[10px] uppercase tracking-widest font-bold rounded-sm border transition-colors ${
                    metricFilter === m ? 'bg-white text-black border-white' : 'text-zinc-500 border-zinc-800 hover:border-zinc-600 hover:text-white'
                  }`} style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                  {m}
                </button>
              ))}
            </div>
            <button onClick={fetchData} className="ml-auto text-zinc-500 hover:text-white transition-colors">
              <RefreshCw size={14} strokeWidth={1.8} />
            </button>
          </div>

          {/* Error */}
          {error && <div className="mb-4 text-red-400 text-xs border border-red-500/30 bg-red-500/10 px-4 py-2 rounded-sm">{error}</div>}

          {/* Table */}
          {loading ? (
            <div className="flex justify-center py-16">
              <div className="w-5 h-5 border-2 border-zinc-700 border-t-white rounded-full animate-spin" />
            </div>
          ) : (
            <div className="border border-zinc-800 rounded-sm overflow-hidden">
              <table className="w-full text-sm border-collapse">
                <thead className="bg-zinc-900">
                  <tr className="border-b border-zinc-800">
                    {['Sensor', 'Zone', 'Metric', 'Latest Reading', 'Quality', 'Last Updated'].map(col => (
                      <th key={col} className="text-left px-4 py-2.5 text-zinc-500 font-semibold text-[10px] uppercase tracking-widest"
                        style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {visible.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-12 text-center text-zinc-600 text-xs">
                        {rows.length === 0 ? 'No sensor data in the database yet. Ingest some sensor data to see readings here.' : 'No readings match the current filter.'}
                      </td>
                    </tr>
                  ) : visible.map(s => {
                    const cfg    = QUALITY_CFG[s.quality]
                    const CatIcon = CATEGORY_ICON[s.category] ?? Activity
                    return (
                      <tr key={s.key} className="border-b border-zinc-800/60 hover:bg-zinc-900/50 transition-colors">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <Wifi size={12} className="text-emerald-500 shrink-0" />
                            <span className="text-white font-mono text-xs font-semibold">{s.sensor_id}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-zinc-400 text-xs">{s.zone}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1.5">
                            <CatIcon size={13} className="text-zinc-500 shrink-0" />
                            <span className="text-zinc-300 text-xs font-medium" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                              {s.category}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <BarGauge value={s.value} unit={s.unit} />
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-sm text-[10px] font-bold tracking-widest border ${cfg.badge}`}
                            style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                            {cfg.label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-zinc-500 text-xs font-mono">
                          {new Date(s.lastUpdated).toLocaleString('en-CA', { hour12: false }).slice(0, 16)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
