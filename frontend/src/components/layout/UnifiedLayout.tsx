import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { useLocalBridgeWS } from '../../hooks/useLocalBridgeWS'
import UnifiedHeader from './UnifiedHeader'
import NavTabs from './NavTabs'
import StatusBar from './StatusBar'
import MobileMenu from './MobileMenu'

export default function UnifiedLayout() {
  useLocalBridgeWS()

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-[#0a0a1a] text-gray-200 flex flex-col">
      <UnifiedHeader onMenuOpen={() => setMobileMenuOpen(true)} />
      <NavTabs />

      <main className="flex-1 w-full max-w-[1100px] mx-auto px-4 md:px-8 py-6">
        <Outlet />
      </main>

      <StatusBar />
      <MobileMenu open={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} />
    </div>
  )
}
