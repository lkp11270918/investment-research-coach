'use client'

import { useState } from 'react'
import { Plus } from 'lucide-react'
import type { AuthUser } from '@/lib/api'

interface NavHeaderProps {
  activeTab: string
  onTabChange: (tab: string) => void
  isLoggedIn: boolean
  user: AuthUser | null
  onLogin: () => void
  onSignup: () => void
  onLogout: () => void
  onDeleteAccount: (password: string) => Promise<void>
  onNewResearch: () => void
}

export function NavHeader({
  activeTab,
  onTabChange,
  isLoggedIn,
  user,
  onLogin,
  onSignup,
  onLogout,
  onDeleteAccount,
  onNewResearch,
}: NavHeaderProps) {
  const [showAccountMenu, setShowAccountMenu] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [deletePassword, setDeletePassword] = useState('')
  const [deleteConfirmation, setDeleteConfirmation] = useState('')
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  const closeDeleteDialog = () => {
    if (deleting) return
    setShowDeleteDialog(false)
    setDeletePassword('')
    setDeleteConfirmation('')
    setDeleteError(null)
  }

  const confirmDeleteAccount = async () => {
    setDeleting(true)
    setDeleteError(null)
    try {
      await onDeleteAccount(deletePassword)
      setShowDeleteDialog(false)
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : '账户删除失败')
    } finally {
      setDeleting(false)
    }
  }

  const tabs = [
    { id: 'map', label: 'Research Map', disabled: false },
    { id: 'evidence', label: 'Evidence', disabled: false },
    { id: 'thesis', label: 'Thesis', disabled: false },
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

          <div className="flex items-center gap-2.5 shrink-0" aria-label="Research Coach">
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
          </div>

          {/* Nav tabs */}
          <nav className="flex min-w-0 items-center gap-2 overflow-x-auto" aria-label="产品功能">
            <div className="flex items-center gap-0.5 rounded-md border border-border/70 bg-black/10 p-0.5" aria-label="完整研究">
              <span className="px-2 text-[10px] font-medium text-muted-foreground">完整研究</span>
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
            </div>
            <div className="h-6 w-px shrink-0 bg-border" />
            <button
              type="button"
              onClick={() => onTabChange('review')}
              className="relative shrink-0 rounded-md border px-3 py-1.5 text-sm font-semibold transition-colors"
              style={{
                color: activeTab === 'review' ? 'oklch(0.10 0.005 240)' : 'oklch(0.72 0.08 195)',
                borderColor: 'oklch(0.45 0.08 195)',
                backgroundColor: activeTab === 'review' ? 'oklch(0.65 0.14 195)' : 'oklch(0.16 0.02 195)',
              }}
            >
              报告批改
            </button>
          </nav>

          {/* Right: auth state */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={onNewResearch}
              className="flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-white/5"
              style={{ color: 'oklch(0.75 0.01 240)', borderColor: 'oklch(0.25 0.01 240)' }}
            >
              <Plus className="h-3.5 w-3.5" />
              新建研究
            </button>
            {isLoggedIn ? (
              <>
                <button
                  type="button"
                  onClick={() => setShowAccountMenu(value => !value)}
                  className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs hover:bg-white/5"
                  style={{ color: 'oklch(0.55 0.01 240)' }}
                  aria-expanded={showAccountMenu}
                  aria-label="打开账户菜单"
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
                </button>
                {showAccountMenu && (
                  <div className="absolute right-20 top-12 w-56 rounded-lg border border-border bg-card p-2 shadow-xl">
                    <div className="border-b border-border px-2 py-2">
                      <div className="truncate text-xs font-medium text-foreground">{user?.name || '当前账户'}</div>
                      <div className="mt-0.5 truncate text-[11px] text-muted-foreground">{user?.email}</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setShowAccountMenu(false)
                        setShowDeleteDialog(true)
                      }}
                      className="mt-1 w-full rounded px-2 py-2 text-left text-xs text-destructive hover:bg-destructive/10"
                    >
                      删除账户
                    </button>
                  </div>
                )}
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
      {showDeleteDialog && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 px-4" role="dialog" aria-modal="true" aria-labelledby="delete-account-title">
          <div className="w-full max-w-md rounded-xl border border-destructive/30 bg-card p-5 shadow-2xl">
            <h2 id="delete-account-title" className="text-base font-semibold text-foreground">永久删除账户</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              删除后，账户、研究项目、上传资料、证据、报告版本、答辩记录和能力画像将无法恢复。
            </p>
            <label className="mt-4 block text-xs font-medium text-foreground">
              当前密码
              <input
                type="password"
                autoComplete="current-password"
                value={deletePassword}
                onChange={event => setDeletePassword(event.target.value)}
                className="mt-1.5 h-10 w-full rounded-md border border-border bg-input px-3 text-sm text-foreground outline-none focus:border-destructive"
              />
            </label>
            <label className="mt-3 block text-xs font-medium text-foreground">
              输入“删除账户”确认
              <input
                value={deleteConfirmation}
                onChange={event => setDeleteConfirmation(event.target.value)}
                className="mt-1.5 h-10 w-full rounded-md border border-border bg-input px-3 text-sm text-foreground outline-none focus:border-destructive"
              />
            </label>
            {deleteError && <div className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 p-2 text-xs text-destructive">{deleteError}</div>}
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={closeDeleteDialog} disabled={deleting} className="rounded-md border border-border px-3 py-2 text-xs text-muted-foreground hover:text-foreground disabled:opacity-50">
                取消
              </button>
              <button
                type="button"
                onClick={confirmDeleteAccount}
                disabled={deleting || !deletePassword || deleteConfirmation !== '删除账户'}
                className="rounded-md bg-destructive px-3 py-2 text-xs font-medium text-destructive-foreground hover:opacity-90 disabled:opacity-40"
              >
                {deleting ? '正在删除…' : '永久删除'}
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  )
}
