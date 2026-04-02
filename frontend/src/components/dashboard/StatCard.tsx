import { type LucideIcon } from 'lucide-react'

interface StatCardProps {
  label: string
  value: number | string
  Icon: LucideIcon
  iconColor?: string
  valueColor?: string
}

export default function StatCard({ label, value, Icon, iconColor = 'text-white', valueColor = 'text-white' }: StatCardProps) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-sm p-4 flex flex-col items-center justify-center gap-1.5 min-h-[90px]">
      <Icon size={20} strokeWidth={1.8} className={iconColor} />
      <span
        className={`text-3xl font-bold leading-none tracking-tight ${valueColor}`}
        style={{ fontFamily: "'Space Grotesk', sans-serif" }}
      >
        {value}
      </span>
      <span className="text-zinc-400 text-[10px] uppercase tracking-widest font-medium">
        {label}
      </span>
    </div>
  )
}
