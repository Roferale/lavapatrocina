'use client'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { LayoutDashboard, Camera, List, BarChart2, Users, Settings, FileText, LogOut } from 'lucide-react'
import { clearAuth, getCurrentUser } from '@/lib/auth'
import { cn } from '@/lib/utils'

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/cameras', label: 'Câmeras', icon: Camera },
  { href: '/events', label: 'Eventos', icon: List },
  { href: '/reports', label: 'Relatórios', icon: BarChart2 },
  { href: '/users', label: 'Usuários', icon: Users },
  { href: '/settings', label: 'Configurações', icon: Settings },
  { href: '/logs', label: 'Logs', icon: FileText },
]

export default function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const user = getCurrentUser()

  function handleLogout() {
    clearAuth()
    router.push('/login')
  }

  return (
    <aside className="w-56 min-h-screen bg-gray-900 text-white flex flex-col">
      <div className="px-4 py-5 border-b border-gray-700">
        <h1 className="text-lg font-bold">🚗 LavaJato</h1>
        <p className="text-xs text-gray-400 mt-0.5">Contagem de Veículos</p>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition',
              pathname.startsWith(href)
                ? 'bg-blue-600 text-white'
                : 'text-gray-300 hover:bg-gray-800 hover:text-white'
            )}
          >
            <Icon size={16} />
            {label}
          </Link>
        ))}
      </nav>
      <div className="px-4 py-4 border-t border-gray-700">
        <div className="text-xs text-gray-400 mb-2 truncate">{user?.email as string || ''}</div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition w-full"
        >
          <LogOut size={14} />
          Sair
        </button>
      </div>
    </aside>
  )
}
