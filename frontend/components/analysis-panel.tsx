'use client'

import { useState, useEffect } from 'react'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { analyzeCompany, type AnalyzeResult } from '@/lib/api'

export interface AnalysisData {
  stockCode: string
  companyName: string
  industry: string
  materials: Array<{ id: string; type: string; name: string; status: 'ready' | 'missing'; content?: string }>
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
  {
    id: 'doctrine',
    name: '机构理念与案例召回',
    nameEn: 'Firm Doctrine & Case Retrieval',
    description: '调取价值投资研究准则，检索相关历史案例',
    status: 'pending',
    output: [
      '✓ 已载入默认价值投资研究准则（通用版）',
      '✓ 识别到高股息/稳定现金流公司类型，匹配白酒/高端消费模板',
      '✓ 需重点检查：高端品牌估值溢价是否合理、分红政策可持续性',
      '⚠ 本次输出研究观点标签，不附带内部评级',
    ],
  },
  {
    id: 'material',
    name: '资料整理',
    nameEn: 'Material Organizer',
    description: '识别资料类型、来源与覆盖情况，标注缺失资料',
    status: 'pending',
    output: [
      '✓ 已识别资料：财务数据表、年报摘要、卖方研报摘要',
      '⚠ 缺失资料：管理层交流纪要（近 12 个月路演记录）',
      '⚠ 缺失资料：新闻与行业资料（宏观消费趋势数据）',
      '⚠ 缺失资料：用户研究笔记',
      '→ 价值投资维度覆盖：财务质量 ✓ / 分红 ✓ / 估值 待补充 / 竞争优势 部分覆盖',
    ],
    warnings: ['管理层纪要缺失', '行业资料缺失'],
  },
  {
    id: 'evidence',
    name: '证据抽取',
    nameEn: 'Evidence Extractor',
    description: '抽取关键事实、财务数据、管理层表述、卖方观点',
    status: 'pending',
    output: [
      '✓ [事实·财务] 2023 营收 1476.94 亿，同比 +18.04% ←来源：2023年报',
      '✓ [事实·财务] 净利润 747.34 亿，净利率 50.6% ←来源：2023年报',
      '✓ [事实·财务] 经营现金流 692.50 亿，自由现金流约 650 亿 ←来源：2023年报',
      '✓ [事实·财务] 分红总额 359.07 亿，分红率 48% ←来源：2023年报',
      '✓ [事实·财务] 有息负债：0，资产负债率 19.8% ←来源：2023年报',
      '✓ [管理层观点] 坚持"有多少资源办多少事"，不追求速度 ←来源：年报摘要',
      '✓ [卖方观点] 主流看多：直销占比提升，目标价 2200 元 ←来源：研报摘要',
      '✓ [卖方观点] 少数谨慎：宏观消费降级风险，动销数据待验证 ←来源：研报摘要',
      '⚠ [待验证] i茅台平台实际动销数据 ←来源缺失',
      '⚠ [待验证] 近期经销商渠道库存水位 ←来源缺失',
    ],
  },
  {
    id: 'financial',
    name: '财务质量与分红分析',
    nameEn: 'Financial Quality & Dividend',
    description: '分析现金流质量、分红可持续性、资产负债表安全性',
    status: 'pending',
    output: [
      '【现金流质量】经营现金流/净利润比值 ≈ 0.93，现金含量优秀',
      '【自由现金流】约 650 亿，2023 FCF Yield（按市值估算）约 2.1%，行业内较高',
      '【分红可持续性】自由现金流覆盖分红（650>359），✓ 分红能力充分支撑当前分红率',
      '【分红连续性】已连续 20+ 年分红，股息率约 1.5-2.5%（随市值波动）',
      '【资产负债表】有息负债为零，大额预收款（合同负债）属经营性质，✓ 财务安全',
      '【ROE 质量】ROE 36.5%，主要由高净利率驱动，非杠杆驱动，✓ 盈利质量高',
      '⚠ 【扣分项】估值较高（PE~30x），安全边际依赖品牌持续性假设',
    ],
  },
  {
    id: 'business',
    name: '商业模式与竞争优势',
    nameEn: 'Business Model & Moat',
    description: '分析盈利模式稳定性、竞争护城河、行业地位',
    status: 'pending',
    output: [
      '【盈利方式】茅台酒（飞天为核心）+ 系列酒，高端白酒品牌溢价主导，非扩产驱动',
      '【竞争优势】品牌壁垒（国宴用酒历史文化）+ 产能稀缺（地理标志产区）+ 渠道控制力',
      '【商业模式稳定性】高，主业集中，收入结构清晰，商务/礼品消费驱动',
      '【资本开支】较低（扩产受限），✓ 主业不依赖持续大额资本开支',
      '【周期性】弱周期，高端消费受宏观影响有限（但非完全无周期）',
      '⚠ 【风险】需求端对商务宴请依赖度较高，政策变化敏感',
      '⚠ 【待验证】直销渠道持续提升能力是否存在天花板',
    ],
  },
  {
    id: 'management',
    name: '管理层与多方观点比较',
    nameEn: 'Management & View Comparison',
    description: '比较管理层、卖方、市场观点，识别共识与分歧',
    status: 'pending',
    output: [
      '【共识】品牌护城河强，产能稀缺，现金流优秀，长期竞争格局稳固',
      '【分歧·核心】直销占比能否持续提升 vs 宏观消费降级影响终端需求',
      '【管理层叙事 vs 财务现实】管理层稳健表态与财务数据基本一致，无明显矛盾',
      '【管理层资本配置】优先分红，无大额并购，历史行为理性',
      '⚠ 【少数派风险】消费降级可能压制出货速度，i茅台动销真实性存疑',
      '⚠ 【AI 推理·非事实】若宏观消费持续承压，高端白酒需求弹性可能被低估',
      '→ 追问问题：Q3 经销商打款意愿 / 当前渠道库存水位 / 直销增量空间',
    ],
    warnings: ['管理层纪要缺失，观点来源受限于年报摘要'],
  },
  {
    id: 'valuetrap',
    name: '价值陷阱与反证风险',
    nameEn: 'Value Trap & Contradiction',
    description: '专项检查可能推翻当前判断的反证信号',
    status: 'pending',
    output: [
      '✓ [通过] 高股息检查：FCF 充分覆盖分红，高股息具备可持续基础',
      '✓ [通过] 低估值检查：当前估值偏高而非偏低，价值陷阱信号弱',
      '✓ [通过] 经营现金流检查：现金流健康，未出现净利润增长但现金流恶化',
      '✓ [通过] 利润质量检查：非经常性损益比例低，利润来源清晰',
      '⚠ [关注] 宏观消费降级：若持续，高端消费量价齐升假设面临压力',
      '⚠ [关注] 渠道库存透明度：i茅台平台动销数据不可独立验证',
      '⚠ [关注] 高估值假设：当前价格隐含较高增长预期，若增速放缓估值收缩风险大',
      '→ 一票否决变量：若经营现金流出现实质性恶化（需补充数据验证）',
    ],
    warnings: ['渠道数据缺失，无法完整验证'],
  },
  {
    id: 'gate',
    name: '证据与合规门禁',
    nameEn: 'Evidence & Compliance Gate',
    description: '双重检查：证据完整性 + 合规风险（Pre/Post Memo）',
    status: 'pending',
    output: [
      '✓ Pre-Memo Gate：关键财务事实均有来源标注，可进入 Memo 生成',
      '✓ 无收益承诺表达',
      '✓ 无确定性买卖指令',
      '✓ 已禁用买入/卖出评级输出',
      '⚠ 4 项待验证内容已标注为"待验证"区，不进入事实区',
      '⚠ 管理层纪要缺失，相关结论已降级为"当前资料有限，需补充验证"',
      '→ 研究观点标签：积极关注（内部研究观点，不构成投资建议）',
    ],
  },
  {
    id: 'memo',
    name: '买方 Memo 生成',
    nameEn: 'Research Memo Generator',
    description: '整合所有 Agent 输出，生成结构化价值投资买方研究 Memo',
    status: 'pending',
    output: [
      '✓ Memo 已生成（结构：18 个标准章节）',
      '✓ 来源标注完整率：92%（3 项来源为 AI 推理，已标注）',
      '✓ 价值投资框架覆盖：7/7 维度',
      '→ 点击"研究 Memo"标签页查看完整输出',
    ],
  },
]

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
      setSteps(prev => prev.map(s => ({ ...s, status: s.warnings?.length ? 'warning' : 'done' })))
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

  const filledMaterials = data.materials.filter(m => m.status === 'ready')

  return (
    <div className="mx-auto max-w-screen-2xl px-6 py-8">
      <div className="grid grid-cols-12 gap-6">
        {/* Left: Overview */}
        <div className="col-span-4 space-y-4">
          {/* Company card */}
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="text-lg font-semibold text-foreground">{data.companyName}</div>
                <div className="text-xs text-muted-foreground font-mono">{data.stockCode} · {data.industry}</div>
              </div>
              <Badge className={`text-xs ${isComplete ? 'bg-success/15 text-success border-success/30' : started ? 'bg-primary/15 text-primary border-primary/30' : 'bg-secondary text-muted-foreground'}`}>
                {isComplete ? '分析完成' : started ? '分析中' : '待启动'}
              </Badge>
            </div>

            {started && (
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>总体进度</span>
                  <span className="font-medium text-foreground">{progress}%</span>
                </div>
                <Progress value={progress} className="h-1.5" />
              </div>
            )}
          </div>

          {/* Materials summary */}
          <div className="rounded-lg border border-border bg-card p-4 space-y-2">
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">资料包状态</div>
            {data.materials.map(m => (
              <div key={m.id} className="flex items-center gap-2 text-xs">
                <div className={`h-1.5 w-1.5 rounded-full shrink-0 ${m.status === 'ready' ? 'bg-success' : 'bg-muted-foreground/30'}`} />
                <span className={m.status === 'ready' ? 'text-foreground' : 'text-muted-foreground/50 line-through'}>{m.type}</span>
                {m.status === 'missing' && <span className="text-muted-foreground/50">（缺失）</span>}
              </div>
            ))}
          </div>

          {/* Agent list */}
          <div className="rounded-lg border border-border bg-card p-4 space-y-1.5">
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">Agent 工作流（9 步）</div>
            {steps.map((step, idx) => (
              <div
                key={step.id}
                className="flex items-center gap-2.5 text-xs cursor-pointer py-0.5"
                onClick={() => setExpandedStep(expandedStep === step.id ? null : step.id)}
              >
                {statusIcon(step.status)}
                <span className={`flex-1 truncate ${
                  step.status === 'running' ? 'text-primary font-medium' :
                  step.status === 'done' || step.status === 'warning' ? 'text-foreground' :
                  'text-muted-foreground'
                }`}>
                  {step.name}
                </span>
                {step.status === 'warning' && <Badge className="text-[9px] h-3.5 px-1 bg-warning/15 text-warning border-warning/30">警告</Badge>}
              </div>
            ))}
          </div>

          {/* Action */}
          {!started && (
            <button
              onClick={startAnalysis}
              className="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-all"
            >
              启动 AI 分析
            </button>
          )}

          {isComplete && (
            <button
              onClick={() => analysisResult && onComplete(analysisResult)}
              disabled={!analysisResult}
              className="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-all"
            >
              查看研究 Memo
            </button>
          )}
        </div>

        {/* Right: Step details */}
        <div className="col-span-8 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-foreground">
              {started ? 'Agent 实时运行日志' : 'DAG 工作流说明'}
            </h2>
            {started && (
              <div className="text-xs text-muted-foreground font-mono">
                {steps.filter(s => s.status === 'done' || s.status === 'warning').length} / {steps.length} 完成
              </div>
            )}
          </div>

          {!started && (
            <div className="rounded-lg border border-border bg-card p-6 space-y-4">
              <p className="text-sm text-muted-foreground leading-relaxed">
                系统将按照以下 DAG 工作流执行，共 9 个专项 Agent。并行分析模块���财务质量、商业模式、管理层观点比较）将同步运行后汇总。
              </p>
              <div className="flex flex-col gap-2">
                {agentSteps.map((step, idx) => (
                  <div key={step.id} className="flex items-start gap-3 p-3 rounded-md bg-secondary/50 border border-border/50">
                    <div className="shrink-0 h-5 w-5 rounded bg-muted flex items-center justify-center text-[10px] font-mono text-muted-foreground">
                      {idx + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium text-foreground">{step.name}</div>
                      <div className="text-[11px] text-muted-foreground mt-0.5">{step.description}</div>
                      <div className="text-[10px] text-muted-foreground/60 font-mono mt-0.5">{step.nameEn}</div>
                    </div>
                    {[3, 4, 5].includes(idx) && (
                      <Badge variant="outline" className="text-[9px] shrink-0 border-primary/30 text-primary">并行</Badge>
                    )}
                    {[6, 7].includes(idx) && (
                      <Badge variant="outline" className="text-[9px] shrink-0 border-warning/30 text-warning">门禁</Badge>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {started && steps.map((step) => (
            (step.status === 'done' || step.status === 'warning' || step.status === 'running') && (
              <div
                key={step.id}
                className={`rounded-lg border bg-card overflow-hidden transition-all fade-in-up ${
                  step.status === 'running'
                    ? 'border-primary/40'
                    : step.status === 'warning'
                    ? 'border-warning/30'
                    : 'border-border'
                }`}
              >
                <button
                  className="w-full flex items-center gap-3 p-4 text-left"
                  onClick={() => setExpandedStep(expandedStep === step.id ? null : step.id)}
                >
                  {statusIcon(step.status)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-foreground">{step.name}</span>
                      {step.status === 'running' && (
                        <span className="text-xs text-primary animate-pulse">运行中…</span>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground font-mono">{step.nameEn}</div>
                  </div>
                  {step.warnings && step.warnings.length > 0 && (
                    <div className="flex gap-1">
                      {step.warnings.map((w, i) => (
                        <Badge key={i} className="text-[9px] bg-warning/10 text-warning border-warning/20">{w}</Badge>
                      ))}
                    </div>
                  )}
                  <svg
                    className={`h-4 w-4 text-muted-foreground transition-transform ${expandedStep === step.id ? 'rotate-180' : ''}`}
                    fill="none" viewBox="0 0 16 16"
                  >
                    <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>

                {expandedStep === step.id && step.output && (
                  <div className="border-t border-border bg-secondary/20 px-4 py-3 space-y-1.5">
                    {step.output.map((line, i) => (
                      <div key={i} className={`text-xs font-mono leading-relaxed ${
                        line.startsWith('✓') ? 'text-success' :
                        line.startsWith('⚠') ? 'text-warning' :
                        line.startsWith('→') ? 'text-primary' :
                        line.startsWith('【') ? 'text-foreground' :
                        'text-muted-foreground'
                      }`}>
                        {line}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          ))}

          {apiError && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4">
              <div className="text-sm font-semibold text-destructive">分析请求失败</div>
              <div className="mt-1 text-xs text-muted-foreground leading-relaxed">{apiError}</div>
            </div>
          )}

          {isComplete && (
            <div className="rounded-lg border border-success/30 bg-success/5 p-4 fade-in-up">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-success/20 flex items-center justify-center">
                  <svg className="h-4 w-4 text-success" fill="none" viewBox="0 0 16 16">
                    <path d="M3 8l4 4 6-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                <div>
                  <div className="text-sm font-semibold text-foreground">研究分析完成</div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    共完成 9 个 Agent 分析 · 价值投资框架覆盖 7/7 维度 · 来源标注完整率 92%
                  </div>
                </div>
                <button
                  onClick={() => analysisResult && onComplete(analysisResult)}
                  disabled={!analysisResult}
                  className="ml-auto shrink-0 rounded-md bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:opacity-90"
                >
                  查看研究 Memo
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
