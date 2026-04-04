import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  BellRing,
  RadioTower,
  ScrollText,
  UserCircle,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

interface NavItem {
  label: string
  path: string
  Icon: LucideIcon
  adminOnly?: boolean
}

const navItems: NavItem[] = [
  { label: 'Dashboard', path: '/dashboard',      Icon: LayoutDashboard },
  { label: 'Alerts',    path: '/alerts',          Icon: BellRing },
  { label: 'Sensors',   path: '/sensors',         Icon: RadioTower },
  { label: 'Audit Log', path: '/logs',            Icon: ScrollText },
  { label: 'Accounts',  path: '/admin/accounts',  Icon: Users, adminOnly: true },
  { label: 'Profile',   path: '/profile',          Icon: UserCircle },
]

export default function Sidebar() {
  const { role } = useAuth()

  return (
    <aside className="w-52 shrink-0 bg-zinc-900 border-r border-zinc-800 flex flex-col h-full">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-zinc-800">
        <span
          className="text-white font-bold text-xl tracking-widest"
          style={{ fontFamily: "'Space Grotesk', sans-serif" }}
        >
          SCEMAS
        </span>
        <p className="text-zinc-500 text-xs mt-0.5 tracking-wide">Operations Center</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3">
        {navItems.filter(item => !item.adminOnly || role === 'System Administrator').map(({ label, path, Icon }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-zinc-800 text-white border-l-2 border-white'
                  : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50 border-l-2 border-transparent'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon
                  size={17}
                  strokeWidth={isActive ? 2.2 : 1.8}
                  className="shrink-0"
                />
                <span style={{ fontFamily: "'Space Grotesk', sans-serif", letterSpacing: '0.02em' }}>
                  {label}
                </span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-zinc-800 text-zinc-600 text-xs tracking-wide">
        SE 3A04 · Group 4
      </div>
    </aside>
  )
}
