'use client'

import { useEffect, useState } from 'react'
import { LandingPage } from '@/components/landing-page'
import { AuthModal } from '@/components/auth-modal'
import { NavHeader } from '@/components/nav-header'
import { InputPanel } from '@/components/input-panel'
import { AnalysisPanel, type AnalysisData } from '@/components/analysis-panel'
import { MemoPanel } from '@/components/memo-panel'
import { ReviewPanel } from '@/components/review-panel'
import type { AuthUser, BackendMemo } from '@/lib/api'
import { clearStoredToken, fetchCurrentUser, getStoredToken } from '@/lib/api'

type AppView = 'landing' | 'app'
type AuthMode = 'login' | 'signup'

export default function Page() {
  const [view, setView] = useState<AppView>('landing')
  const [authModal, setAuthModal] = useState<AuthMode | null>(null)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null)
  const [activeTab, setActiveTab] = useState('input')
  const [analysisData, setAnalysisData] = useState<AnalysisData | null>(null)
  const [memo, setMemo] = useState<BackendMemo | null>(null)

  useEffect(() => {
    const token = getStoredToken()
    if (!token) return
    fetchCurrentUser(token)
      .then(user => {
        setCurrentUser(user)
        setIsLoggedIn(true)
      })
      .catch(() => {
        clearStoredToken()
        setCurrentUser(null)
        setIsLoggedIn(false)
      })
  }, [])

  const handleEnterApp = () => {
    setView('app')
    setActiveTab('input')
  }

  const handleLogin = () => setAuthModal('login')
  const handleSignup = () => setAuthModal('signup')
  const handleAuthClose = () => setAuthModal(null)

  const handleAuthSuccess = (user: AuthUser) => {
    setCurrentUser(user)
    setIsLoggedIn(true)
    setAuthModal(null)
    setView('app')
    setActiveTab('input')
  }

  const handleLogout = () => {
    clearStoredToken()
    setCurrentUser(null)
    setIsLoggedIn(false)
  }

  const handleStartAnalysis = (data: {
    stockCode: string
    companyName: string
    industry: string
    materials: AnalysisData['materials']
  }) => {
    setMemo(null)
    setAnalysisData(data)
    setActiveTab('analysis')
  }

  return (
    <>
      {view === 'landing' && (
        <LandingPage
          onEnterApp={handleEnterApp}
          onLogin={handleLogin}
          onSignup={handleSignup}
        />
      )}

      {view === 'app' && (
        <div className="min-h-screen" style={{ backgroundColor: 'oklch(0.10 0.005 240)', color: 'oklch(0.93 0.005 240)' }}>
          <NavHeader
            activeTab={activeTab}
            onTabChange={setActiveTab}
            onBackToHome={() => setView('landing')}
            isLoggedIn={isLoggedIn}
            user={currentUser}
            hasAnalysisData={!!analysisData}
            onLogin={handleLogin}
            onSignup={handleSignup}
            onLogout={handleLogout}
          />

          <main>
            {activeTab === 'input' && (
              <InputPanel onStartAnalysis={handleStartAnalysis} />
            )}

            {activeTab === 'analysis' && analysisData ? (
              <AnalysisPanel
                data={analysisData}
                onComplete={(result) => {
                  setMemo(result.state.memo || null)
                  setActiveTab('memo')
                }}
              />
            ) : activeTab === 'analysis' && !analysisData ? (
              <div className="flex items-center justify-center h-[60vh]">
                <div className="text-center">
                  <div className="text-sm mb-3" style={{ color: 'oklch(0.55 0.01 240)' }}>
                    请先在「资料输入」页填写公司信息并开始分析
                  </div>
                  <button
                    onClick={() => setActiveTab('input')}
                    className="text-xs transition-opacity hover:opacity-75"
                    style={{ color: 'oklch(0.65 0.14 195)' }}
                  >
                    前往资料输入
                  </button>
                </div>
              </div>
            ) : null}

            {activeTab === 'memo' && (
              <MemoPanel
                companyName={analysisData?.companyName}
                stockCode={analysisData?.stockCode}
                industry={analysisData?.industry}
                memo={memo}
              />
            )}

            {activeTab === 'review' && <ReviewPanel />}
          </main>
        </div>
      )}

      {authModal && (
        <AuthModal
          mode={authModal}
          onClose={handleAuthClose}
          onSuccess={handleAuthSuccess}
          onSwitchMode={setAuthModal}
        />
      )}
    </>
  )
}
