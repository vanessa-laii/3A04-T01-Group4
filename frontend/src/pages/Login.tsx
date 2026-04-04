import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Lock, Mail, Eye, EyeOff, ShieldCheck } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const navigate = useNavigate()
  const { signIn } = useAuth()

  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)

    const { error: authError } = await signIn(email.trim().toLowerCase(), password)

    if (authError) {
      setError(authError)
      setLoading(false)
      return
    }

    navigate('/dashboard')
  }

  return (
    <div className="min-h-screen bg-black flex flex-col items-center justify-center px-4">
      {/* Logo */}
      <div className="mb-8 text-center">
        <h1
          className="text-white text-3xl font-bold tracking-widest"
          style={{ fontFamily: "'Space Grotesk', sans-serif" }}
        >
          SCEMAS
        </h1>
        <p className="text-zinc-500 text-xs mt-1 tracking-widest uppercase">
          Smart City Environmental Monitoring
        </p>
      </div>

      {/* Card */}
      <div className="w-full max-w-sm bg-zinc-900 border border-zinc-800 rounded-sm p-8">
        <div className="flex items-center gap-2 mb-6">
          <ShieldCheck size={18} strokeWidth={1.8} className="text-zinc-400" />
          <span
            className="text-white text-sm font-semibold tracking-wide uppercase"
            style={{ fontFamily: "'Space Grotesk', sans-serif" }}
          >
            Operator Sign In
          </span>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Email */}
          <div className="flex flex-col gap-1.5">
            <label className="text-zinc-400 text-xs uppercase tracking-widest font-medium">
              Email
            </label>
            <div className="relative">
              <Mail size={14} strokeWidth={1.8} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@scemas.ca"
                className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm pl-9 pr-3 py-2.5 rounded-sm outline-none focus:border-zinc-500 placeholder:text-zinc-600 transition-colors"
              />
            </div>
          </div>

          {/* Password */}
          <div className="flex flex-col gap-1.5">
            <label className="text-zinc-400 text-xs uppercase tracking-widest font-medium">
              Password
            </label>
            <div className="relative">
              <Lock size={14} strokeWidth={1.8} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none" />
              <input
                type={showPass ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm pl-9 pr-10 py-2.5 rounded-sm outline-none focus:border-zinc-500 placeholder:text-zinc-600 transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPass((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                {showPass ? <EyeOff size={14} strokeWidth={1.8} /> : <Eye size={14} strokeWidth={1.8} />}
              </button>
            </div>
          </div>

          {/* Error */}
          {error && (
            <p className="text-red-400 text-xs border border-red-500/30 bg-red-500/10 px-3 py-2 rounded-sm">
              {error}
            </p>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="mt-1 w-full bg-white text-black text-sm font-bold py-2.5 rounded-sm hover:bg-zinc-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed tracking-wide"
            style={{ fontFamily: "'Space Grotesk', sans-serif" }}
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        <p className="text-zinc-600 text-xs text-center mt-6">
          Access restricted to authorized personnel only.
        </p>
      </div>
    </div>
  )
}
