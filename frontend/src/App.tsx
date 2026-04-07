import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Accounts from './pages/admin/Accounts'
import Profile from './pages/Profile'
import AuditLog from './pages/AuditLog'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/"                element={<Navigate to="/login" replace />} />
          <Route path="/login"           element={<Login />} />
          <Route path="/dashboard"       element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/auditlog"       element={<ProtectedRoute><AuditLog /></ProtectedRoute>} />
          <Route path="/admin/accounts"  element={<ProtectedRoute adminOnly><Accounts /></ProtectedRoute>} />
          <Route path="/profile"         element={<ProtectedRoute><Profile /></ProtectedRoute>} />
          <Route path="*"                element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
