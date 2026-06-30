'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'

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

interface ReviewIssue {
  id: string
  severity: 'error' | 'warning' | 'info'
  category: string
  quote: string
  issue: string
  suggestion: string
}

const reviewIssues: ReviewIssue[] = [
  {
    id: '1',
    severity: 'error',
    category: '高股息误判',
    quote: '是典型的高股息价值股',
    issue: '直接将高股息等同于"价值股"属于典型价值陷阱思维。高股息是否安全取决于自由现金流能否覆盖分红，以及分红是否可持续，不能作为直接结论。',
    suggestion: '应改为：分红率48%，自由现金流约650亿元，FCF覆盖分红约1.81倍，分红具备持续的现金流支撑。注意区分"高股息"和"可持续分红"。',
  },
  {
    id: '2',
    severity: 'error',
    category: '低估值误判',
    quote: '估值处于合理区间',
    issue: '直接把PE回调等同于"低估值/合理估值"是典型的价值陷阱判断错误。PE 30倍是否合理，需要对应增长假设、行业平均水平和安全边际分析，不能简单以历史高点作为比较基准。',
    suggestion: '应明确：当前PE约30x，隐含未来3-5年盈利增速约X%（需显式假设）。若增速低于假设，估值存在收缩风险，当前不具备明显安全边际。',
  },
  {
    id: '3',
    severity: 'error',
    category: '卖方观点复读',
    quote: '卖方普遍看多，目标价2200元，未来三年EPS有望保持15%增长。主流研究机构认为茅台是中国最好的消费股之一。',
    issue: '这段直接将卖方结论当作买方研究结论，没有进行二次消化和独立判断。买方研究的核心是：卖方的15%增速假设依赖什么核心变量？这个假设是否可验证？分歧在哪里？',
    suggestion: '应改为：卖方主流预测未来三年EPS CAGR约15%，核心驱动假设为[X]。但部分机构对宏观消费降级持谨慎态度。买方需独立判断：该增速假设是否合理，关键变量是什么。',
  },
  {
    id: '4',
    severity: 'warning',
    category: '缺少反证意识',
    quote: '（整个报告中缺少反证检查）',
    issue: '报告没有专门的反证风险章节。价值投资研究的核心要求之一是：哪些因素会推翻当前判断？价值陷阱检查是必须的，不是可选项。',
    suggestion: '需要新增：哪些信号会让当前判断降级或反转？例如：若经营现金流恶化，若渠道库存快速上升，若宏观消费持续下行，当前判断如何调整？',
  },
  {
    id: '5',
    severity: 'warning',
    category: '来源缺失',
    quote: '品牌护城河深厚，市场地位稳固',
    issue: '该结论没有来源标注，读者无法判断这是事实、卖方观点还是作者自己的推理。买方研究要求区分事实（有来源）、观点（标注来源方）和AI/自身推理（标注不确定性）。',
    suggestion: '添加来源标注，例如：[卖方共识观点] / [年报信息] / [AI推理，需进一步验证]',
  },
  {
    id: '6',
    severity: 'info',
    category: '结构不完整',
    quote: '（报告整体结构）',
    issue: '报告缺少以下价值投资必要分析维度：① 管理层叙事与财务现实一致性检查 ② 卖方共识与分歧的拆解 ③ 资料缺口说明 ④ 研究置信度说明。',
    suggestion: '建议按照标准价值投资 Memo 框架补充上述章节，尤其是"卖方共识与分歧拆解"和"价值陷阱检查"是买方研究的核心差异化部分。',
  },
]

const severityConfig = {
  error: { label: '严重问题', color: 'bg-destructive/15 text-destructive border-destructive/30', dot: 'bg-destructive' },
  warning: { label: '需改进', color: 'bg-warning/15 text-warning border-warning/30', dot: 'bg-warning' },
  info: { label: '建议', color: 'bg-primary/15 text-primary border-primary/30', dot: 'bg-primary' },
}

const scoreItems = [
  { label: '事实/观点/推理分区', score: 2, max: 5, comment: '缺少来源标注，事实与观点混用' },
  { label: '价值投资框架覆盖', score: 3, max: 5, comment: '基础财务覆盖，但缺少价值陷阱检查' },
  { label: '卖方观点二次消化', score: 1, max: 5, comment: '直接复读卖方结论，无买方独立判断' },
  { label: '反证风险意识', score: 1, max: 5, comment: '缺少专项反证分析' },
  { label: '结论与证据一致性', score: 3, max: 5, comment: '部分结论有数据支撑，但假设未显式说明' },
]

export function ReviewPanel() {
  const [memoText, setMemoText] = useState(sampleMemo)
  const [isReviewing, setIsReviewing] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const [selectedIssue, setSelectedIssue] = useState<string | null>('1')

  const handleReview = () => {
    setIsReviewing(true)
    setTimeout(() => {
      setIsReviewing(false)
      setShowResults(true)
    }, 2500)
  }

  const totalScore = scoreItems.reduce((sum, item) => sum + item.score, 0)
  const maxScore = scoreItems.reduce((sum, item) => sum + item.max, 0)
  const scorePercent = Math.round((totalScore / maxScore) * 100)

  return (
    <div className="mx-auto max-w-screen-2xl px-6 py-8">
      <div className="grid grid-cols-12 gap-6">
        {/* Left: Input */}
        <div className="col-span-5 space-y-4">
          <div>
            <h1 className="text-xl font-semibold text-foreground">研究报告批改模式</h1>
            <p className="mt-1 text-sm text-muted-foreground leading-relaxed">
              上传或粘贴您写的研究报告，AI 将按照价值投资研究准则进行批改，指出不符合买方研究标准的地方。
            </p>
          </div>

          <div className="rounded-lg border border-border bg-card overflow-hidden">
            <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
              <span className="text-xs font-medium text-foreground">粘贴研究报告</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setMemoText(sampleMemo)}
                  className="text-xs text-primary hover:underline"
                >
                  载入示例报告
                </button>
                <button
                  onClick={() => { setMemoText(''); setShowResults(false) }}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  清空
                </button>
              </div>
            </div>
            <Textarea
              value={memoText}
              onChange={e => { setMemoText(e.target.value); setShowResults(false) }}
              placeholder="粘贴您写的研究报告、投资笔记或 Memo 初稿…"
              className="min-h-[400px] resize-none rounded-none border-0 bg-secondary/20 font-mono text-xs text-foreground placeholder:text-muted-foreground focus:ring-0 leading-relaxed"
            />
            <div className="flex items-center justify-between border-t border-border px-4 py-2.5">
              <span className="text-xs text-muted-foreground">{memoText.length} 字</span>
              <button
                onClick={handleReview}
                disabled={!memoText.trim() || isReviewing}
                className="flex items-center gap-2 rounded-md bg-primary px-4 py-1.5 text-xs font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-all"
              >
                {isReviewing ? (
                  <>
                    <div className="h-3 w-3 rounded-full border-2 border-primary-foreground border-t-transparent animate-spin" />
                    <span>批改中…</span>
                  </>
                ) : '开始批改'}
              </button>
            </div>
          </div>

          {/* Criteria */}
          <div className="rounded-lg border border-border bg-card p-4 space-y-2">
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">批改维度</div>
            {[
              '事实 / 观点 / 假设 / AI推理 分区是否清晰',
              '是否存在卖方观点复读（无二次消化）',
              '是否直接把高股息等同于安全',
              '是否直接把低估值等同于安全边际',
              '是否缺少反证风险和价值陷阱检查',
              '结论是否有足够证据支撑',
              '是否符合机构价值投资研究标准',
            ].map((item, i) => (
              <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                <div className="h-1.5 w-1.5 rounded-full bg-primary/50 mt-1.5 shrink-0" />
                {item}
              </div>
            ))}
          </div>
        </div>

        {/* Right: Review results */}
        <div className="col-span-7 space-y-4">
          {!showResults && !isReviewing && (
            <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-border bg-card">
              <div className="text-center">
                <div className="h-10 w-10 rounded-full border border-border bg-secondary flex items-center justify-center mx-auto mb-3">
                  <svg className="h-5 w-5 text-muted-foreground" fill="none" viewBox="0 0 20 20">
                    <path d="M10 2L3 7v11h5v-5h4v5h5V7L10 2z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                  </svg>
                </div>
                <div className="text-sm text-muted-foreground">粘贴研究报告后点击"开始批改"</div>
                <div className="text-xs text-muted-foreground/60 mt-1">AI 将按价值投资研究准则进行评分和批注</div>
              </div>
            </div>
          )}

          {isReviewing && (
            <div className="rounded-lg border border-primary/30 bg-card p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center">
                  <div className="h-4 w-4 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                </div>
                <div>
                  <div className="text-sm font-medium text-foreground">Research Coach 批改中…</div>
                  <div className="text-xs text-muted-foreground mt-0.5">正在对照价值投资研究准则逐项检查</div>
                </div>
              </div>
              <div className="space-y-2">
                {['检查事实/观点/推理分区…', '识别卖方观点复读…', '检查高股息/低估值误判…', '检查反证风险意识…', '综合评分中…'].map((step, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-muted-foreground">
                    <div className="h-1.5 w-1.5 rounded-full bg-primary/50 animate-pulse" />
                    {step}
                  </div>
                ))}
              </div>
            </div>
          )}

          {showResults && (
            <div className="space-y-4 fade-in-up">
              {/* Score summary */}
              <div className="rounded-lg border border-border bg-card p-4">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="text-sm font-semibold text-foreground">批改评分</div>
                    <div className="text-xs text-muted-foreground mt-0.5">基于价值投资研究准则，共 5 个维度</div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-foreground">{totalScore}<span className="text-sm text-muted-foreground font-normal">/{maxScore}</span></div>
                    <div className={`text-xs font-medium ${scorePercent >= 70 ? 'text-success' : scorePercent >= 50 ? 'text-warning' : 'text-destructive'}`}>
                      {scorePercent >= 70 ? '基本合格' : scorePercent >= 50 ? '需要改进' : '存在重大问题'}
                    </div>
                  </div>
                </div>
                <div className="space-y-2">
                  {scoreItems.map(item => (
                    <div key={item.label}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-muted-foreground">{item.label}</span>
                        <span className="text-xs font-medium text-foreground">{item.score}/{item.max}</span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${
                            item.score / item.max >= 0.6 ? 'bg-success' : item.score / item.max >= 0.4 ? 'bg-warning' : 'bg-destructive'
                          }`}
                          style={{ width: `${(item.score / item.max) * 100}%` }}
                        />
                      </div>
                      <div className="text-[10px] text-muted-foreground mt-0.5">{item.comment}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Issue summary */}
              <div className="flex items-center gap-2">
                {(['error', 'warning', 'info'] as const).map(sev => {
                  const count = reviewIssues.filter(i => i.severity === sev).length
                  const cfg = severityConfig[sev]
                  return (
                    <div key={sev} className={`flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs ${cfg.color}`}>
                      <div className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
                      {count} 项{cfg.label}
                    </div>
                  )
                })}
              </div>

              {/* Issues list */}
              <div className="space-y-2">
                {reviewIssues.map(issue => {
                  const cfg = severityConfig[issue.severity]
                  const isSelected = selectedIssue === issue.id
                  return (
                    <div
                      key={issue.id}
                      className={`rounded-lg border bg-card cursor-pointer transition-all ${
                        isSelected ? 'border-primary/40' : 'border-border hover:border-border'
                      }`}
                      onClick={() => setSelectedIssue(isSelected ? null : issue.id)}
                    >
                      <div className="flex items-start gap-3 p-3">
                        <div className={`h-1.5 w-1.5 rounded-full mt-1.5 shrink-0 ${cfg.dot}`} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge className={`text-[9px] h-4 ${cfg.color}`}>{cfg.label}</Badge>
                            <span className="text-xs font-medium text-foreground">{issue.category}</span>
                          </div>
                          <div className="text-xs text-muted-foreground italic border-l-2 border-border pl-2 py-0.5 mb-1.5">
                            &ldquo;{issue.quote}&rdquo;
                          </div>
                          {isSelected && (
                            <div className="space-y-2 mt-2 fade-in-up">
                              <div className="text-xs text-foreground leading-relaxed bg-secondary/50 rounded p-2.5 border border-border">
                                <span className="text-destructive font-medium">问题：</span>{issue.issue}
                              </div>
                              <div className="text-xs text-foreground leading-relaxed bg-success/5 rounded p-2.5 border border-success/20">
                                <span className="text-success font-medium">建议：</span>{issue.suggestion}
                              </div>
                            </div>
                          )}
                        </div>
                        <svg
                          className={`h-4 w-4 text-muted-foreground transition-transform shrink-0 mt-0.5 ${isSelected ? 'rotate-180' : ''}`}
                          fill="none" viewBox="0 0 16 16"
                        >
                          <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Summary */}
              <div className="rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground leading-relaxed">
                <div className="text-xs font-medium text-foreground mb-2">总体评价</div>
                <p>
                  该报告具备基础财务分析框架，现金流和资产负债表数据引用准确。
                  但存在以下主要问题：<span className="text-warning">卖方观点被直接当作买方结论复读</span>；
                  <span className="text-destructive">高股息和"合理估值"的判断缺少可持续性验证</span>；
                  <span className="text-warning">全文缺少反证风险和价值陷阱专项检查</span>。
                  这是典型的初级研究员常见问题——资料整理能力较好，但买方独立判断和反证意识有待加强。
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
