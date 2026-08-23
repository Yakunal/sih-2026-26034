/*
  App.tsx — the shell: navigation bar, routed page, footer.
*/

import { NavLink, Route, Routes } from 'react-router-dom'
import { ClipboardCheck, Gauge, History, ScanLine, Scale } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import Scan from './pages/Scan'
import Result from './pages/Result'
import HistoryPage from './pages/History'
import Rules from './pages/Rules'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', Icon: Gauge },
  { to: '/scan', label: 'Scan', Icon: ScanLine },
  { to: '/history', label: 'History', Icon: History },
  { to: '/rules', label: 'Rules', Icon: ClipboardCheck },
]

function Nav() {
  return (
    <header className="bg-ink">
      <nav className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
        <NavLink to="/" className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-lg bg-primary">
            <Scale className="h-6 w-6 text-white" strokeWidth={2.5} />
          </span>
          <span className="leading-tight">
            <span className="block font-extrabold tracking-tight text-white">Legal Metrology Checker</span>
            <span className="block text-xs font-medium tracking-wider text-gray-400 uppercase">
              Packaged Commodities Rules, 2011
            </span>
          </span>
        </NavLink>

        <ul className="flex flex-wrap items-center gap-1">
          {NAV_ITEMS.map(({ to, label, Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all duration-200 ${
                    isActive ? 'bg-primary text-white' : 'text-gray-300 hover:bg-white/10 hover:text-white'
                  }`
                }
              >
                <Icon className="h-4 w-4" strokeWidth={2.5} />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  )
}

function Footer() {
  return (
    <footer className="bg-ink">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <p className="max-w-4xl text-sm leading-relaxed text-gray-400">
          <span className="font-bold text-white">Prototype — decision support only.</span> This system flags
          declarations that appear to be missing or not in the prescribed form. It does not replace an official
          inspection or a legal determination, and it cannot assess declarations printed on panels that are not
          visible in the photograph.
        </p>
        <p className="mt-4 text-xs tracking-wider text-gray-500 uppercase">
          Built for SIH 26034 &nbsp;·&nbsp; Gemini reads the label, a deterministic rule engine decides
        </p>
      </div>
    </footer>
  )
}

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Nav />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/scan" element={<Scan />} />
          <Route path="/result/:id" element={<Result />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/rules" element={<Rules />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
