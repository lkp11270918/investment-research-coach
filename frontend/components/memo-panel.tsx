'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import type { BackendEvidenceItem, BackendMemo } from '@/lib/api'
import { MEMO_CHAPTER_TITLES } from '@/lib/memo-chapters'

interface MemoPanelProps {
  companyName?: string
  stockCode?: string
  industry?: string
  hasProject?: boolean
  memo?: BackendMemo | null
  evidenceItems?: BackendEvidenceItem[]
}

const categoryLabel: Record<string, string> = {
  fact: '事实',
  financial_fact: '财务事实',
  management_opinion: '管理层观点',
  sell_side_opinion: '卖方观点',
  news_or_market_opinion: '新闻/市场观点',
  user_opinion: '用户观点',
  assumption: '假设',
  ai_reasoning: 'AI 推理',
  risk: '风险',
  verification_question: '待验证问题',
}

const categoryTone: Record<string, string> = {
  fact: 'bg-success/15 text-success border-success/30',
  financial_fact: 'bg-success/15 text-success border-success/30',
  management_opinion: 'bg-primary/15 text-primary border-primary/30',
  sell_side_opinion: 'bg-warning/15 text-warning border-warning/30',
  news_or_market_opinion: 'bg-primary/15 text-primary border-primary/30',
  user_opinion: 'bg-muted text-muted-foreground border-border',
  assumption: 'bg-warning/15 text-warning border-warning/30',
  ai_reasoning: 'bg-muted text-muted-foreground border-border',
  risk: 'bg-destructive/15 text-destructive border-destructive/30',
  verification_question: 'bg-warning/15 text-warning border-warning/30',
}

function confidenceText(value: string) {
  return value === 'high' ? '高' : value === 'medium' ? '中' : '低'
}

function verificationText(value: string) {
  return value === 'verified' ? '已验证' : value === 'partially_supported' ? '部分支持' : value === 'unsupported' ? '未支持' : '待验证'
}

function EvidenceTraceList({ evidenceIds, evidenceById }: { evidenceIds: string[]; evidenceById: Map<string, BackendEvidenceItem> }) {
  if (!evidenceIds.length) return null
  const matched = evidenceIds.map(id => evidenceById.get(id)).filter(Boolean) as BackendEvidenceItem[]
  return (
    <div className="mt-4 rounded-lg border border-border bg-card/50 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-medium text-foreground">可追溯证据</span>
        <span className="text-[10px] text-muted-foreground">{matched.length}/{evidenceIds.length} 条已匹配</span>
      </div>
      {matched.length > 0 ? (
        <div className="space-y-2">
          {matched.map(evidence => {
            const source = evidence.source_refs?.[0]
            return (
              <div key={evidence.evidence_id} className="rounded-md border border-border bg-secondary/30 p-3">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[10px] text-muted-foreground">{evidence.evidence_id}</span>
                  <Badge className={`h-4 text-[9px] ${categoryTone[evidence.category] || 'bg-muted text-muted-foreground border-border'}`}>
                    {categoryLabel[evidence.category] || evidence.category}
                  </Badge>
                  <span className="text-[10px] text-muted-foreground">置信度：{confidenceText(evidence.confidence)}</span>
                  <span className="text-[10px] text-muted-foreground">状态：{verificationText(evidence.verification_status)}</span>
                </div>
                <div className="text-xs leading-relaxed text-foreground">{evidence.statement}</div>
                {source && (
                  <div className="mt-2 rounded border border-border/60 bg-card/60 p-2 text-[10px] text-muted-foreground">
                    <div>来源：{source.source_id}{source.page ? ` · 页 ${source.page}` : ''}{source.paragraph_id ? ` · 段 ${source.paragraph_id}` : ''}{source.row_id ? ` · 行 ${source.row_id}` : ''}</div>
                    {source.excerpt && <div className="mt-1 line-clamp-3 leading-relaxed">“{source.excerpt}”</div>}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ) : <div className="text-xs text-muted-foreground">当前响应没有包含对应证据详情。</div>}
      {matched.length < evidenceIds.length && <div className="mt-2 text-[10px] text-muted-foreground">未匹配证据：{evidenceIds.filter(id => !evidenceById.has(id)).join('、')}</div>}
    </div>
  )
}

function EmptyMemo({ companyName, hasProject }: { companyName?: string; hasProject: boolean }) {
  return (
    <div className="mx-auto max-w-screen-xl px-6 py-12">
      <div className="mx-auto max-w-2xl rounded-lg border border-border bg-card p-8 text-center">
        <div className="text-xs font-medium uppercase tracking-wider text-primary">Memo</div>
        <h1 className="mt-3 text-xl font-semibold text-foreground">尚未生成研究报告</h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          {hasProject
            ? `“${companyName || '当前研究项目'}”还没有完成资料分析。请先回到 Research Map，补充资料并开始分析。`
            : '请先在 Research Map 中选择一个研究项目，或创建项目并完成一次资料分析。报告只会显示所选项目自己的研究结果。'}
        </p>
      </div>
    </div>
  )
}

export function MemoPanel({ companyName, stockCode, industry, hasProject = false, memo, evidenceItems = [] }: MemoPanelProps) {
  const [activeSection, setActiveSection] = useState<string | null>(memo?.sections[0]?.section_id || null)
  const evidenceById = new Map(evidenceItems.map(item => [item.evidence_id, item]))

  if (!memo || !memo.sections.length) return <EmptyMemo companyName={companyName} hasProject={hasProject || Boolean(companyName || stockCode || industry)} />

  const download = () => {
    const blob = new Blob([memo.markdown || memo.sections.map(section => `## ${section.title}\n\n${section.body}`).join('\n\n')], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${stockCode || companyName || '研究项目'}_研究报告.md`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="mx-auto max-w-screen-2xl px-6 py-8">
      <div className="grid grid-cols-12 gap-6">
        <aside className="col-span-3 space-y-3">
          <div className="space-y-1 rounded-lg border border-border bg-card p-4">
            <div className="mb-3">
              <div className="text-sm font-semibold text-foreground">{companyName || '未命名研究项目'}</div>
              <div className="font-mono text-xs text-muted-foreground">{stockCode || '未填写代码'} · {industry || '行业待识别'}</div>
            </div>
            <div className="mb-3 grid grid-cols-2 gap-1.5">
              <div className="rounded border border-border/50 bg-secondary/50 px-2 py-1.5"><div className="text-[10px] text-muted-foreground">置信度</div><div className="text-[11px] font-semibold text-primary">{confidenceText(memo.confidence)}</div></div>
              <div className="rounded border border-border/50 bg-secondary/50 px-2 py-1.5"><div className="text-[10px] text-muted-foreground">证据数</div><div className="text-[11px] font-semibold text-foreground">{evidenceItems.length || memo.source_ids.length}</div></div>
            </div>
            <div className="space-y-0.5">
              {memo.sections.map((section, index) => <button key={section.section_id} onClick={() => { setActiveSection(section.section_id); document.getElementById(`section-${section.section_id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }} className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs ${activeSection === section.section_id ? 'bg-accent text-foreground' : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'}`}><span className="w-5 shrink-0 font-mono text-[10px] text-muted-foreground">{String(index + 1).padStart(2, '0')}</span><span className="flex-1 truncate">{MEMO_CHAPTER_TITLES[section.section_id] || section.title}</span></button>)}
            </div>
            <div className="mt-2 border-t border-border pt-2"><button onClick={download} className="w-full rounded-md border border-border bg-secondary/50 px-3 py-2 text-xs text-foreground hover:bg-secondary">下载 Markdown</button></div>
          </div>
        </aside>
        <section className="col-span-9 space-y-4">
          <div className="flex items-center justify-between"><div><h1 className="text-lg font-semibold text-foreground">价值投资买方研究 Memo</h1><p className="mt-0.5 text-xs text-muted-foreground">仅基于当前研究项目资料生成 · 不构成投资建议 · Memo ID {memo.memo_id}</p></div><Badge className="border-primary/30 bg-primary/15 text-primary text-xs">置信度 {confidenceText(memo.confidence)}</Badge></div>
          <Accordion type="multiple" defaultValue={memo.sections.slice(0, 4).map(section => section.section_id)} className="space-y-3">
            {memo.sections.map((section, index) => <AccordionItem key={section.section_id} value={section.section_id} id={`section-${section.section_id}`} className="overflow-hidden rounded-lg border border-border bg-card data-[state=open]:border-primary/30"><AccordionTrigger className="px-4 py-3 hover:bg-accent/30 hover:no-underline"><div className="flex items-center gap-3"><span className="shrink-0 font-mono text-xs text-muted-foreground">{String(index + 1).padStart(2, '0')}</span><span className="text-sm font-medium text-foreground">{MEMO_CHAPTER_TITLES[section.section_id] || section.title}</span><Badge variant="outline" className="h-5 border-border text-[10px] text-muted-foreground">{confidenceText(section.confidence)}</Badge></div></AccordionTrigger><AccordionContent className="px-4 pb-4 pt-1"><div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">{section.body}</div><EvidenceTraceList evidenceIds={section.evidence_ids} evidenceById={evidenceById} /></AccordionContent></AccordionItem>)}
          </Accordion>
        </section>
      </div>
    </div>
  )
}
