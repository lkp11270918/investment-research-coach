'use client'

import { useState } from 'react'

type AuthMode = 'login' | 'signup'

interface AuthModalProps {
  mode: AuthMode
  onClose: () => void
  onSuccess: () => void
  onSwitchMode: (mode: AuthMode) => void
}

export function AuthModal({ mode, onClose, onSuccess, onSwitchMode }: AuthModalProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    // Placeholder: direct success for now
    setTimeout(() => {
      setLoading(false)
      onSuccess()
    }, 800)
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ backgroundColor: 'oklch(0.05 0.003 240 / 0.85)', backdropFilter: 'blur(8px)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        className="w-full max-w-sm rounded-2xl border p-8 relative"
        style={{
          backgroundColor: 'oklch(0.13 0.008 240)',
          borderColor: 'oklch(0.25 0.01 240)',
        }}
      >
        {/* Close */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 h-7 w-7 flex items-center justify-center rounded-md transition-colors"
          style={{ color: 'oklch(0.50 0.01 240)' }}
          onMouseEnter={e => (e.currentTarget.style.color = 'oklch(0.80 0.005 240)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'oklch(0.50 0.01 240)')}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
        </button>

        {/* Logo */}
        <div className="flex items-center gap-2 mb-6">
          <div
            className="flex h-6 w-6 items-center justify-center rounded"
            style={{ backgroundColor: 'oklch(0.65 0.14 195)' }}
          >
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
              <path d="M3 12L6 7L9 9.5L12 4" stroke="oklch(0.10 0.005 240)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
              <circle cx="12" cy="4" r="1.5" fill="oklch(0.10 0.005 240)"/>
            </svg>
          </div>
          <span className="text-sm font-semibold" style={{ color: 'oklch(0.93 0.005 240)' }}>Research Coach</span>
        </div>

        {/* Title */}
        <h2 className="text-xl font-bold mb-1" style={{ color: 'oklch(0.93 0.005 240)' }}>
          {mode === 'login' ? '欢迎回来' : '创建账户'}
        </h2>
        <p className="text-sm mb-6" style={{ color: 'oklch(0.55 0.01 240)' }}>
          {mode === 'login' ? '登录后访问你的研究记录' : '免费开始你的价值投资研究训练'}
        </p>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'signup' && (
            <div>
              <label className="block text-xs mb-1.5" style={{ color: 'oklch(0.65 0.01 240)' }}>姓名</label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="你的姓名"
                className="w-full rounded-lg px-3 py-2.5 text-sm outline-none transition-all"
                style={{
                  backgroundColor: 'oklch(0.17 0.009 240)',
                  border: '1px solid oklch(0.25 0.01 240)',
                  color: 'oklch(0.93 0.005 240)',
                }}
                onFocus={e => (e.currentTarget.style.borderColor = 'oklch(0.65 0.14 195 / 0.6)')}
                onBlur={e => (e.currentTarget.style.borderColor = 'oklch(0.25 0.01 240)')}
              />
            </div>
          )}

          <div>
            <label className="block text-xs mb-1.5" style={{ color: 'oklch(0.65 0.01 240)' }}>邮箱</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              className="w-full rounded-lg px-3 py-2.5 text-sm outline-none transition-all"
              style={{
                backgroundColor: 'oklch(0.17 0.009 240)',
                border: '1px solid oklch(0.25 0.01 240)',
                color: 'oklch(0.93 0.005 240)',
              }}
              onFocus={e => (e.currentTarget.style.borderColor = 'oklch(0.65 0.14 195 / 0.6)')}
              onBlur={e => (e.currentTarget.style.borderColor = 'oklch(0.25 0.01 240)')}
            />
          </div>

          <div>
            <label className="block text-xs mb-1.5" style={{ color: 'oklch(0.65 0.01 240)' }}>密码</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder={mode === 'signup' ? '至少 8 位' : '输入密码'}
              required
              className="w-full rounded-lg px-3 py-2.5 text-sm outline-none transition-all"
              style={{
                backgroundColor: 'oklch(0.17 0.009 240)',
                border: '1px solid oklch(0.25 0.01 240)',
                color: 'oklch(0.93 0.005 240)',
              }}
              onFocus={e => (e.currentTarget.style.borderColor = 'oklch(0.65 0.14 195 / 0.6)')}
              onBlur={e => (e.currentTarget.style.borderColor = 'oklch(0.25 0.01 240)')}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg py-2.5 text-sm font-semibold transition-opacity hover:opacity-90 disabled:opacity-60 flex items-center justify-center gap-2"
            style={{
              backgroundColor: 'oklch(0.65 0.14 195)',
              color: 'oklch(0.10 0.005 240)',
            }}
          >
            {loading && (
              <div
                className="h-3.5 w-3.5 rounded-full border-2 border-t-transparent animate-spin"
                style={{ borderColor: 'oklch(0.10 0.005 240 / 0.4)', borderTopColor: 'transparent' }}
              />
            )}
            {mode === 'login' ? '登录' : '注册'}
          </button>
        </form>

        {/* Switch mode */}
        <p className="text-center text-xs mt-5" style={{ color: 'oklch(0.50 0.01 240)' }}>
          {mode === 'login' ? '还没有账户？' : '已有账户？'}
          <button
            className="ml-1 font-medium transition-colors"
            style={{ color: 'oklch(0.65 0.14 195)' }}
            onClick={() => onSwitchMode(mode === 'login' ? 'signup' : 'login')}
            onMouseEnter={e => (e.currentTarget.style.opacity = '0.75')}
            onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
          >
            {mode === 'login' ? '免费注册' : '立即登录'}
          </button>
        </p>

        {/* Disclaimer */}
        <p className="text-center text-[11px] mt-4" style={{ color: 'oklch(0.40 0.01 240)' }}>
          本工具仅作研究训练用途，不构成投资建议
        </p>
      </div>
    </div>
  )
}
