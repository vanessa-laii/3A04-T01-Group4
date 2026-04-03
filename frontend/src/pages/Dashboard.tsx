import { Clock, AlertTriangle, Wifi } from 'lucide-react'
import Sidebar from '../components/layout/Sidebar'
import Header from '../components/layout/Header'
import StatCard from '../components/dashboard/StatCard'
import MapView from '../components/dashboard/MapView'
import AlertsTable from '../components/dashboard/AlertsTable'

const STATS = [
  { label: 'Pending',        value: 2,   Icon: Clock,          iconColor: 'text-amber-400', valueColor: 'text-amber-400' },
  { label: 'Active Alerts',  value: 2,   Icon: AlertTriangle,  iconColor: 'text-red-400',   valueColor: 'text-red-400'   },
  { label: 'Sensors Online', value: 103, Icon: Wifi,           iconColor: 'text-emerald-400', valueColor: 'text-white'   },
]

export default function Dashboard() {
  return (
    <div className="flex h-screen bg-black overflow-hidden">
      <Sidebar />

      <div className="flex flex-col flex-1 min-w-0">
        <Header title="311 Operations Center Dashboard" />

        {/* Map + stat cards */}
        <div className="flex flex-1 min-h-0">
          <div className="flex flex-1 min-h-0 min-w-0">
            {/* Map */}
            <div className="flex-1 min-w-0">
              <MapView />
            </div>

            {/* Stat cards */}
            <div className="w-44 shrink-0 bg-black border-l border-zinc-800 flex flex-col gap-2 p-3 pt-4">
              {STATS.map((s) => (
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
            <span
              className="text-zinc-300 text-xs uppercase tracking-widest font-semibold"
              style={{ fontFamily: "'Space Grotesk', sans-serif" }}
            >
              Recent Alerts
            </span>
            <span className="text-zinc-600 text-xs">Mock data — Supabase integration pending</span>
          </div>
          <div className="h-[calc(100%-33px)]">
            <AlertsTable />
          </div>
        </div>
      </div>
    </div>
  )
}
