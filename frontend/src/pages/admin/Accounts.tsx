import { useState, useEffect } from 'react'
import { UserPlus, X, ToggleLeft, ToggleRight, Pencil } from 'lucide-react'
import { supabase } from '../../lib/supabase'
import { backendFetch } from '../../lib/api'
import Sidebar from '../../components/layout/Sidebar'
import Header from '../../components/layout/Header'

interface Operator {
  accountinfo_id: string
  user_id: string
  username: string
  email: string
  phone_number: string | null
  role: string
  is_active: boolean
  created_at: string
}

interface CreateForm {
  username: string
  email: string
  password: string
  phone_number: string
  role: 'City Operator' | 'System Administrator'
}

interface EditForm {
  username: string
  phone_number: string
  role: 'City Operator' | 'System Administrator'
}

const EMPTY_CREATE: CreateForm = { username: '', email: '', password: '', phone_number: '', role: 'City Operator' }

export default function Accounts() {
  const [operators, setOperators]     = useState<Operator[]>([])
  const [loadingList, setLoadingList] = useState(true)
  const [showCreate, setShowCreate]   = useState(false)
  const [editTarget, setEditTarget]   = useState<Operator | null>(null)
  const [createForm, setCreateForm]   = useState<CreateForm>(EMPTY_CREATE)
  const [editForm, setEditForm]       = useState<EditForm>({ username: '', phone_number: '', role: 'City Operator' })
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState('')
  const [success, setSuccess]         = useState('')

  useEffect(() => { fetchOperators() }, [])

  async function fetchOperators() {
    setLoadingList(true)
    const { data, error } = await supabase
      .from('account_information')
      .select('accountinfo_id, user_id, username, email, phone_number, role, is_active, created_at')
      .order('created_at', { ascending: false })
    if (!error && data) setOperators(data as Operator[])
    setLoadingList(false)
  }

  async function toggleActive(op: Operator) {
    const res = await backendFetch(`/api/v1/accounts/${op.user_id}`, {
      method: 'PATCH',
      body: JSON.stringify({ is_active: !op.is_active }),
    })
    if (res.ok) setOperators((prev) =>
      prev.map((o) => o.accountinfo_id === op.accountinfo_id ? { ...o, is_active: !o.is_active } : o)
    )
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)

    const res  = await backendFetch('/api/v1/accounts', {
      method: 'POST',
      body: JSON.stringify({
        username:     createForm.username,
        email:        createForm.email,
        password:     createForm.password,
        phone_number: createForm.phone_number || null,
        role:         createForm.role,
      }),
    })
    const data = await res.json()
    setLoading(false)

    if (!res.ok || !data.success) {
      setError(data?.message ?? 'Failed to create account')
      return
    }

    setSuccess(`Account "${createForm.username}" created successfully.`)
    setCreateForm(EMPTY_CREATE)
    setShowCreate(false)
    fetchOperators()
  }

  function openEdit(op: Operator) {
    setEditTarget(op)
    setEditForm({
      username: op.username,
      phone_number: op.phone_number ?? '',
      role: op.role as EditForm['role'],
    })
    setError('')
  }

  async function handleEdit(e: React.FormEvent) {
    e.preventDefault()
    if (!editTarget) return
    setError('')
    setLoading(true)

    const res  = await backendFetch(`/api/v1/accounts/${editTarget.user_id}`, {
      method: 'PATCH',
      body: JSON.stringify({
        username:     editForm.username,
        phone_number: editForm.phone_number || null,
        role:         editForm.role,
      }),
    })
    const data = await res.json()
    setLoading(false)

    if (!res.ok || !data.success) {
      setError(data?.message ?? 'Failed to update account')
      return
    }

    setSuccess(`Account "${editForm.username}" updated.`)
    setEditTarget(null)
    fetchOperators()
  }

  const ROLE_OPTIONS: { value: CreateForm['role']; label: string }[] = [
    { value: 'City Operator',        label: 'City Operator' },
    { value: 'System Administrator', label: 'System Administrator' },
  ]

  return (
    <div className="flex h-screen bg-black overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <Header title="Account Management" />

        <div className="flex-1 p-6 overflow-auto">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-white text-lg font-bold tracking-wide" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
              Accounts
            </h2>
            <button
              onClick={() => { setShowCreate(true); setError('') }}
              className="flex items-center gap-2 bg-white text-black text-xs font-bold px-4 py-2 rounded-sm hover:bg-zinc-200 transition-colors"
              style={{ fontFamily: "'Space Grotesk', sans-serif" }}
            >
              <UserPlus size={14} strokeWidth={2} /> Create Account
            </button>
          </div>

          {success && (
            <div className="mb-4 text-emerald-400 text-xs border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 rounded-sm">
              {success}
            </div>
          )}

          <div className="border border-zinc-800 rounded-sm overflow-hidden">
            <table className="w-full text-sm border-collapse">
              <thead className="bg-zinc-900">
                <tr className="border-b border-zinc-800">
                  {['Username', 'Email', 'Phone', 'Role', 'Created', 'Status', ''].map((col) => (
                    <th key={col} className="text-left px-4 py-2.5 text-zinc-500 font-semibold text-[10px] uppercase tracking-widest" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loadingList ? (
                  <tr><td colSpan={7} className="px-4 py-8 text-center">
                    <div className="flex justify-center"><div className="w-5 h-5 border-2 border-zinc-700 border-t-white rounded-full animate-spin" /></div>
                  </td></tr>
                ) : operators.length === 0 ? (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-zinc-600 text-xs">No accounts found.</td></tr>
                ) : (
                  operators.map((op) => (
                    <tr key={op.accountinfo_id} className="border-b border-zinc-800/60 hover:bg-zinc-900/50 transition-colors">
                      <td className="px-4 py-3 text-white text-xs font-medium">{op.username}</td>
                      <td className="px-4 py-3 text-zinc-400 text-xs">{op.email}</td>
                      <td className="px-4 py-3 text-zinc-400 text-xs">{op.phone_number ?? '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-sm tracking-widest ${
                          op.role === 'System Administrator'
                            ? 'bg-white/10 text-white border border-white/20'
                            : 'bg-zinc-700 text-zinc-300 border border-zinc-600'
                        }`} style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                          {op.role === 'System Administrator' ? 'ADMIN' : 'OPERATOR'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-zinc-500 text-xs font-mono">
                        {new Date(op.created_at).toLocaleDateString('en-CA')}
                      </td>
                      <td className="px-4 py-3">
                        <button onClick={() => toggleActive(op)} className="flex items-center gap-1.5 text-xs transition-colors">
                          {op.is_active
                            ? <><ToggleRight size={18} strokeWidth={1.8} className="text-emerald-400" /><span className="text-emerald-400">Active</span></>
                            : <><ToggleLeft size={18} strokeWidth={1.8} className="text-zinc-600" /><span className="text-zinc-600">Inactive</span></>
                          }
                        </button>
                      </td>
                      <td className="px-4 py-3">
                        <button onClick={() => openEdit(op)} className="text-zinc-500 hover:text-white transition-colors">
                          <Pencil size={14} strokeWidth={1.8} />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <Modal title="New Account" onClose={() => setShowCreate(false)}>
          <form onSubmit={handleCreate} className="flex flex-col gap-4">
            <Field label="Username" type="text" value={createForm.username} placeholder="John Doe" required
              onChange={(v) => setCreateForm((f) => ({ ...f, username: v }))} />
            <Field label="Email" type="email" value={createForm.email} placeholder="user@scemas.ca" required
              onChange={(v) => setCreateForm((f) => ({ ...f, email: v }))} />
            <Field label="Password" type="password" value={createForm.password} placeholder="••••••••" required
              onChange={(v) => setCreateForm((f) => ({ ...f, password: v }))} />
            <Field label="Phone" type="text" value={createForm.phone_number} placeholder="+1 416 000 0000 (optional)"
              onChange={(v) => setCreateForm((f) => ({ ...f, phone_number: v }))} />
            <div className="flex flex-col gap-1.5">
              <label className="text-zinc-400 text-xs uppercase tracking-widest font-medium">Role</label>
              <select
                value={createForm.role}
                onChange={(e) => setCreateForm((f) => ({ ...f, role: e.target.value as CreateForm['role'] }))}
                className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm px-3 py-2.5 rounded-sm outline-none focus:border-zinc-500 transition-colors"
              >
                {ROLE_OPTIONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </div>
            {error && <ErrorMsg msg={error} />}
            <ModalActions onCancel={() => setShowCreate(false)} loading={loading} label="Create Account" />
          </form>
        </Modal>
      )}

      {/* Edit Modal */}
      {editTarget && (
        <Modal title={`Edit — ${editTarget.username}`} onClose={() => setEditTarget(null)}>
          <form onSubmit={handleEdit} className="flex flex-col gap-4">
            <Field label="Username" type="text" value={editForm.username} placeholder="John Doe" required
              onChange={(v) => setEditForm((f) => ({ ...f, username: v }))} />
            <Field label="Phone" type="text" value={editForm.phone_number} placeholder="+1 416 000 0000 (optional)"
              onChange={(v) => setEditForm((f) => ({ ...f, phone_number: v }))} />
            <div className="flex flex-col gap-1.5">
              <label className="text-zinc-400 text-xs uppercase tracking-widest font-medium">Role</label>
              <select
                value={editForm.role}
                onChange={(e) => setEditForm((f) => ({ ...f, role: e.target.value as EditForm['role'] }))}
                className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm px-3 py-2.5 rounded-sm outline-none focus:border-zinc-500 transition-colors"
              >
                {ROLE_OPTIONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </div>
            {error && <ErrorMsg msg={error} />}
            <ModalActions onCancel={() => setEditTarget(null)} loading={loading} label="Save Changes" />
          </form>
        </Modal>
      )}
    </div>
  )
}

/* ── Shared sub-components ── */

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-zinc-900 border border-zinc-800 rounded-sm w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-white text-sm font-bold tracking-wide uppercase" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
            {title}
          </h3>
          <button onClick={onClose} className="text-zinc-500 hover:text-white transition-colors">
            <X size={16} strokeWidth={1.8} />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

function Field({ label, type, value, placeholder, required, onChange }: {
  label: string; type: string; value: string; placeholder: string; required?: boolean; onChange: (v: string) => void
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-zinc-400 text-xs uppercase tracking-widest font-medium">{label}</label>
      <input
        type={type} value={value} placeholder={placeholder} required={required}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm px-3 py-2.5 rounded-sm outline-none focus:border-zinc-500 placeholder:text-zinc-600 transition-colors"
      />
    </div>
  )
}

function ErrorMsg({ msg }: { msg: string }) {
  return <p className="text-red-400 text-xs border border-red-500/30 bg-red-500/10 px-3 py-2 rounded-sm">{msg}</p>
}

function ModalActions({ onCancel, loading, label }: { onCancel: () => void; loading: boolean; label: string }) {
  return (
    <div className="flex gap-3 mt-1">
      <button type="button" onClick={onCancel}
        className="flex-1 border border-zinc-700 text-zinc-400 text-xs font-bold py-2.5 rounded-sm hover:text-white hover:border-zinc-500 transition-colors"
        style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
        Cancel
      </button>
      <button type="submit" disabled={loading}
        className="flex-1 bg-white text-black text-xs font-bold py-2.5 rounded-sm hover:bg-zinc-200 transition-colors disabled:opacity-50"
        style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
        {loading ? 'Saving…' : label}
      </button>
    </div>
  )
}
