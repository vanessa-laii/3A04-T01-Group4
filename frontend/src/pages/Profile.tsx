import { useState } from 'react'
import { supabase } from '../lib/supabase'
import { useAuth } from '../context/AuthContext'
import Sidebar from '../components/layout/Sidebar'
import Header from '../components/layout/Header'

export default function Profile() {
  const { profile, refreshProfile } = useAuth()

  const [username, setUsername]       = useState(profile?.username ?? '')
  const [phone, setPhone]             = useState(profile?.phone_number ?? '')
  const [infoLoading, setInfoLoading] = useState(false)
  const [infoError, setInfoError]     = useState('')
  const [infoSuccess, setInfoSuccess] = useState('')

  const [currentPw, setCurrentPw]   = useState('')
  const [newPw, setNewPw]           = useState('')
  const [confirmPw, setConfirmPw]   = useState('')
  const [pwLoading, setPwLoading]   = useState(false)
  const [pwError, setPwError]       = useState('')
  const [pwSuccess, setPwSuccess]   = useState('')

  async function handleInfoSave(e: React.FormEvent) {
    e.preventDefault()
    setInfoError('')
    setInfoSuccess('')
    if (!profile) return
    setInfoLoading(true)

    const { error } = await supabase
      .from('account_information')
      .update({
        username,
        phone_number: phone || null,
        updated_at: new Date().toISOString(),
      })
      .eq('accountinfo_id', profile.accountinfo_id)

    setInfoLoading(false)

    if (error) {
      setInfoError(error.message)
      return
    }

    await refreshProfile()
    setInfoSuccess('Profile updated successfully.')
  }

  async function handlePasswordChange(e: React.FormEvent) {
    e.preventDefault()
    setPwError('')
    setPwSuccess('')

    if (newPw !== confirmPw) {
      setPwError('New passwords do not match.')
      return
    }
    if (newPw.length < 6) {
      setPwError('Password must be at least 6 characters.')
      return
    }

    setPwLoading(true)

    // Re-authenticate to verify current password
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email: profile?.email ?? '',
      password: currentPw,
    })

    if (signInError) {
      setPwLoading(false)
      setPwError('Current password is incorrect.')
      return
    }

    const { error } = await supabase.auth.updateUser({ password: newPw })
    setPwLoading(false)

    if (error) {
      setPwError(error.message)
      return
    }

    setCurrentPw('')
    setNewPw('')
    setConfirmPw('')
    setPwSuccess('Password changed successfully.')
  }

  return (
    <div className="flex h-screen bg-black overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <Header title="Profile" />

        <div className="flex-1 p-6 overflow-auto">
          <div className="max-w-lg space-y-6">

            {/* Read-only info */}
            <div className="border border-zinc-800 rounded-sm p-5 space-y-3">
              <h2 className="text-white text-xs font-bold uppercase tracking-widest mb-4" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                Account Info
              </h2>
              <div className="flex items-center justify-between">
                <span className="text-zinc-500 text-xs uppercase tracking-widest">Email</span>
                <span className="text-zinc-300 text-sm font-mono">{profile?.email}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-500 text-xs uppercase tracking-widest">Role</span>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-sm tracking-widest ${
                  profile?.role === 'System Administrator'
                    ? 'bg-white/10 text-white border border-white/20'
                    : 'bg-zinc-700 text-zinc-300 border border-zinc-600'
                }`} style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                  {profile?.role === 'System Administrator' ? 'ADMIN' : 'OPERATOR'}
                </span>
              </div>
            </div>

            {/* Edit profile info */}
            <div className="border border-zinc-800 rounded-sm p-5">
              <h2 className="text-white text-xs font-bold uppercase tracking-widest mb-4" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                Edit Profile
              </h2>
              <form onSubmit={handleInfoSave} className="space-y-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-zinc-400 text-xs uppercase tracking-widest font-medium">Username</label>
                  <input
                    type="text" value={username} required
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm px-3 py-2.5 rounded-sm outline-none focus:border-zinc-500 placeholder:text-zinc-600 transition-colors"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-zinc-400 text-xs uppercase tracking-widest font-medium">Phone</label>
                  <input
                    type="text" value={phone} placeholder="+1 416 000 0000 (optional)"
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm px-3 py-2.5 rounded-sm outline-none focus:border-zinc-500 placeholder:text-zinc-600 transition-colors"
                  />
                </div>
                {infoError   && <p className="text-red-400 text-xs border border-red-500/30 bg-red-500/10 px-3 py-2 rounded-sm">{infoError}</p>}
                {infoSuccess && <p className="text-emerald-400 text-xs border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 rounded-sm">{infoSuccess}</p>}
                <button
                  type="submit" disabled={infoLoading}
                  className="w-full bg-white text-black text-xs font-bold py-2.5 rounded-sm hover:bg-zinc-200 transition-colors disabled:opacity-50"
                  style={{ fontFamily: "'Space Grotesk', sans-serif" }}
                >
                  {infoLoading ? 'Saving…' : 'Save Changes'}
                </button>
              </form>
            </div>

            {/* Change password */}
            <div className="border border-zinc-800 rounded-sm p-5">
              <h2 className="text-white text-xs font-bold uppercase tracking-widest mb-4" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                Change Password
              </h2>
              <form onSubmit={handlePasswordChange} className="space-y-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-zinc-400 text-xs uppercase tracking-widest font-medium">Current Password</label>
                  <input
                    type="password" value={currentPw} required placeholder="••••••••"
                    onChange={(e) => setCurrentPw(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm px-3 py-2.5 rounded-sm outline-none focus:border-zinc-500 placeholder:text-zinc-600 transition-colors"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-zinc-400 text-xs uppercase tracking-widest font-medium">New Password</label>
                  <input
                    type="password" value={newPw} required placeholder="••••••••"
                    onChange={(e) => setNewPw(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm px-3 py-2.5 rounded-sm outline-none focus:border-zinc-500 placeholder:text-zinc-600 transition-colors"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-zinc-400 text-xs uppercase tracking-widest font-medium">Confirm New Password</label>
                  <input
                    type="password" value={confirmPw} required placeholder="••••••••"
                    onChange={(e) => setConfirmPw(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm px-3 py-2.5 rounded-sm outline-none focus:border-zinc-500 placeholder:text-zinc-600 transition-colors"
                  />
                </div>
                {pwError   && <p className="text-red-400 text-xs border border-red-500/30 bg-red-500/10 px-3 py-2 rounded-sm">{pwError}</p>}
                {pwSuccess && <p className="text-emerald-400 text-xs border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 rounded-sm">{pwSuccess}</p>}
                <button
                  type="submit" disabled={pwLoading}
                  className="w-full bg-white text-black text-xs font-bold py-2.5 rounded-sm hover:bg-zinc-200 transition-colors disabled:opacity-50"
                  style={{ fontFamily: "'Space Grotesk', sans-serif" }}
                >
                  {pwLoading ? 'Updating…' : 'Update Password'}
                </button>
              </form>
            </div>

          </div>
        </div>
      </div>
    </div>
  )
}
