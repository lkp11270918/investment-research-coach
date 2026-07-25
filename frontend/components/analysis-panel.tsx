'use client'

import { useState, useEffect } from 'react'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { analyzeCompany, type AnalyzeResult, type BackendAgentOutput } from '@/lib/api'

export interface AnalysisData {
  stockCode: string
  companyName: string
  industry: string
  materials: Array<{ id: string; type: string; name: string; status: 'ready' | 'missing'; content?: string }>
  projectId?: string | null
  researchObjective?: string
  investmentHorizon?: string
  initialView?: string
  keyQuestion?: string
}

interface AgentStep {
  id: string
  name: string
  nameEn: string
  description: string
  status: 'pending' | 'running' | 'done' | 'warning'
  duration?: string
  output?: string[]
  warnings?: string[]
}

const agentSteps: AgentStep[] = [
  { id: 'planning', name: '研究路径规划', nameEn: 'Research Planning', description: '识别公司类型、优先问题和所需分析', status: 'pending' },
  { id: 'evidence', name: '资料整理与证据构建', nameEn: 'Evidence Building', description: '解析资料、定位来源并更新证据图谱', status: 'pending' },
  { id: 'analysis', name: '专项研究分析', nameEn: 'Research Analysis', description: '按计划并行完成财务、商业模式、观点和估值分析', status: 'pending' },
  { id: 'judge', name: '反证与质量门禁', nameEn: 'Red Team & Judge', description: '检查反方证据、价值陷阱、证据充分性和合规性', status: 'pending' },
  { id: 'writing', name: '研究 Memo 生成', nameEn: 'Memo Writing', description: '仅将通过门禁的内容写入标准 Memo', status: 'pending' },
]

const backendOutputKeyByStepId: Record<string, string> = {
  planning: 'research_planner',
  evidence: 'evidence',
  analysis: 'research_analyst',
  judge: 'red_team_judge',
}

function statusFromBackend(output?: BackendAgentOutput): AgentStep['status'] {
  if (!output) return 'done'
  if (output.status === 'fail' || output.warnings.length > 0 || output.missing_materials.length > 0) return 'warning'
  return 'done'
}

function formatBackendOutput(output?: BackendAgentOutput): string[] {
  if (!output) return ['后端未返回该步骤的详细输出。']
  const lines: string[] = []
  lines.push(`【结论】${output.summary}`)
  if (output.findings.length > 0) {
    for (const finding of output.findings.slice(0, 6)) {
      lines.push(`✓ [${finding.classification}] ${finding.title}：${finding.detail}`)
    }
  }
  if (output.missing_materials.length > 0) {
    for (const item of output.missing_materials.slice(0, 6)) {
      lines.push(`⚠ 缺失资料：${item}`)
    }
  }
  if (output.warnings.length > 0) {
    for (const warning of output.warnings.slice(0, 6)) {
      lines.push(`⚠ ${warning}`)
    }
  }
  lines.push(`→ 状态：${output.status} · 置信度：${output.confidence} · 证据数：${output.evidence_ids.length}`)
  return lines
}

function stepsFromBackendResult(result: AnalyzeResult): AgentStep[] {
  return agentSteps.map(step => {
    const key = backendOutputKeyByStepId[step.id]
    const output = result.state.agent_outputs[key] || result.state.skill_outputs?.[key]
    if (step.id === 'writing') {
      const writingEvent = result.state.workflow_events?.find(item => item.stage === 'writing')
      return {...step,status:writingEvent?.status === 'completed' ? 'done' : 'warning',output:[writingEvent?.status === 'completed' ? '已按门禁批准内容生成 Memo。' : '门禁未通过，未生成正式 Memo。']}
    }
    return {
      ...step,
      status: statusFromBackend(output),
      output: formatBackendOutput(output),
      warnings: [
        ...(output?.warnings || []),
        ...(output?.missing_materials || []).map(item => `缺：${item}`),
      ].slice(0, 3),
    }
  })
}

interface AnalysisPanelProps {
  data: AnalysisData
  onComplete: (result: AnalyzeResult) => void
}

export function AnalysisPanel({ data, onComplete }: AnalysisPanelProps) {
  const [steps, setSteps] = useState<AgentStep[]>(agentSteps.map(s => ({ ...s, status: 'pending' as const })))
  const [currentStep, setCurrentStep] = useState(-1)
  const [expandedStep, setExpandedStep] = useState<string | null>(null)
  const [isComplete, setIsComplete] = useState(false)
  const [started, setStarted] = useState(false)
  const [progress, setProgress] = useState(0)
  const [apiError, setApiError] = useState<string | null>(null)
  const [analysisResult, setAnalysisResult] = useState<AnalyzeResult | null>(null)

  const startAnalysis = () => {
    setStarted(true)
    setApiError(null)
    runSteps()
  }

  const runSteps = async () => {
    try {
      for (let idx = 0; idx < agentSteps.length; idx++) {
        setCurrentStep(idx)
        setExpandedStep(agentSteps[idx].id)
        setProgress(Math.round((idx / agentSteps.length) * 100))
        setSteps(prev => prev.map((s, i) => ({
          ...s,
          status: i === idx ? 'running' : i < idx ? 'done' : 'pending',
        })))
        await new Promise(resolve => setTimeout(resolve, 350))
      }

      const result = await analyzeCompany(data)
      setAnalysisResult(result)
      setSteps(stepsFromBackendResult(result))
      setIsComplete(true)
      setProgress(100)
      onComplete(result)
    } catch (error) {
      setApiError(error instanceof Error ? error.message : '分析请求失败')
      setSteps(prev => prev.map((s, i) => ({
        ...s,
        status: i <= Math.max(currentStep, 0) ? 'warning' : s.status,
      })))
    }
  }

  const statusIcon = (status: AgentStep['status']) => {
    switch (status) {
      case 'done': return (
        <div className="h-6 w-6 rounded-full bg-success/20 border border-success/40 flex items-center justify-center">
          <svg className="h-3 w-3 text-success" fill="none" viewBox="0 0 12 12">
            <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      )
      case 'warning': return (
        <div className="h-6 w-6 rounded-full bg-warning/20 border border-warning/40 flex items-center justify-center">
          <svg className="h-3 w-3 text-warning" fill="none" viewBox="0 0 12 12">
            <path d="M6 2v5M6 9v1" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
        </div>
      )
      case 'running': return (
        <div className="h-6 w-6 rounded-full bg-primary/20 border border-primary/40 flex items-center justify-center agent-active">
          <div className="h-2 w-2 rounded-full bg-primary animate-pulse" />
        </div>
      )
      default: return (
        <div className="h-6 w-6 rounded-full border border-border flex items-center justify-center">
          <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground/30" />
        </div>
      )
    }
  }

  return (
    <div className="mx-auto max-w-screen-2xl px-6 py-8">
      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-4 rounded-lg border border-border bg-card p-5"><div className="flex items-start justify-between"><div><div className="text-lg font-semibold text-foreground">{data.companyName}</div><div className="mt-1 font-mono text-xs text-muted-foreground">{data.stockCode} · {data.industry}</div></div><Badge className={isComplete ? 'border-success/30 bg-success/10 text-success' : 'border-primary/30 bg-primary/10 text-primary'}>{isComplete ? '研究底稿已更新' : started ? '正在处理' : '待启动'}</Badge></div><div className="mt-5 text-xs text-muted-foreground">研究目的</div><div className="mt-1 text-sm text-foreground">{data.researchObjective || '证据驱动的买方研究'}</div><div className="mt-4 text-xs text-muted-foreground">核心问题</div><div className="mt-1 text-sm leading-relaxed text-foreground">{data.keyQuestion || '什么证据支持或推翻当前判断？'}</div>{!started && <button onClick={startAnalysis} className="mt-6 w-full rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:opacity-90">开始研究</button>}</div>
        <div className="col-span-8 rounded-lg border border-border bg-card p-6"><div className="flex items-center justify-between"><div className="text-sm font-semibold text-foreground">研究资料处理</div><span className="font-mono text-xs text-primary">{progress}%</span></div><Progress value={progress} className="mt-3 h-1.5" /><div className="mt-6 grid grid-cols-4 gap-3">{['资料标准化', '证据与关系', '基本面与反证', '证据门禁'].map((label, index) => { const threshold = (index + 1) * 25; const done = progress >= threshold; const active = progress < threshold && progress >= index * 25; return <div key={label} className={`rounded-md border p-3 ${done ? 'border-success/30 bg-success/5' : active ? 'border-primary/40 bg-primary/5' : 'border-border bg-secondary/20'}`}><div className={`text-xs font-medium ${done ? 'text-success' : active ? 'text-primary' : 'text-muted-foreground'}`}>{label}</div><div className="mt-1 text-[10px] text-muted-foreground">{done ? '完成' : active ? '处理中' : '等待'}</div></div> })}</div><div className="mt-6 grid grid-cols-3 gap-3">{data.materials.filter(item => item.status === 'ready').map(item => <div key={item.id} className="rounded-md border border-border bg-secondary/20 p-3"><div className="truncate text-xs text-foreground">{item.type}</div><div className="mt-1 text-[10px] text-muted-foreground">已加入资料包</div></div>)}</div>{apiError && <div className="mt-5 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{apiError}</div>}{isComplete && <div className="mt-5 rounded-md border border-success/30 bg-success/5 p-4 text-sm text-success">资料、证据图谱和研究地图已更新。</div>}</div>
      </div>
    </div>
  )
}
