import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { User } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8005'

interface Profile {
  accountinfo_id: string
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

  // async function signIn(email: string, password: string): Promise<{ error: string | null }> {
  //   const { data, error } = await supabase.auth.signInWithPassword({ email, password })

  //   if (error) return { error: 'Invalid email or password.' }

  //   const prof = await fetchProfile(data.user.id)

  //   if (!prof) {
  //     await supabase.auth.signOut()
  //     return { error: 'Access denied — no account profile found.' }
  //   }

  //   if (!prof.is_active) {
  //     await supabase.auth.signOut()
  //     return { error: 'Access denied — account is inactive.' }
  //   }

  //   setUser(data.user)
  //   setProfile(prof)
  //   return { error: null }
  // }

  async function signIn(email: string, password: string): Promise<{ error: string | null }> {
    try {
      console.log(email)
      console.log(password)
      const response = await fetch('http://localhost:8005/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username:email, password:password }),
      });

      console.log(response)

      // if (!response.ok) {
      //   const errorData = await response.json();
      //   return { error: errorData.detail || 'Invalid username or password.' };
      // }

      const data = await response.json();

      if (data.success) {
        setUser({ id: data.accountinfo_id, email: data.email, app_metadata: {}, user_metadata: {}, aud: "authenticated", created_at: "" });
        setProfile({
          accountinfo_id: data.accountinfo_id,
          username:       data.username,
          email:          data.email,
          role:           data.role,
          phone_number:   null,
          is_active:      true,
        });
        return { error: null };
      } else {
        return { error: data.message || 'Login failed.' };
      }
    } catch (err) {
      console.error('Connection error:', err);
      return { error: 'Could not connect to the authentication service.' };
    }
  }

  async function signOut() {
    await supabase.auth.signOut()
    setUser(null)
    setProfile(null)
  }

  async function refreshProfile() {
    if (!user) return
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/accounts/${user.id}`)
      if (!res.ok) return
      const data = await res.json()
      const acc = data.account_info
      setProfile({
        accountinfo_id: acc.accountinfo_id,
        username:       acc.username,
        email:          acc.email,
        role:           acc.role,
        phone_number:   acc.phone_number ?? null,
        is_active:      acc.is_active,
      })
    } catch { /* ignore */ }
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
