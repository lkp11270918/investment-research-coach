'use client'

import { useEffect, useState } from 'react'
import { LandingPage } from '@/components/landing-page'
import { AuthModal } from '@/components/auth-modal'
import { NavHeader } from '@/components/nav-header'
import { InputPanel } from '@/components/input-panel'
import { AnalysisPanel, type AnalysisData } from '@/components/analysis-panel'
import { MemoPanel } from '@/components/memo-panel'
import { ReviewPanel } from '@/components/review-panel'
import { HistoryPanel } from '@/components/history-panel'
import { ResearchWorkspacePanel } from '@/components/research-workspace-panel'
import { CapabilityPanel } from '@/components/capability-panel'
import type { AnalyzeResult, AuthUser, BackendMemo, ResearchRunDetail } from '@/lib/api'
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
  const [analysisResult, setAnalysisResult] = useState<AnalyzeResult | null>(null)
  const [memo, setMemo] = useState<BackendMemo | null>(null)
  const [currentProjectId, setCurrentProjectId] = useState<string | null>(null)

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
    setAuthModal(null)
    setView('landing')
    setActiveTab('input')
    setAnalysisData(null)
    setAnalysisResult(null)
    setMemo(null)
    setCurrentProjectId(null)
  }

  const handleStartAnalysis = (data: {
    stockCode: string
    companyName: string
    industry: string
    materials: AnalysisData['materials']
  }) => {
    setMemo(null)
    setAnalysisResult(null)
    setCurrentProjectId(null)
    setAnalysisData(data)
    setActiveTab('analysis')
  }

  const handleOpenHistoryRun = (detail: ResearchRunDetail) => {
    const profile = detail.state.company_profile
    setAnalysisData({
      stockCode: profile?.ticker || '',
      companyName: profile?.company_name || detail.summary.company_name,
      industry: profile?.industry || detail.summary.industry || '',
      materials: [],
    })
    setAnalysisResult({
      run_id: detail.summary.run_id,
      status: 'completed',
      state: detail.state,
    })
    setMemo(detail.state.memo || null)
    setCurrentProjectId(null)
    setActiveTab(detail.state.memo ? 'memo' : 'analysis')
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
                  setAnalysisResult(result)
                  setMemo(result.state.memo || null)
                  setCurrentProjectId(result.project_id || null)
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
                evidenceItems={analysisResult?.state.evidence_items || []}
              />
            )}

            {activeTab === 'review' && <ReviewPanel />}

            {activeTab === 'workspace' && (
              <ResearchWorkspacePanel
                isLoggedIn={isLoggedIn}
                projectId={currentProjectId}
                companyName={analysisData?.companyName}
                onLogin={handleLogin}
              />
            )}

            {activeTab === 'history' && (
              <HistoryPanel
                isLoggedIn={isLoggedIn}
                onLogin={handleLogin}
                onOpenRun={handleOpenHistoryRun}
              />
            )}

            {activeTab === 'capability' && (
              <CapabilityPanel isLoggedIn={isLoggedIn} onLogin={handleLogin} />
            )}
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
