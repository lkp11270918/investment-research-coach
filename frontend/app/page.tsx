'use client'

import { useEffect, useState } from 'react'
import { LandingPage } from '@/components/landing-page'
import { AuthModal } from '@/components/auth-modal'
import { NavHeader } from '@/components/nav-header'
import { InputPanel } from '@/components/input-panel'
import { AnalysisPanel, type AnalysisData } from '@/components/analysis-panel'
import { MemoPanel } from '@/components/memo-panel'
import { ReviewPanel } from '@/components/review-panel'
import { ResearchWorkspacePanel } from '@/components/research-workspace-panel'
import { CapabilityPanel } from '@/components/capability-panel'
import type { AnalyzeResult, AuthUser, BackendMemo } from '@/lib/api'
import { clearStoredToken, fetchCurrentUser, getStoredToken } from '@/lib/api'

type AppView = 'landing' | 'app'
type AuthMode = 'login' | 'signup'

export default function Page() {
  const [view, setView] = useState<AppView>('landing')
  const [authModal, setAuthModal] = useState<AuthMode | null>(null)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null)
  const [activeTab, setActiveTab] = useState('map')
  const [showIntake, setShowIntake] = useState(true)
  const [intakeProjectId, setIntakeProjectId] = useState<string | null>(null)
  const [intakeCompany, setIntakeCompany] = useState<{ stockCode: string; companyName: string; industry: string } | null>(null)
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
        setShowIntake(false)
      })
      .catch(() => {
        clearStoredToken()
        setCurrentUser(null)
        setIsLoggedIn(false)
      })
  }, [])

  const handleEnterApp = () => {
    setView('app')
    setActiveTab('map')
  }

  const handleLogin = () => setAuthModal('login')
  const handleSignup = () => setAuthModal('signup')
  const handleAuthClose = () => setAuthModal(null)

  const handleAuthSuccess = (user: AuthUser) => {
    setCurrentUser(user)
    setIsLoggedIn(true)
    setAuthModal(null)
    setView('app')
    setActiveTab('map')
    setShowIntake(false)
  }

  const handleLogout = () => {
    clearStoredToken()
    setCurrentUser(null)
    setIsLoggedIn(false)
    setAuthModal(null)
    setView('landing')
    setActiveTab('map')
    setShowIntake(true)
    setAnalysisData(null)
    setAnalysisResult(null)
    setMemo(null)
    setCurrentProjectId(null)
  }

  const handleStartAnalysis = (data: {
    stockCode: string
    companyName: string
    industry: string
    researchObjective: string
    investmentHorizon: string
    initialView: string
    keyQuestion: string
    materials: AnalysisData['materials']
  }) => {
    setMemo(null)
    setAnalysisResult(null)
    setAnalysisData(data)
    setShowIntake(false)
    setActiveTab('map')
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
            {activeTab === 'map' && showIntake && <InputPanel projectId={intakeProjectId} initialCompany={intakeCompany} onStartAnalysis={handleStartAnalysis} />}

            {activeTab === 'map' && analysisData && !analysisResult ? (
              <AnalysisPanel
                data={analysisData}
                onComplete={(result) => {
                  setAnalysisResult(result)
                  setMemo(result.state.memo || null)
                  setCurrentProjectId(result.project_id || null)
                  setActiveTab('map')
                }}
              />
            ) : null}

            {activeTab === 'map' && !showIntake && (!analysisData || analysisResult) && <ResearchWorkspacePanel isLoggedIn={isLoggedIn} projectId={currentProjectId} companyName={analysisData?.companyName} onLogin={handleLogin} section="map" onNewResearch={() => { setShowIntake(true); setIntakeProjectId(null); setIntakeCompany(null); setAnalysisData(null); setAnalysisResult(null); setCurrentProjectId(null) }} onAddMaterials={(projectId, company) => { setIntakeProjectId(projectId); setIntakeCompany(company); setCurrentProjectId(projectId); setAnalysisData(null); setAnalysisResult(null); setShowIntake(true) }} onProjectChange={setCurrentProjectId} />}

            {activeTab === 'evidence' && <ResearchWorkspacePanel isLoggedIn={isLoggedIn} projectId={currentProjectId} companyName={analysisData?.companyName} onLogin={handleLogin} section="evidence" onProjectChange={setCurrentProjectId} />}

            {activeTab === 'thesis' && <ResearchWorkspacePanel isLoggedIn={isLoggedIn} projectId={currentProjectId} companyName={analysisData?.companyName} onLogin={handleLogin} section="thesis" onProjectChange={setCurrentProjectId} />}

            {activeTab === 'memo' && (
              <><MemoPanel
                companyName={analysisData?.companyName}
                stockCode={analysisData?.stockCode}
                industry={analysisData?.industry}
                memo={memo}
                evidenceItems={analysisResult?.state.evidence_items || []}
              /><ReviewPanel /></>
            )}

            {activeTab === 'defense' && <><ResearchWorkspacePanel isLoggedIn={isLoggedIn} projectId={currentProjectId} companyName={analysisData?.companyName} onLogin={handleLogin} section="defense" onProjectChange={setCurrentProjectId} /><CapabilityPanel isLoggedIn={isLoggedIn} onLogin={handleLogin} /></>}
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
