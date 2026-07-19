'use client'

import { useEffect, useState } from 'react'
import { RefreshCw, Target } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { fetchCapabilityProfileHistory, fetchCurrentCapabilityProfile, refreshCapabilityProfile, type CapabilityProfile } from '@/lib/api'

interface CapabilityPanelProps {
  isLoggedIn: boolean
  onLogin: () => void
}

const dimensionLabels: Record<string, string> = {
  financial_analysis: '财务分析',
  business_model: '商业模式',
  valuation: '估值与安全边际',
  evidence_awareness: '证据意识',
  counter_evidence: '反证意识',
  management_analysis: '管理层分析',
  industry_understanding: '行业理解',
  memo_writing: 'Memo写作',
  defense: '答辩表现',
}

export function CapabilityPanel({ isLoggedIn, onLogin }: CapabilityPanelProps) {
  const [profile, setProfile] = useState<CapabilityProfile | null>(null)
  const [historyCount, setHistoryCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isLoggedIn) return
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchCapabilityProfileHistory()
      .then(async history => {
        if (cancelled) return
        setHistoryCount(history.length)
        const next = await fetchCurrentCapabilityProfile()
        if (!cancelled) {
          setProfile(next)
          setHistoryCount(history.length)
        }
      })
      .catch(error => !cancelled && setError(error instanceof Error ? error.message : '能力画像加载失败'))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [isLoggedIn])

  if (!isLoggedIn) {
    return (
      <div className="mx-auto max-w-screen-xl px-6 py-16">
        <div className="mx-auto max-w-md rounded-lg border border-border bg-card p-6 text-center">
          <div className="text-lg font-semibold text-foreground">登录后查看能力成长</div>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">系统会根据你的研究、批改和答辩记录识别优势与重复错误。</p>
          <Button className="mt-5" onClick={onLogin}>登录</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-screen-xl px-6 py-8">
      <div className="mb-5 flex items-end justify-between gap-4">
        <div>
          <div className="mb-1 text-xs font-medium uppercase tracking-wider text-primary">Capability Profile</div>
          <h1 className="text-xl font-semibold text-foreground">个人研究能力画像</h1>
          <p className="mt-1 text-sm text-muted-foreground">评分只来自已完成的研究行为，并保留对应依据。</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void refreshCapabilityProfile().then(next => { setProfile(next); setHistoryCount(count => count + 1) }).catch(error => setError(error instanceof Error ? error.message : '画像刷新失败'))} disabled={loading}>
          <RefreshCw className="h-3.5 w-3.5" />刷新画像
        </Button>
      </div>

      {error && <div className="mb-4 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</div>}
      {loading && !profile ? <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">正在整理研究表现...</div> : profile && (
        <>
          <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-3">
            <Metric label="有效训练样本" value={profile.sample_count} suffix="次" />
            <Metric label="画像历史" value={historyCount} suffix="版" />
            <Metric label="当前优势" value={profile.strengths.length} suffix="项" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_360px]">
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="mb-4 text-sm font-semibold text-foreground">能力维度</div>
              <div className="space-y-5">
                {profile.dimensions.map(dimension => (
                  <div key={dimension.dimension}>
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-sm text-foreground">{dimensionLabels[dimension.dimension] || dimension.dimension}</span>
                      <span className="font-mono text-xs text-primary">{dimension.score == null ? '数据不足' : dimension.score.toFixed(0)}</span>
                    </div>
                    <Progress value={dimension.score || 0} />
                    <div className="mt-1 flex gap-3 text-[10px] text-muted-foreground"><span>{dimension.sample_count}个样本</span><span>可信度：{dimension.confidence}</span><span>{dimension.trend === 'improving' ? '上升' : dimension.trend === 'declining' ? '下降' : dimension.trend === 'stable' ? '稳定' : '数据不足'}{dimension.change != null ? ` ${dimension.change > 0 ? '+' : ''}${dimension.change}` : ''}</span></div>
                    {!!dimension.evidence.length && <div className="mt-2 text-[11px] text-muted-foreground">依据：{dimension.evidence[dimension.evidence.length - 1]}</div>}
                    {dimension.repeated_errors.map(item => <div key={item} className="mt-1 text-[11px] text-warning">重复问题：{item}</div>)}
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-lg border border-border bg-card p-4">
                <div className="mb-3 text-sm font-semibold text-foreground">当前优势</div>
                <div className="flex flex-wrap gap-2">{profile.strengths.length ? profile.strengths.map(item => <Badge key={item} className="border-success/30 bg-success/10 text-success">{dimensionLabels[item] || item}</Badge>) : <span className="text-xs text-muted-foreground">完成更多训练后形成稳定判断。</span>}</div>
              </div>
              <div className="rounded-lg border border-border bg-card p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-foreground"><Target className="h-4 w-4 text-primary" />优先训练</div>
                {profile.recommended_tasks.map(task => <div key={task} className="mt-2 rounded-md border border-border bg-secondary/20 p-3 text-xs leading-relaxed text-muted-foreground">{formatTask(task)}</div>)}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function Metric({ label, value, suffix }: { label: string; value: number; suffix: string }) {
  return <div className="rounded-lg border border-border bg-card p-4"><div className="text-xs text-muted-foreground">{label}</div><div className="mt-1 font-mono text-xl font-semibold text-foreground">{value}<span className="ml-1 text-xs font-normal text-muted-foreground">{suffix}</span></div></div>
}

function formatTask(task: string) {
  return Object.entries(dimensionLabels).reduce(
    (result, [key, label]) => result.replace(key, label),
    task,
  )
}
