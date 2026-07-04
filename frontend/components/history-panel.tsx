'use client'

import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { fetchResearchRun, fetchResearchRuns, type ResearchRunSummary, type ResearchRunDetail } from '@/lib/api'

interface HistoryPanelProps {
  isLoggedIn: boolean
  onLogin: () => void
  onOpenRun: (detail: ResearchRunDetail) => void
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function runTypeLabel(type: string) {
  return type === 'review' ? '报告批改' : '研究分析'
}

function confidenceLabel(value?: string | null) {
  if (value === 'high') return '高'
  if (value === 'medium') return '中'
  if (value === 'low') return '低'
  return '未生成'
}

export function HistoryPanel({ isLoggedIn, onLogin, onOpenRun }: HistoryPanelProps) {
  const [runs, setRuns] = useState<ResearchRunSummary[]>([])
  const [loading, setLoading] = useState(false)
  const [openingRunId, setOpeningRunId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isLoggedIn) return
    setLoading(true)
    setError(null)
    fetchResearchRuns()
      .then(setRuns)
      .catch(error => setError(error instanceof Error ? error.message : '历史记录加载失败'))
      .finally(() => setLoading(false))
  }, [isLoggedIn])

  const handleOpen = async (runId: string) => {
    setOpeningRunId(runId)
    setError(null)
    try {
      const detail = await fetchResearchRun(runId)
      onOpenRun(detail)
    } catch (error) {
      setError(error instanceof Error ? error.message : '打开历史记录失败')
    } finally {
      setOpeningRunId(null)
    }
  }

  if (!isLoggedIn) {
    return (
      <div className="mx-auto max-w-screen-xl px-6 py-16">
        <div className="mx-auto max-w-md rounded-lg border border-border bg-card p-6 text-center">
          <div className="text-lg font-semibold text-foreground">登录后查看历史研究</div>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            登录后，系统会保存你的分析、批改、Memo 和证据，方便后续复盘。
          </p>
          <button
            onClick={onLogin}
            className="mt-5 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90"
          >
            登录
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-screen-xl px-6 py-8">
      <div className="mb-5 flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">历史研究资产</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            已保存的研究分析、报告批改、Memo 和证据记录。
          </p>
        </div>
        <Badge className="border-primary/30 bg-primary/15 text-primary">{runs.length} 条记录</Badge>
      </div>

      {loading && (
        <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
          正在加载历史研究...
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {!loading && runs.length === 0 && (
        <div className="rounded-lg border border-dashed border-border bg-card p-8 text-center">
          <div className="text-sm font-medium text-foreground">还没有历史研究</div>
          <div className="mt-1 text-xs text-muted-foreground">完成一次分析或报告批改后，这里会自动沉淀记录。</div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-3">
        {runs.map(run => (
          <button
            key={run.run_id}
            onClick={() => handleOpen(run.run_id)}
            className="rounded-lg border border-border bg-card p-4 text-left transition-all hover:border-primary/35 hover:bg-accent/20"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <Badge className="border-border bg-secondary text-muted-foreground">{runTypeLabel(run.run_type)}</Badge>
                  <span className="font-mono text-[10px] text-muted-foreground">{run.run_id}</span>
                </div>
                <div className="truncate text-sm font-semibold text-foreground">{run.company_name}</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {run.ticker || '无代码'} · {run.industry || '未指定行业'} · {formatTime(run.created_at)}
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 text-right">
                <div>
                  <div className="text-[10px] text-muted-foreground">资料</div>
                  <div className="text-xs font-semibold text-foreground">{run.material_count}</div>
                </div>
                <div>
                  <div className="text-[10px] text-muted-foreground">证据</div>
                  <div className="text-xs font-semibold text-foreground">{run.evidence_count}</div>
                </div>
                <div>
                  <div className="text-[10px] text-muted-foreground">置信度</div>
                  <div className="text-xs font-semibold text-primary">{confidenceLabel(run.memo_confidence)}</div>
                </div>
              </div>
            </div>
            {openingRunId === run.run_id && (
              <div className="mt-3 text-xs text-primary">正在打开...</div>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}
