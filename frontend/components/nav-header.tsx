'use client'

import type { AuthUser } from '@/lib/api'

interface NavHeaderProps {
  activeTab: string
  onTabChange: (tab: string) => void
  onBackToHome: () => void
  isLoggedIn: boolean
  user: AuthUser | null
  hasAnalysisData: boolean
  onLogin: () => void
  onSignup: () => void
  onLogout: () => void
}

export function NavHeader({
  activeTab,
  onTabChange,
  onBackToHome,
  isLoggedIn,
  user,
  hasAnalysisData,
  onLogin,
  onSignup,
  onLogout,
}: NavHeaderProps) {
  const tabs = [
    { id: 'map', label: 'Research Map', disabled: false },
    { id: 'evidence', label: 'Evidence', disabled: false },
    { id: 'thesis', label: 'Thesis', disabled: false },
    { id: 'memo', label: 'Memo', disabled: !hasAnalysisData },
    { id: 'defense', label: 'Defense & Feedback', disabled: false },
  ]
  return (
    <header
      className="sticky top-0 z-50 border-b"
      style={{
        borderColor: 'oklch(0.22 0.01 240)',
        backgroundColor: 'oklch(0.10 0.005 240 / 0.97)',
        backdropFilter: 'blur(12px)',
      }}
    >
      <div className="mx-auto max-w-screen-2xl px-6">
        <div className="flex h-14 items-center justify-between gap-6">

          {/* Logo — clickable to go back to home */}
          <button
            onClick={onBackToHome}
            className="flex items-center gap-2.5 shrink-0 transition-opacity hover:opacity-80"
          >
            <div
              className="flex h-6 w-6 items-center justify-center rounded"
              style={{ backgroundColor: 'oklch(0.65 0.14 195)' }}
            >
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                <path d="M3 12L6 7L9 9.5L12 4" stroke="oklch(0.10 0.005 240)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx="12" cy="4" r="1.5" fill="oklch(0.10 0.005 240)"/>
              </svg>
            </div>
            <span className="text-sm font-semibold" style={{ color: 'oklch(0.93 0.005 240)' }}>
              Research Coach
            </span>
          </button>

          {/* Nav tabs */}
          <nav className="flex min-w-0 items-center gap-0.5 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => !tab.disabled && onTabChange(tab.id)}
                disabled={tab.disabled}
                title={tab.disabled ? '请先完成资料输入并开始分析' : undefined}
                className="relative px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-150"
                style={{
                  color: tab.disabled
                    ? 'oklch(0.35 0.01 240)'
                    : activeTab === tab.id
                    ? 'oklch(0.93 0.005 240)'
                    : 'oklch(0.55 0.01 240)',
                  backgroundColor: activeTab === tab.id && !tab.disabled ? 'oklch(0.22 0.015 240)' : 'transparent',
                  cursor: tab.disabled ? 'not-allowed' : 'pointer',
                }}
                onMouseEnter={e => {
                  if (!tab.disabled && activeTab !== tab.id) e.currentTarget.style.color = 'oklch(0.80 0.005 240)'
                }}
                onMouseLeave={e => {
                  if (!tab.disabled && activeTab !== tab.id) e.currentTarget.style.color = 'oklch(0.55 0.01 240)'
                }}
              >
                {tab.label}
                {activeTab === tab.id && !tab.disabled && (
                  <span
                    className="absolute bottom-0 left-1/2 -translate-x-1/2 h-0.5 w-4 rounded-full"
                    style={{ backgroundColor: 'oklch(0.65 0.14 195)' }}
                  />
                )}
              </button>
            ))}
          </nav>

          {/* Right: auth state */}
          <div className="flex items-center gap-2 shrink-0">
            {isLoggedIn ? (
              <>
                <div
                  className="flex items-center gap-1.5 text-xs"
                  style={{ color: 'oklch(0.55 0.01 240)' }}
                >
                  <div
                    className="h-6 w-6 rounded-full flex items-center justify-center text-[10px] font-semibold"
                    style={{
                      backgroundColor: 'oklch(0.65 0.14 195 / 0.2)',
                      color: 'oklch(0.65 0.14 195)',
                    }}
                  >
                    {(user?.name || user?.email || 'U').slice(0, 1).toUpperCase()}
                  </div>
                  <span className="hidden lg:inline max-w-40 truncate">{user?.name || user?.email}</span>
                </div>
                <button
                  onClick={onLogout}
                  className="text-xs px-3 py-1.5 rounded-md border transition-colors"
                  style={{
                    color: 'oklch(0.55 0.01 240)',
                    borderColor: 'oklch(0.25 0.01 240)',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.color = 'oklch(0.80 0.005 240)'
                    e.currentTarget.style.borderColor = 'oklch(0.40 0.01 240)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.color = 'oklch(0.55 0.01 240)'
                    e.currentTarget.style.borderColor = 'oklch(0.25 0.01 240)'
                  }}
                >
                  退出
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={onLogin}
                  className="text-xs px-3 py-1.5 rounded-md transition-colors"
                  style={{ color: 'oklch(0.65 0.01 240)' }}
                  onMouseEnter={e => (e.currentTarget.style.color = 'oklch(0.90 0.005 240)')}
                  onMouseLeave={e => (e.currentTarget.style.color = 'oklch(0.65 0.01 240)')}
                >
                  登录
                </button>
                <button
                  onClick={onSignup}
                  className="text-xs px-3 py-1.5 rounded-md font-medium transition-opacity hover:opacity-85"
                  style={{
                    backgroundColor: 'oklch(0.65 0.14 195)',
                    color: 'oklch(0.10 0.005 240)',
                  }}
                >
                  注册
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
