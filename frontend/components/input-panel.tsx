'use client'

import { useState, useRef, type ChangeEvent } from 'react'
import { Textarea } from '@/components/ui/textarea'

interface MaterialItem {
  id: string
  type: string
  name: string
  size?: string
  status: 'ready' | 'missing'
  content?: string
  file?: File
  files?: File[]
}

interface InputPanelProps {
  projectId?: string | null
  initialCompany?: { stockCode: string; companyName: string; industry: string } | null
  onStartAnalysis: (data: {
    stockCode: string
    companyName: string
    industry: string
    projectId?: string | null
    researchObjective: string
    investmentHorizon: string
    initialView: string
    keyQuestion: string
    materials: MaterialItem[]
  }) => void
}

const materialTypes = [
  { id: 'financial', label: '财务数据表', icon: '📊', hint: '年报财务表、Excel 格式', required: true },
  { id: 'annual', label: '年报摘要', icon: '📋', hint: '年报核心内容摘要', required: true },
  { id: 'management', label: '管理层交流纪要', icon: '💬', hint: '业绩会、路演记录', required: false },
  { id: 'sellside', label: '卖方研报', icon: '📄', hint: '支持同时上传多份券商研报 PDF，用于比较共同点、分歧点和假设差异', required: false },
  { id: 'news', label: '新闻与行业资料', icon: '📰', hint: '相关新闻、行业研究', required: false },
  { id: 'notes', label: '已有研究笔记', icon: '✏️', hint: '用户自己的初步分析', required: false },
]

const sampleCompanies = [
  { code: '600519', name: '贵州茅台', industry: '白酒 / 消费品' },
  { code: '000858', name: '五粮液', industry: '白酒 / 消费品' },
  { code: '601318', name: '中国平安', industry: '保险' },
  { code: '000333', name: '美的集团', industry: '家电制造' },
]

const sampleTexts: Record<string, string> = {
  financial: `【财务摘要 - 贵州茅台 2023年报】
营业收入：1,476.94 亿元，同比 +18.04%
净利润：747.34 亿元，同比 +19.16%
经营活动现金流量净额：692.50 亿元
自由现金流：约 650 亿元
分红总额：359.07 亿元（分红率 48%）
期末现金及等价物：381.37 亿元
有息负债：0（无有息负债）
资产负债率：19.8%（主要为合同负债/预收款）
ROE：36.5%（不含高杠杆）
毛利率：91.97%
净利率：50.6%`,

  annual: `【年报摘要 - 贵州茅台 2023】
公司介绍：贵州茅台酒股份有限公司，主营高端白酒，旗舰产品茅台酒（飞天）市场地位稳固。
核心业务：茅台酒（直销+经销）约占营收85%，系列酒占15%。
直销渠道占比提升：i茅台数字营销平台直销占比约28%（较2022年提升约5pct），有助于提高利润率。
提价情况：2023年未进行官方提价，出厂价保持1499元，但市场价（飞天茅台散瓶）维持2500-2700元区间。
管理层表态：将保持稳健经营，坚持"有多少资源办多少事"原则，不追求速度。
产能情况：基酒产能约5.72万吨，茅台酒销量受配额限制，短期内大幅扩产概率低。`,

  sellside: `【卖方研报观点摘要（仅供研究参考）】
看多观点（主流）：
- 某券商A：直销占比提升是核心逻辑，未来3年EPS CAGR预计约15%，目标价2200元。
- 某券商B：品牌护城河深厚，稀缺产能是定价权核心，现金储备充裕，股息率+回购提升股东回报。

看空/谨慎观点（少数）：
- 某券商C：高端白酒需求受宏观消费降级影响，商务宴请需求弹性较大，若经济持续承压，出货压力可能上升。
- 某机构研报：i茅台平台渠道库存透明度不足，实际动销数据需持续验证。

分歧点：直销占比提升能否持续 vs 宏观消费不确定性影响需求。`,
}

export function InputPanel({ onStartAnalysis, projectId, initialCompany }: InputPanelProps) {
  const [stockCode, setStockCode] = useState(initialCompany?.stockCode || '')
  const [companyName, setCompanyName] = useState(initialCompany?.companyName || '')
  const [industry, setIndustry] = useState(initialCompany?.industry || '')
  const [researchObjective, setResearchObjective] = useState('')
  const [investmentHorizon, setInvestmentHorizon] = useState('3-5年')
  const [initialView, setInitialView] = useState('')
  const [keyQuestion, setKeyQuestion] = useState('')
  const [activeType, setActiveType] = useState<string | null>('financial')
  const [materialContents, setMaterialContents] = useState<Record<string, string>>({})
  const [uploadedFiles, setUploadedFiles] = useState<Record<string, File[]>>({})
  const fileRef = useRef<HTMLInputElement>(null)

  const handleSampleCompany = (c: typeof sampleCompanies[0]) => {
    setStockCode(c.code)
    setCompanyName(c.name)
    setIndustry(c.industry)
  }

  const handleTextChange = (id: string, value: string) => {
    setMaterialContents(prev => ({ ...prev, [id]: value }))
  }

  const handleUploadClick = (id: string) => {
    setActiveType(id)
    fileRef.current?.click()
  }

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || [])
    if (!files.length || !activeType) return
    setUploadedFiles(prev => ({
      ...prev,
      [activeType]: activeType === 'sellside' ? [...(prev[activeType] || []), ...files] : [files[0]],
    }))
    event.target.value = ''
  }

  const removeUploadedFile = (id: string, index: number) => {
    setUploadedFiles(prev => {
      const remaining = (prev[id] || []).filter((_, fileIndex) => fileIndex !== index)
      const next = { ...prev }
      if (remaining.length) {
        next[id] = remaining
      } else {
        delete next[id]
      }
      return next
    })
  }

  const materialReady = (id: string) => Boolean(materialContents[id]?.trim() || uploadedFiles[id]?.length)
  const uploadedFileCount = (id: string) => uploadedFiles[id]?.length || 0
  const uploadedFileSize = (id: string) => (uploadedFiles[id] || []).reduce((sum, file) => sum + file.size, 0)
  const filledCount = materialTypes.filter(m => materialReady(m.id)).length

  const handleStart = () => {
    if (!stockCode || !companyName) return
    const materials: MaterialItem[] = materialTypes.map(m => ({
      id: m.id,
      type: m.label,
      name: uploadedFileCount(m.id) > 1
        ? `${m.label}（${uploadedFileCount(m.id)} 份文件）`
        : uploadedFiles[m.id]?.[0]?.name || (materialContents[m.id] ? `${m.label}（粘贴文本）` : ''),
      size: uploadedFileCount(m.id) ? `${Math.round(uploadedFileSize(m.id) / 1024)} KB` : undefined,
      status: materialReady(m.id) ? 'ready' : 'missing',
      content: materialContents[m.id] || '',
      file: uploadedFiles[m.id]?.[0],
      files: uploadedFiles[m.id] || [],
    }))
    onStartAnalysis({ stockCode, companyName, industry, projectId, researchObjective, investmentHorizon, initialView, keyQuestion, materials })
  }

  return (
    <div className="mx-auto max-w-screen-2xl px-6 py-8">
      <div className="grid grid-cols-12 gap-6">
        {/* Left: Company Info */}
        <div className="col-span-4 space-y-5">
          {/* Title */}
          <div>
            <h1 className="text-xl font-semibold text-foreground">{projectId ? '补充项目资料' : '新建研究任务'}</h1>
            <p className="mt-1 text-sm text-muted-foreground leading-relaxed">
              输入公司信息，上传或粘贴研究资料，AI 将按照价值投资框架完成分析。
            </p>
          </div>

          {/* Company Info Card */}
          <div className="rounded-lg border border-border bg-card p-4 space-y-4">
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">公司基础信息</div>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-muted-foreground mb-1.5 block">股票代码</label>
                <input
                  type="text"
                  value={stockCode}
                  onChange={e => setStockCode(e.target.value)}
                  placeholder="例：600519"
                  className="w-full rounded-md border border-border bg-input px-3 py-2 text-sm font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1.5 block">公司名称</label>
                <input
                  type="text"
                  value={companyName}
                  onChange={e => setCompanyName(e.target.value)}
                  placeholder="例：贵州茅台"
                  className="w-full rounded-md border border-border bg-input px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1.5 block">所属行业</label>
                <input
                  type="text"
                  value={industry}
                  onChange={e => setIndustry(e.target.value)}
                  placeholder="例：白酒 / 消费品"
                  className="w-full rounded-md border border-border bg-input px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-xs text-muted-foreground mb-1.5 block">研究目的</label><input value={researchObjective} onChange={e => setResearchObjective(e.target.value)} placeholder="例：验证现金流质量" className="w-full rounded-md border border-border bg-input px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary" /></div>
                <div><label className="text-xs text-muted-foreground mb-1.5 block">投资期限</label><input value={investmentHorizon} onChange={e => setInvestmentHorizon(e.target.value)} className="w-full rounded-md border border-border bg-input px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary" /></div>
              </div>
              <div><label className="text-xs text-muted-foreground mb-1.5 block">初步判断</label><Textarea value={initialView} onChange={e => setInitialView(e.target.value)} placeholder="写下当前判断，后续系统会主动寻找反证" className="min-h-20 bg-input text-sm" /></div>
              <div><label className="text-xs text-muted-foreground mb-1.5 block">最想验证的问题</label><Textarea value={keyQuestion} onChange={e => setKeyQuestion(e.target.value)} placeholder="例：资本开支是否会侵蚀自由现金流？" className="min-h-20 bg-input text-sm" /></div>
            </div>

            {/* Quick select */}
            <div>
              <div className="text-xs text-muted-foreground mb-2">快速选择示例公司</div>
              <div className="grid grid-cols-2 gap-1.5">
                {sampleCompanies.map(c => (
                  <button
                    key={c.code}
                    onClick={() => handleSampleCompany(c)}
                    className={`text-left px-2.5 py-2 rounded-md border text-xs transition-all ${
                      stockCode === c.code
                        ? 'border-primary/50 bg-primary/10 text-primary'
                        : 'border-border bg-secondary/50 text-muted-foreground hover:border-border hover:text-foreground'
                    }`}
                  >
                    <div className="font-mono font-medium">{c.code}</div>
                    <div className="truncate">{c.name}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Research checklist */}
          <div className="rounded-lg border border-border bg-card p-4 space-y-3">
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">价值投资分析维度</div>
            {[
              '现金流质量与自由现金流',
              '分红可持续性分析',
              '资产负债表安全性',
              '商业模式与竞争护城河',
              '管理层资本配置',
              '卖方共识与分歧拆解',
              '价值陷阱与反证风险',
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <div className="h-1.5 w-1.5 rounded-full bg-primary/60" />
                <span className="text-muted-foreground">{item}</span>
              </div>
            ))}
          </div>

          {/* Start button */}
          <div>
            <div className="mb-2 flex items-center justify-between text-xs text-muted-foreground">
              <span>已添加资料</span>
              <span className="font-medium text-foreground">{filledCount} / {materialTypes.length}</span>
            </div>
            <div className="mb-3 h-1.5 w-full rounded-full bg-secondary overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all duration-500"
                style={{ width: `${(filledCount / materialTypes.length) * 100}%` }}
              />
            </div>
            <button
              onClick={handleStart}
              disabled={!stockCode || !companyName || filledCount === 0}
              className="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-all hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              开始 AI 研究分析
            </button>
            <p className="mt-2 text-center text-[11px] text-muted-foreground">
              本工具仅作为研究训练用途，不构成投资建议
            </p>
          </div>
        </div>

        {/* Right: Material Inputs */}
        <div className="col-span-8 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-foreground">研究资料包</h2>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>支持粘贴文字摘要或上传文件</span>
            </div>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".txt,.md,.csv,.docx,.xlsx,.pdf,.png,.jpg,.jpeg,.webp,.mp3,.m4a,.wav,.mp4"
            multiple={activeType === 'sellside'}
            className="hidden"
            onChange={handleFileChange}
          />

          {/* Tab selector */}
          <div className="flex flex-wrap gap-2">
            {materialTypes.map(m => (
              <button
                key={m.id}
                onClick={() => setActiveType(m.id)}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all border ${
                  activeType === m.id
                    ? 'border-primary/50 bg-primary/10 text-primary'
                    : materialReady(m.id)
                    ? 'border-success/30 bg-success/5 text-success'
                    : 'border-border bg-secondary/50 text-muted-foreground hover:text-foreground hover:border-border'
                }`}
              >
                {materialReady(m.id) && activeType !== m.id && (
                  <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 12 12">
                    <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                )}
                {m.label}
                {uploadedFileCount(m.id) > 1 && <span className="text-[10px]">×{uploadedFileCount(m.id)}</span>}
                {m.required && <span className="text-destructive">*</span>}
              </button>
            ))}
          </div>

          {/* Active material editor */}
          {activeType && (() => {
            const mt = materialTypes.find(m => m.id === activeType)!
            return (
              <div className="rounded-lg border border-border bg-card overflow-hidden fade-in-up">
                <div className="flex items-center justify-between border-b border-border px-4 py-3">
                  <div>
                    <div className="text-sm font-medium text-foreground">{mt.label}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{mt.hint}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    {sampleTexts[activeType] && (
                      <button
                        onClick={() => handleTextChange(activeType, sampleTexts[activeType])}
                        className="text-xs text-primary hover:underline"
                      >
                        载入示例数据
                      </button>
                    )}
                    <button
                      onClick={() => handleUploadClick(activeType)}
                      className="text-xs text-primary hover:underline"
                    >
                      {activeType === 'sellside' ? '上传多份研报' : '上传文件'}
                    </button>
                    <button
                      onClick={() => {
                        handleTextChange(activeType, '')
                        setUploadedFiles(prev => {
                          const next = { ...prev }
                          delete next[activeType]
                          return next
                        })
                      }}
                      className="text-xs text-muted-foreground hover:text-foreground"
                    >
                      清空
                    </button>
                  </div>
                </div>
                <div className="p-4">
                  <Textarea
                    value={materialContents[activeType] || ''}
                    onChange={e => handleTextChange(activeType, e.target.value)}
                    placeholder={`粘贴 ${mt.label} 内容，或简要描述相关信息…\n\n支持：摘要文字 / 财务数据片段 / 管理层引言 / 新闻摘要`}
                    className="min-h-[280px] resize-none border-border bg-secondary/30 text-sm text-foreground placeholder:text-muted-foreground focus:ring-primary font-mono"
                  />
                  {uploadedFileCount(activeType) > 0 && (
                    <div className="mt-3 rounded-md border border-border bg-secondary/30 p-3">
                      <div className="mb-2 flex items-center justify-between">
                        <span className="text-xs font-medium text-foreground">
                          已上传文件 {uploadedFileCount(activeType)} 份
                        </span>
                        {activeType === 'sellside' && (
                          <span className="text-[10px] text-muted-foreground">将作为多份卖方研报输入进行横向比较</span>
                        )}
                      </div>
                      <div className="space-y-1.5">
                        {(uploadedFiles[activeType] || []).map((file, index) => (
                          <div key={`${file.name}-${index}`} className="flex items-center gap-2 rounded border border-border/60 bg-card/50 px-2 py-1.5">
                            <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">{file.name}</span>
                            <span className="text-[10px] text-muted-foreground">{Math.round(file.size / 1024)} KB</span>
                            <button
                              type="button"
                              onClick={() => removeUploadedFile(activeType, index)}
                              className="text-[10px] text-muted-foreground hover:text-destructive"
                            >
                              移除
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                    <span>{(materialContents[activeType] || '').length} 字</span>
                    <div className="flex items-center gap-3">
                      <span>支持文档 / 表格 / 图片 / 音频</span>
                      {uploadedFileCount(activeType) > 0 && (
                        <span className="text-primary flex items-center gap-1">
                          已上传：{uploadedFileCount(activeType)} 份
                        </span>
                      )}
                      {materialReady(activeType) && (
                        <span className="text-success flex items-center gap-1">
                          <svg className="h-3 w-3" fill="none" viewBox="0 0 12 12">
                            <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                          已录入
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )
          })()}

          {/* Material overview */}
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">资料覆盖情况</div>
            <div className="grid grid-cols-3 gap-2">
              {materialTypes.map(m => (
                <div
                  key={m.id}
                  className={`flex items-center gap-2 rounded-md border px-3 py-2 cursor-pointer transition-all ${
                    materialReady(m.id)
                      ? 'border-success/30 bg-success/5'
                      : 'border-border bg-secondary/30'
                  }`}
                  onClick={() => setActiveType(m.id)}
                >
                  <div className={`h-2 w-2 rounded-full shrink-0 ${
                    materialReady(m.id) ? 'bg-success' : 'bg-muted-foreground/30'
                  }`} />
                  <span className={`text-xs truncate ${
                    materialReady(m.id) ? 'text-foreground' : 'text-muted-foreground'
                  }`}>
                    {m.label}
                    {uploadedFileCount(m.id) > 1 ? `（${uploadedFileCount(m.id)}份）` : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Disclaimer */}
          <div className="rounded-md border border-warning/20 bg-warning/5 p-3 text-xs text-muted-foreground leading-relaxed">
            <span className="text-warning font-medium">资料使用说明：</span>
            请确保您有权使用所上传的研究资料。系统不抓取付费研报全文，不联网搜索，不自动生成未经验证的财务数据。所有分析输出均基于您提供的资料，关键事实将标注来源。
          </div>
        </div>
      </div>
    </div>
  )
}
