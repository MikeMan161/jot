import { useState } from 'react'
import { Routes, Route } from 'react-router'
import LoginPage from './pages/Login'
import Dashboard from './pages/Dashboard'
import LandingPage from './pages/LandingPage'
import Register from './pages/Register'
import Buckets from './pages/Buckets'
import Transactions from './pages/Transactions'
import GoalsAndDebts from './pages/GoalsAndDebts'
import UserPage from './pages/User'
import AppLayout from './components/AppLayout'

export default function App() {
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem("token")
  )
  
  function saveToken(newToken: string) {
    localStorage.setItem("token", newToken)
    setToken(newToken)
  }

  function clearToken() {
    localStorage.removeItem("token")
    setToken(null)
  }
  return (
    <Routes>
      <Route path="/" element={<LandingPage setToken={saveToken} />} />
      <Route path="/Login" element={<LoginPage setToken={saveToken} />} />
      <Route path="/SignUp" element={<Register setToken={saveToken} />} />

      <Route element ={<AppLayout token={token} />} >
        <Route path="/Dashboard" element={<Dashboard token={token} clearToken={clearToken} />} />
        <Route path="/Buckets" element={<Buckets token={token} clearToken={clearToken} />} />
        <Route path="/Transactions/:bucketId?" element={<Transactions token={token} clearToken={clearToken} />} />
        <Route path="/GoalsAndDebts" element={<GoalsAndDebts token={token} clearToken={clearToken} />} />
        <Route path="/User" element={<UserPage token={token} clearToken={clearToken} />} />
      </Route>
    </Routes>
      
  );
}