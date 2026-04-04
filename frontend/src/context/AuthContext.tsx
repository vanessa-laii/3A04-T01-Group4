import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { User } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'

interface Profile {
  accountinfo_id: string
  user_id: string
  username: string
  email: string
  phone_number: string | null
  role: 'System Administrator' | 'City Operator'
  is_active: boolean
}

interface AuthContextType {
  user: User | null
  profile: Profile | null
  role: 'System Administrator' | 'City Operator' | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<{ error: string | null }>
  signOut: () => Promise<void>
  refreshProfile: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

async function fetchProfile(userId: string): Promise<Profile | null> {
  const { data, error } = await supabase
    .from('account_information')
    .select('*')
    .eq('user_id', userId)
    .single()
  if (error || !data) return null
  return data as Profile
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser]       = useState<User | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Restore existing session on mount
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (session?.user) {
        const prof = await fetchProfile(session.user.id)
        setUser(session.user)
        setProfile(prof)
      }
      setLoading(false)
    })

    // Only handle sign-out via listener
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        setUser(null)
        setProfile(null)
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  async function signIn(email: string, password: string): Promise<{ error: string | null }> {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password })

    if (error) return { error: 'Invalid email or password.' }

    const prof = await fetchProfile(data.user.id)

    if (!prof) {
      await supabase.auth.signOut()
      return { error: 'Access denied — no account profile found.' }
    }

    if (!prof.is_active) {
      await supabase.auth.signOut()
      return { error: 'Access denied — account is inactive.' }
    }

    setUser(data.user)
    setProfile(prof)
    return { error: null }
  }

  async function signOut() {
    await supabase.auth.signOut()
    setUser(null)
    setProfile(null)
  }

  async function refreshProfile() {
    if (!user) return
    const prof = await fetchProfile(user.id)
    setProfile(prof)
  }

  return (
    <AuthContext.Provider value={{
      user,
      profile,
      role: profile?.role ?? null,
      loading,
      signIn,
      signOut,
      refreshProfile,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
