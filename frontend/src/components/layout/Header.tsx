import { LogOut } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

interface HeaderProps {
  title: string
}

export default function Header({ title }: HeaderProps) {
  const navigate = useNavigate()

  const raw = sessionStorage.getItem('scemas_user')
  const user = raw ? JSON.parse(raw) as { email: string; role: string } : null

  function handleSignOut() {
    sessionStorage.removeItem('scemas_user')
    navigate('/login')
  }

  return (
    <header className="h-12 shrink-0 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between px-6">
      <h1
        className="text-white text-sm font-semibold tracking-widest uppercase"
        style={{ fontFamily: "'Space Grotesk', sans-serif" }}
      >
        {title}
      </h1>

      <div className="flex items-center gap-4">
        <span className="text-zinc-500 text-xs tracking-wide">
          {new Date().toLocaleDateString('en-CA', {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric',
          })}
        </span>

        {user && (
          <>
            <span className="text-zinc-400 text-xs font-medium" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
              {user.email.split('@')[0]}
            </span>
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-sm tracking-widest ${
              user.role === 'admin'
                ? 'bg-white/10 text-white border border-white/20'
                : 'bg-zinc-700 text-zinc-300 border border-zinc-600'
            }`}>
              {user.role.toUpperCase()}
            </span>
          </>
        )}

        <button
          onClick={handleSignOut}
          className="text-zinc-500 hover:text-white transition-colors"
          title="Sign out"
        >
          <LogOut size={16} strokeWidth={1.8} />
        </button>
      </div>
    </header>
  )
}
