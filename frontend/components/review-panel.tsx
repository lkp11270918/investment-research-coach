'use client'

import { useMemo, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { reviewMemo, type AnalyzeResult, type BackendAgentOutput, type BackendFinding } from '@/lib/api'

const sampleMemo = `贵州茅台（600519）研究报告

一、公司概述
贵州茅台是中国最大的高端白酒生产商，2023年实现营收1476.94亿元，同比增长18%，净利润747.34亿元。公司ROE高达36.5%，盈利能力强劲。

二、投资亮点
1. 高股息回报：2023年分红率48%，股息率约2%，是典型的高股息价值股。
2. 低估值：目前PE约30倍，相比历史高点已有明显回调，估值处于合理区间。
3. 现金流好：经营现金流692亿元，现金充裕。
4. 品牌护城河深厚，市场地位稳固。

三、财务分析
公司资产负债率只有19.8%，负债率极低。毛利率91.97%，在A股消费品中位居前列。
卖方普遍看多，目标价2200元，未来三年EPS有望保持15%增长。
主流研究机构认为茅台是中国最好的消费股之一。

四、风险提示
宏观经济下行可能影响高端白酒需求，需关注消费降级风险。`

const classificationLabel: Record<string, string> = {
  sell_side_repetition: '卖方复读',
  evidence_gap: '证据缺口',
  value_trap_omission: '价值陷阱遗漏',
  doctrine_mismatch: '理念不匹配',
  compliance: '合规边界',
  missing_data: '缺失资料',
  unsupported_claim: '无证据结论',
  rewrite_guidance: '改写建议',
  strength: '优点',
}

const classificationTone: Record<string, string> = {
  sell_side_repetition: 'bg-destructive/15 text-destructive border-destructive/30',
  evidence_gap: 'bg-warning/15 text-warning border-warning/30',
  value_trap_omission: 'bg-destructive/15 text-destructive border-destructive/30',
  doctrine_mismatch: 'bg-warning/15 text-warning border-warning/30',
  compliance: 'bg-destructive/15 text-destructive border-destructive/30',
  missing_data: 'bg-secondary text-muted-foreground border-border',
  unsupported_claim: 'bg-warning/15 text-warning border-warning/30',
  rewrite_guidance: 'bg-primary/15 text-primary border-primary/30',
  strength: 'bg-success/15 text-success border-success/30',
}

function statusLabel(status?: string) {
  if (status === 'pass') return '通过'
  if (status === 'fail') return '未通过'
  return '需补充'
}

function statusTone(status?: string) {
  if (status === 'pass') return 'text-success'
  if (status === 'fail') return 'text-destructive'
  return 'text-warning'
}

function confidenceLabel(confidence?: string) {
  if (confidence === 'high') return '高'
  if (confidence === 'medium') return '中'
  return '低'
}

function issueSeverity(finding: BackendFinding) {
  if (['sell_side_repetition', 'value_trap_omission', 'compliance'].includes(finding.classification)) return '严重问题'
  if (['evidence_gap', 'doctrine_mismatch', 'unsupported_claim', 'missing_data'].includes(finding.classification)) return '需改进'
  return '建议'
}

function ReviewFindingCard({
  finding,
  selected,
  onToggle,
}: {
  finding: BackendFinding
  selected: boolean
  onToggle: () => void
}) {
  const tone = classificationTone[finding.classification] || 'bg-primary/15 text-primary border-primary/30'
  return (
    <button
      type="button"
      className={`w-full rounded-lg border bg-card text-left transition-all ${
        selected ? 'border-primary/40' : 'border-border hover:border-primary/25'
      }`}
      onClick={onToggle}
    >
      <div className="flex items-start gap-3 p-3">
        <div className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
          finding.classification === 'strength' ? 'bg-success' :
          finding.classification === 'rewrite_guidance' ? 'bg-primary' :
          finding.classification === 'missing_data' ? 'bg-muted-foreground' :
          'bg-warning'
        }`} />
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <Badge className={`h-4 text-[9px] ${tone}`}>
              {classificationLabel[finding.classification] || finding.classification}
            </Badge>
            <span className="text-xs font-medium text-foreground">{finding.title}</span>
            <span className="text-[10px] text-muted-foreground">置信度：{confidenceLabel(finding.confidence)}</span>
          </div>
          {selected && (
            <div className="mt-2 space-y-2 fade-in-up">
              <div className="rounded border border-border bg-secondary/50 p-2.5 text-xs leading-relaxed text-foreground">
                <span className="font-medium text-warning">{issueSeverity(finding)}：</span>{finding.detail}
              </div>
              {finding.evidence_ids.length > 0 && (
                <div className="text-[10px] text-muted-foreground">
                  关联证据：{finding.evidence_ids.join(', ')}
                </div>
              )}
            </div>
          )}
        </div>
        <svg
          className={`mt-0.5 h-4 w-4 shrink-0 text-muted-foreground transition-transform ${selected ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 16 16"
        >
          <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
    </button>
  )
}

export function ReviewPanel() {
  const [memoText, setMemoText] = useState(sampleMemo)
  const [isReviewing, setIsReviewing] = useState(false)
  const [reviewResult, setReviewResult] = useState<AnalyzeResult | null>(null)
  const [apiError, setApiError] = useState<string | null>(null)
  const [selectedIssue, setSelectedIssue] = useState<string | null>(null)

  const reviewOutput = (reviewResult?.state.skill_outputs?.research_coach_review || reviewResult?.state.agent_outputs.red_team_judge || reviewResult?.state.agent_outputs.research_coach_review) as BackendAgentOutput | undefined
  const doctrineOutput = (reviewResult?.state.agent_outputs.research_planner || reviewResult?.state.agent_outputs.firm_doctrine_case_retrieval) as BackendAgentOutput | undefined

  const groupedCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const finding of reviewOutput?.findings || []) {
      counts[finding.classification] = (counts[finding.classification] || 0) + 1
    }
    return counts
  }, [reviewOutput])

  const handleReview = async () => {
    setIsReviewing(true)
    setApiError(null)
    setReviewResult(null)
    setSelectedIssue(null)
    try {
      const result = await reviewMemo({ memoText })
      setReviewResult(result)
      const firstFinding = (result.state.skill_outputs?.research_coach_review || result.state.agent_outputs.red_team_judge || result.state.agent_outputs.research_coach_review)?.findings?.[0]
      setSelectedIssue(firstFinding ? `0-${firstFinding.title}` : null)
    } catch (error) {
      setApiError(error instanceof Error ? error.message : '批改请求失败')
    } finally {
      setIsReviewing(false)
    }
  }

  return (
    <div className="mx-auto max-w-screen-2xl px-6 py-8">
      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-5 space-y-4">
          <div>
            <h1 className="text-xl font-semibold text-foreground">研究报告批改模式</h1>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              粘贴您写的研究报告，系统会调用 Research Coach Review Mode，对照通用价值投资 Doctrine 批改研究质量。
            </p>
          </div>

          <div className="overflow-hidden rounded-lg border border-border bg-card">
            <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
              <span className="text-xs font-medium text-foreground">粘贴研究报告</span>
              <div className="flex items-center gap-2">
                <button onClick={() => setMemoText(sampleMemo)} className="text-xs text-primary hover:underline">
                  载入示例报告
                </button>
                <button
                  onClick={() => { setMemoText(''); setReviewResult(null); setApiError(null) }}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  清空
                </button>
              </div>
            </div>
            <Textarea
              value={memoText}
              onChange={event => { setMemoText(event.target.value); setReviewResult(null); setApiError(null) }}
              placeholder="粘贴您写的研究报告、投资笔记或 Memo 初稿..."
              className="min-h-[400px] resize-none rounded-none border-0 bg-secondary/20 font-mono text-xs leading-relaxed text-foreground placeholder:text-muted-foreground focus:ring-0"
            />
            <div className="flex items-center justify-between border-t border-border px-4 py-2.5">
              <span className="text-xs text-muted-foreground">{memoText.length} 字</span>
              <button
                onClick={handleReview}
                disabled={!memoText.trim() || isReviewing}
                className="flex items-center gap-2 rounded-md bg-primary px-4 py-1.5 text-xs font-semibold text-primary-foreground transition-all hover:opacity-90 disabled:opacity-50"
              >
                {isReviewing ? (
                  <>
                    <div className="h-3 w-3 rounded-full border-2 border-primary-foreground border-t-transparent animate-spin" />
                    <span>批改中...</span>
                  </>
                ) : '开始批改'}
              </button>
            </div>
          </div>

          <div className="space-y-2 rounded-lg border border-border bg-card p-4">
            <div className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">通用价值投资批改底座</div>
            {(doctrineOutput?.findings || [
              { title: '安全边际' },
              { title: '能力圈' },
              { title: '现金流质量' },
              { title: 'Owner Earnings' },
              { title: '分红可持续性' },
              { title: '资产负债表安全' },
              { title: 'ROE 质量' },
              { title: '护城河' },
              { title: '管理层资本配置' },
              { title: '价值陷阱与反证' },
              { title: '市场预期与二阶思维' },
              { title: '本金保护与机会成本' },
            ]).map((item, index) => (
              <div key={`${item.title}-${index}`} className="flex items-start gap-2 text-xs text-muted-foreground">
                <div className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/50" />
                {item.title}
              </div>
            ))}
          </div>
        </div>

        <div className="col-span-7 space-y-4">
          {!reviewResult && !isReviewing && !apiError && (
            <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-border bg-card">
              <div className="text-center">
                <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full border border-border bg-secondary">
                  <svg className="h-5 w-5 text-muted-foreground" fill="none" viewBox="0 0 20 20">
                    <path d="M5 4h10M5 9h10M5 14h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                </div>
                <div className="text-sm text-muted-foreground">粘贴研究报告后点击“开始批改”</div>
                <div className="mt-1 text-xs text-muted-foreground/60">结果将来自线上 /api/review</div>
              </div>
            </div>
          )}

          {isReviewing && (
            <div className="rounded-lg border border-primary/30 bg-card p-6">
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20">
                  <div className="h-4 w-4 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                </div>
                <div>
                  <div className="text-sm font-medium text-foreground">Research Coach 批改中...</div>
                  <div className="mt-0.5 text-xs text-muted-foreground">正在识别卖方复读、证据缺口、价值陷阱和理念偏离</div>
                </div>
              </div>
              <div className="space-y-2">
                {['材料整理', '证据抽取', '通用价值投资 Doctrine 对照', '研究质量批改'].map(step => (
                  <div key={step} className="flex items-center gap-2 text-xs text-muted-foreground">
                    <div className="h-1.5 w-1.5 rounded-full bg-primary/50 animate-pulse" />
                    {step}
                  </div>
                ))}
              </div>
            </div>
          )}

          {apiError && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4">
              <div className="text-sm font-semibold text-destructive">批改请求失败</div>
              <div className="mt-1 text-xs leading-relaxed text-muted-foreground">{apiError}</div>
            </div>
          )}

          {reviewOutput && (
            <div className="space-y-4 fade-in-up">
              <div className="rounded-lg border border-border bg-card p-4">
                <div className="mb-3 flex items-start justify-between gap-4">
                  <div>
                    <div className="text-sm font-semibold text-foreground">批改结论</div>
                    <div className="mt-0.5 text-xs text-muted-foreground">Run ID：{reviewResult?.run_id}</div>
                  </div>
                  <div className="text-right">
                    <div className={`text-2xl font-bold ${statusTone(reviewOutput.status)}`}>{statusLabel(reviewOutput.status)}</div>
                    <div className="text-xs text-muted-foreground">置信度：{confidenceLabel(reviewOutput.confidence)}</div>
                  </div>
                </div>
                <p className="text-sm leading-relaxed text-muted-foreground">{reviewOutput.summary}</p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {Object.entries(groupedCounts).map(([classification, count]) => (
                  <div
                    key={classification}
                    className={`rounded-md border px-3 py-1.5 text-xs ${classificationTone[classification] || 'bg-secondary text-muted-foreground border-border'}`}
                  >
                    {count} 项{classificationLabel[classification] || classification}
                  </div>
                ))}
              </div>

              <div className="space-y-2">
                {reviewOutput.findings.map((finding, index) => {
                  const id = `${index}-${finding.title}`
                  return (
                    <ReviewFindingCard
                      key={id}
                      finding={finding}
                      selected={selectedIssue === id}
                      onToggle={() => setSelectedIssue(selectedIssue === id ? null : id)}
                    />
                  )
                })}
              </div>

              {(reviewOutput.missing_materials.length > 0 || reviewOutput.warnings.length > 0) && (
                <div className="grid grid-cols-2 gap-3">
                  {reviewOutput.missing_materials.length > 0 && (
                    <div className="rounded-lg border border-border bg-card p-4">
                      <div className="mb-2 text-xs font-medium text-foreground">缺失资料</div>
                      <div className="space-y-1">
                        {reviewOutput.missing_materials.map(item => (
                          <div key={item} className="text-xs leading-relaxed text-muted-foreground">- {item}</div>
                        ))}
                      </div>
                    </div>
                  )}
                  {reviewOutput.warnings.length > 0 && (
                    <div className="rounded-lg border border-border bg-card p-4">
                      <div className="mb-2 text-xs font-medium text-foreground">边界提醒</div>
                      <div className="space-y-1">
                        {reviewOutput.warnings.map(item => (
                          <div key={item} className="text-xs leading-relaxed text-muted-foreground">- {item}</div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
