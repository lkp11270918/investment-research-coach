'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import type { BackendEvidenceItem, BackendMemo } from '@/lib/api'

interface MemoPanelProps {
  companyName?: string
  stockCode?: string
  industry?: string
  memo?: BackendMemo | null
  evidenceItems?: BackendEvidenceItem[]
}

type EvidenceTag = 'fact' | 'opinion' | 'assumption' | 'ai'
type EvidenceItem = { text: string; tag: EvidenceTag; source?: string }

const tagConfig: Record<EvidenceTag, { label: string; color: string }> = {
  fact:       { label: '事实', color: 'bg-success/15 text-success border-success/30' },
  opinion:    { label: '观点', color: 'bg-primary/15 text-primary border-primary/30' },
  assumption: { label: '假设', color: 'bg-warning/15 text-warning border-warning/30' },
  ai:         { label: 'AI推理', color: 'bg-muted text-muted-foreground border-border' },
}

function EvidenceBadge({ tag }: { tag: EvidenceTag }) {
  const cfg = tagConfig[tag]
  return <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium border ${cfg.color} shrink-0`}>{cfg.label}</span>
}

function EvidenceLine({ item }: { item: EvidenceItem }) {
  return (
    <div className="flex items-start gap-2 py-1.5 border-b border-border/50 last:border-0">
      <EvidenceBadge tag={item.tag} />
      <span className="text-sm text-foreground leading-relaxed flex-1">{item.text}</span>
      {item.source && (
        <span className="text-[10px] text-muted-foreground font-mono shrink-0 mt-0.5">← {item.source}</span>
      )}
    </div>
  )
}

const backendCategoryLabel: Record<string, string> = {
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

const backendCategoryTone: Record<string, string> = {
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

function confidenceText(confidence: string) {
  if (confidence === 'high') return '高'
  if (confidence === 'medium') return '中'
  return '低'
}

function verificationText(status: string) {
  if (status === 'verified') return '已验证'
  if (status === 'partially_supported') return '部分支持'
  if (status === 'unsupported') return '未支持'
  return '待验证'
}

function EvidenceTraceCard({ evidence }: { evidence: BackendEvidenceItem }) {
  const source = evidence.source_refs?.[0]
  const location = [
    source?.page ? `页 ${source.page}` : null,
    source?.paragraph_id ? `段 ${source.paragraph_id}` : null,
    source?.row_id ? `行 ${source.row_id}` : null,
  ].filter(Boolean).join(' · ')
  return (
    <div className="rounded-md border border-border bg-secondary/30 p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="font-mono text-[10px] text-muted-foreground">{evidence.evidence_id}</span>
        <Badge className={`h-4 text-[9px] ${backendCategoryTone[evidence.category] || 'bg-muted text-muted-foreground border-border'}`}>
          {backendCategoryLabel[evidence.category] || evidence.category}
        </Badge>
        <span className="text-[10px] text-muted-foreground">置信度：{confidenceText(evidence.confidence)}</span>
        <span className="text-[10px] text-muted-foreground">状态：{verificationText(evidence.verification_status)}</span>
      </div>
      <div className="text-xs leading-relaxed text-foreground">{evidence.statement}</div>
      {(evidence.metric_name || evidence.period || evidence.metric_value !== undefined && evidence.metric_value !== null) && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {evidence.metric_name && <span className="rounded border border-border bg-card px-1.5 py-0.5 text-[10px] text-muted-foreground">指标：{evidence.metric_name}</span>}
          {evidence.period && <span className="rounded border border-border bg-card px-1.5 py-0.5 text-[10px] text-muted-foreground">期间：{evidence.period}</span>}
          {evidence.metric_value !== undefined && evidence.metric_value !== null && (
            <span className="rounded border border-border bg-card px-1.5 py-0.5 text-[10px] text-muted-foreground">
              数值：{evidence.metric_value}{evidence.unit || ''}
            </span>
          )}
        </div>
      )}
      {source && (
        <div className="mt-2 rounded border border-border/60 bg-card/60 p-2">
          <div className="mb-1 flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
            <span>来源：{source.source_id}</span>
            {location && <span>{location}</span>}
            {source.url && <span className="truncate">URL：{source.url}</span>}
          </div>
          {source.excerpt && (
            <div className="line-clamp-3 text-[11px] leading-relaxed text-muted-foreground">
              “{source.excerpt}”
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function EvidenceTraceList({
  evidenceIds,
  evidenceById,
}: {
  evidenceIds: string[]
  evidenceById: Map<string, BackendEvidenceItem>
}) {
  if (evidenceIds.length === 0) return null
  const items = evidenceIds.map(id => evidenceById.get(id)).filter(Boolean) as BackendEvidenceItem[]
  return (
    <div className="mt-4 rounded-lg border border-border bg-card/50 p-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="text-xs font-medium text-foreground">可追溯证据</div>
        <div className="text-[10px] text-muted-foreground">
          {items.length}/{evidenceIds.length} 条已匹配
        </div>
      </div>
      {items.length > 0 ? (
        <div className="space-y-2">
          {items.map(item => <EvidenceTraceCard key={item.evidence_id} evidence={item} />)}
        </div>
      ) : (
        <div className="text-xs text-muted-foreground">
          后端返回了证据 ID，但当前响应没有包含对应证据详情。
        </div>
      )}
      {items.length < evidenceIds.length && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {evidenceIds.filter(id => !evidenceById.has(id)).map(id => (
            <span key={id} className="rounded border border-border bg-secondary/50 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
              未匹配：{id}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

const memoSections = [
  {
    id: 'overview',
    title: '资料范围与结论置信度',
    icon: '01',
    content: (
      <div className="space-y-3 text-sm">
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: '已录入资料', value: '3 类', sub: '财务表 / 年报摘要 / 研报摘要' },
            { label: '缺失资料', value: '3 类', sub: '管理层纪要 / 新闻 / 用户笔记' },
            { label: '来源标注完整率', value: '92%', sub: '3 项 AI 推理已标注' },
          ].map(card => (
            <div key={card.label} className="rounded-md bg-secondary/50 border border-border p-3">
              <div className="text-xs text-muted-foreground">{card.label}</div>
              <div className="text-lg font-semibold text-foreground mt-1">{card.value}</div>
              <div className="text-[11px] text-muted-foreground mt-0.5">{card.sub}</div>
            </div>
          ))}
        </div>
        <div className="rounded-md border border-warning/20 bg-warning/5 p-3 text-xs text-muted-foreground leading-relaxed">
          <span className="text-warning font-medium">置信度说明：</span>
          当前资料覆盖财务质量、分红分析和卖方观点，但管理层交流纪要和行业资料缺失，部分结论置信度为中等水平。以下涉及管理层意图的判断均已降级为"待验证假设"。
        </div>
      </div>
    ),
  },
  {
    id: 'basics',
    title: '公司基本信息',
    icon: '02',
    content: (
      <div className="grid grid-cols-2 gap-3 text-sm">
        {[
          { k: '股票代码', v: '600519.SH' },
          { k: '公司名称', v: '贵州茅台酒股份有限公司' },
          { k: '所属行业', v: '白酒 / 高端消费品' },
          { k: '主营产品', v: '茅台酒（飞天）、系列酒' },
          { k: '分析资料日期', v: '截至 2023 年报' },
          { k: '分析输出日期', v: '2024 年' },
        ].map(item => (
          <div key={item.k} className="flex justify-between border-b border-border/50 pb-2">
            <span className="text-muted-foreground text-xs">{item.k}</span>
            <span className="text-foreground font-medium text-xs">{item.v}</span>
          </div>
        ))}
      </div>
    ),
  },
  {
    id: 'cashflow',
    title: '现金流质量分析',
    icon: '03',
    badge: { label: '优秀', color: 'bg-success/15 text-success border-success/30' },
    content: (
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: '经营现金流', value: '692.50 亿元', trend: '同比 +19.1%', good: true },
            { label: '自由现金流', value: '~650 亿元', trend: 'FCF 充裕', good: true },
            { label: '净利润', value: '747.34 亿元', trend: '净利率 50.6%', good: true },
            { label: 'CF/净利润比', value: '92.7%', trend: '现金含量优秀', good: true },
          ].map(item => (
            <div key={item.label} className={`rounded-md border p-3 ${item.good ? 'border-success/30 bg-success/5' : 'border-warning/30 bg-warning/5'}`}>
              <div className="text-xs text-muted-foreground">{item.label}</div>
              <div className="text-base font-semibold text-foreground mt-1">{item.value}</div>
              <div className={`text-[11px] mt-0.5 ${item.good ? 'text-success' : 'text-warning'}`}>{item.trend}</div>
            </div>
          ))}
        </div>
        <div className="space-y-1.5">
          {([
            { text: '2023 年经营现金流 692.50 亿元，净利润 747.34 亿元，现金/利润比约 92.7%', tag: 'fact', source: '2023年报' },
            { text: '未出现净利润增长但经营现金流恶化的信号', tag: 'fact', source: '2023年报' },
            { text: '自由现金流（FCF）约 650 亿元，FCF 质量高', tag: 'ai', source: 'AI推理（基于年报数据）' },
            { text: '现金流健康是茅台价值投资逻辑的核心基础之一', tag: 'ai', source: 'AI推理' },
          ] as EvidenceItem[]).map((item, i) => <EvidenceLine key={i} item={item} />)}
        </div>
      </div>
    ),
  },
  {
    id: 'dividend',
    title: '分红质量与可持续性',
    icon: '04',
    badge: { label: '可持续', color: 'bg-success/15 text-success border-success/30' },
    content: (
      <div className="space-y-3">
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: '分红总额', value: '359.07 亿元', note: '2023 年度' },
            { label: '分红率', value: '48%', note: '近三年稳定' },
            { label: 'FCF 覆盖率', value: '181%', note: '650/359，充分覆盖' },
          ].map(item => (
            <div key={item.label} className="rounded-md border border-success/30 bg-success/5 p-3">
              <div className="text-xs text-muted-foreground">{item.label}</div>
              <div className="text-lg font-semibold text-foreground mt-1">{item.value}</div>
              <div className="text-[11px] text-success mt-0.5">{item.note}</div>
            </div>
          ))}
        </div>
        <div className="space-y-1.5">
          {([
            { text: '2023 年分红总额 359.07 亿元，分红率约 48%', tag: 'fact', source: '2023年报' },
            { text: '自由现金流约 650 亿元，FCF 充分覆盖分红（FCF/分红 ≈ 1.81x）', tag: 'fact', source: '2023年报 + AI测算' },
            { text: '连续 20+ 年分红，分红政策稳定', tag: 'fact', source: '年报摘要' },
            { text: '分红不依赖一次性非经常性收益，由持续经营自由现金流支撑', tag: 'ai', source: 'AI推理' },
            { text: '当前分红可持续，高股息风险低——前提是主业现金流保持稳定', tag: 'assumption', source: 'AI推理（需持续验证）' },
          ] as EvidenceItem[]).map((item, i) => <EvidenceLine key={i} item={item} />)}
        </div>
      </div>
    ),
  },
  {
    id: 'balance',
    title: '资产负债表安全性',
    icon: '05',
    badge: { label: '安全', color: 'bg-success/15 text-success border-success/30' },
    content: (
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: '有息负债', value: '0 元', note: '零有息负债', good: true },
            { label: '资产负债率', value: '19.8%', note: '主要为合同负债（预收款）', good: true },
            { label: '期末现金', value: '381.37 亿元', note: '充裕的现金储备', good: true },
            { label: 'ROE', value: '36.5%', note: '非杠杆驱动，利润率驱动', good: true },
          ].map(item => (
            <div key={item.label} className={`rounded-md border p-3 ${item.good ? 'border-success/30 bg-success/5' : 'border-warning/30 bg-warning/5'}`}>
              <div className="text-xs text-muted-foreground">{item.label}</div>
              <div className="text-base font-semibold text-foreground mt-1">{item.value}</div>
              <div className="text-[11px] text-success mt-0.5">{item.note}</div>
            </div>
          ))}
        </div>
        <div className="space-y-1.5">
          {([
            { text: '有息负债为 0，不存在债务偿还压力', tag: 'fact', source: '2023年报' },
            { text: '资产负债率 19.8%，负债主要为合同负债（预收款），属经营性负债而非金融负债', tag: 'fact', source: '2023年报' },
            { text: 'ROE 36.5%，主要由净利率（50.6%）驱动，而非高杠杆，✓ 盈利质量高', tag: 'ai', source: 'AI推理（杜邦分析）' },
          ] as EvidenceItem[]).map((item, i) => <EvidenceLine key={i} item={item} />)}
        </div>
      </div>
    ),
  },
  {
    id: 'business',
    title: '商业模式稳定性与竞争优势',
    icon: '06',
    badge: { label: '稳固', color: 'bg-success/15 text-success border-success/30' },
    content: (
      <div className="space-y-3 text-sm">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-md bg-secondary/50 border border-border p-3 space-y-2">
            <div className="text-xs font-medium text-foreground">核心竞争优势</div>
            {['品牌壁垒（国宴历史文化）', '产能稀缺（地理标志保护）', '渠道定价控制力', '直销占比持续提升'].map(item => (
              <div key={item} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <div className="h-1 w-1 rounded-full bg-primary shrink-0" />
                {item}
              </div>
            ))}
          </div>
          <div className="rounded-md bg-secondary/50 border border-border p-3 space-y-2">
            <div className="text-xs font-medium text-foreground">商业模式特征</div>
            {['毛利率 91.97%（行业顶端）', '弱资本开支需求', '预收款模式（现金流领先利润）', '受周期影响相对有限'].map(item => (
              <div key={item} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <div className="h-1 w-1 rounded-full bg-primary shrink-0" />
                {item}
              </div>
            ))}
          </div>
        </div>
        <div className="space-y-1.5">
          {([
            { text: '2023 年毛利率 91.97%，净利率 50.6%，行业内最高水平', tag: 'fact', source: '2023年报' },
            { text: 'i茅台直销占比约 28%，同比提升约 5pct', tag: 'fact', source: '年报摘要' },
            { text: '商业模式简单且可理解，不依赖大额资本再投入', tag: 'ai', source: 'AI推理' },
            { text: '高端消费需求对商务宴请依赖度较高，政策变化存在一定敏感性', tag: 'opinion', source: '研报摘要（少数派观点）' },
          ] as EvidenceItem[]).map((item, i) => <EvidenceLine key={i} item={item} />)}
        </div>
      </div>
    ),
  },
  {
    id: 'management',
    title: '管理层资本配置',
    icon: '07',
    badge: { label: '理性', color: 'bg-success/15 text-success border-success/30' },
    content: (
      <div className="space-y-3 text-sm">
        <div className="space-y-1.5">
          {([
            { text: '管理层明确表示"有多少资源办多少事"，不追求速度', tag: 'opinion', source: '年报摘要（管理层表述）' },
            { text: '无大额并购，无盲目扩张，资本配置以分红为主', tag: 'fact', source: '年报摘要' },
            { text: '历史资本配置行为理性，与价值投资偏好一致', tag: 'ai', source: 'AI推理' },
            { text: '管理层是否回避核心问题（如渠道库存、终端动销）暂无法验证', tag: 'assumption', source: '待验证（管理层纪要缺失）' },
          ] as EvidenceItem[]).map((item, i) => <EvidenceLine key={i} item={item} />)}
        </div>
        <div className="rounded-md border border-warning/20 bg-warning/5 p-3 text-xs text-muted-foreground">
          <span className="text-warning font-medium">资料缺口：</span>
          近 12 个月管理层路演纪要和业绩会记录缺失，以上判断仅基于年报披露内容，存在信息不完整风险。
        </div>
      </div>
    ),
  },
  {
    id: 'sellside',
    title: '卖方共识与核心分歧',
    icon: '08',
    content: (
      <div className="space-y-3 text-sm">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-md border border-success/30 bg-success/5 p-3">
            <div className="text-xs font-semibold text-success mb-2">共识（主流看多）</div>
            <div className="space-y-1.5 text-xs text-muted-foreground">
              <div>• 品牌护城河深厚，产能稀缺</div>
              <div>• 直销占比提升提高利润率</div>
              <div>• 现金流优秀，股东回报稳定</div>
              <div>• 目标价区间：2000-2200 元</div>
            </div>
          </div>
          <div className="rounded-md border border-warning/30 bg-warning/5 p-3">
            <div className="text-xs font-semibold text-warning mb-2">分歧（少数谨慎）</div>
            <div className="space-y-1.5 text-xs text-muted-foreground">
              <div>• 宏观消费降级压制高端需求</div>
              <div>• i茅台动销数据透明度不足</div>
              <div>• 当前估值隐含较高增长预期</div>
              <div>• 商务宴请需求弹性被低估</div>
            </div>
          </div>
        </div>
        <div className="space-y-1.5">
          {([
            { text: '主流看多核心逻辑：直销提升 + 品牌护城河 + 稳定现金流', tag: 'opinion', source: '研报摘要（主流）' },
            { text: '少数谨慎：宏观消费降级可能压制出货节奏，i茅台动销真实性存疑', tag: 'opinion', source: '研报摘要（少数派）' },
            { text: '买方视角核心分歧：直销占比能否持续提升 vs 需求端宏观压力', tag: 'ai', source: 'AI推理（基于卖方观点汇总）' },
          ] as EvidenceItem[]).map((item, i) => <EvidenceLine key={i} item={item} />)}
        </div>
      </div>
    ),
  },
  {
    id: 'valuetrap',
    title: '价值陷阱与反证风险',
    icon: '09',
    badge: { label: '3项关注', color: 'bg-warning/15 text-warning border-warning/30' },
    content: (
      <div className="space-y-3 text-sm">
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: '高股息不可持续', status: '通过', pass: true },
            { label: '低估值价值陷阱', status: '通过', pass: true },
            { label: '现金流恶化', status: '通过', pass: true },
            { label: '非经常性损益', status: '通过', pass: true },
            { label: '宏观消费降级', status: '关注', pass: false },
            { label: '渠道库存透明度', status: '关注', pass: false },
            { label: '高估值压力', status: '关注', pass: false },
          ].map(item => (
            <div key={item.label} className={`rounded-md border p-2.5 text-center ${item.pass ? 'border-success/30 bg-success/5' : 'border-warning/30 bg-warning/5'}`}>
              <div className={`text-[11px] font-medium ${item.pass ? 'text-success' : 'text-warning'}`}>{item.status}</div>
              <div className="text-[10px] text-muted-foreground mt-1 leading-tight">{item.label}</div>
            </div>
          ))}
        </div>
        <div className="space-y-1.5">
          {([
            { text: '高股息检查：FCF（650亿）充分覆盖分红（359亿），高股息可持续 ✓', tag: 'fact', source: '2023年报' },
            { text: '当前估值偏高（非低估值），价值陷阱的低估值陷阱信号不适用', tag: 'ai', source: 'AI推理' },
            { text: '关注：若宏观消费持续承压，高端消费量价齐升假设面临压力', tag: 'assumption', source: '风险推理' },
            { text: '关注：i茅台动销数据无法独立验证，渠道真实库存水位不明', tag: 'assumption', source: '待验证' },
            { text: '一票否决变量：若经营现金流出现实质性恶化，当前判断需重新评估', tag: 'ai', source: 'AI推理' },
          ] as EvidenceItem[]).map((item, i) => <EvidenceLine key={i} item={item} />)}
        </div>
      </div>
    ),
  },
  {
    id: 'gaps',
    title: '待验证问题与资料缺口',
    icon: '10',
    content: (
      <div className="space-y-3 text-sm">
        <div className="space-y-2">
          {[
            { q: '近 12 个月 i茅台平台实际动销数量及趋势', priority: '高', type: '待补充' },
            { q: '经销商渠道当前库存水位及打款节奏', priority: '高', type: '待补充' },
            { q: '2024H1 高端白酒终端需求最新数据', priority: '中', type: '待补充' },
            { q: '管理层对宏观消费环境的最新表态（路演纪要）', priority: '中', type: '缺失' },
            { q: '系列酒直销渠道推进进展', priority: '低', type: '缺失' },
          ].map((item, i) => (
            <div key={i} className="flex items-start gap-3 rounded-md border border-border bg-secondary/30 p-3">
              <span className="text-xs font-mono text-muted-foreground shrink-0 mt-0.5">Q{i+1}</span>
              <span className="flex-1 text-xs text-foreground leading-relaxed">{item.q}</span>
              <Badge className={`text-[9px] shrink-0 ${
                item.priority === '高' ? 'bg-destructive/15 text-destructive border-destructive/30' :
                item.priority === '中' ? 'bg-warning/15 text-warning border-warning/30' :
                'bg-muted text-muted-foreground border-border'
              }`}>
                {item.priority}优先
              </Badge>
              <Badge variant="outline" className="text-[9px] shrink-0 border-border text-muted-foreground">{item.type}</Badge>
            </div>
          ))}
        </div>
      </div>
    ),
  },
  {
    id: 'view',
    title: '研究观点',
    icon: '11',
    badge: { label: '积极关注', color: 'bg-primary/15 text-primary border-primary/30' },
    content: (
      <div className="space-y-3">
        <div className="rounded-md border border-primary/30 bg-primary/5 p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs text-muted-foreground">研究观点标签</span>
            <Badge className="bg-primary/20 text-primary border-primary/40 text-xs">积极关注</Badge>
            <span className="text-[10px] text-muted-foreground">（内部研究观点，不构成投资建议）</span>
          </div>

          <p className="text-sm text-foreground leading-relaxed">
            基于当前资料，贵州茅台在现金流质量、分红可持续性和资产负债表安全性三个核心维度表现优秀，符合价值投资基础框架要求。商业模式稳定、竞争优势清晰。
            主要关注点在于：当前估值较高，安全边际依赖品牌持续溢价和需求稳定假设；宏观消费环境和渠道库存透明度是短期不确定性来源。
            管理层纪要缺失限制了完整评估，需补充验证。
          </p>
        </div>
        <div className="rounded-md border border-destructive/20 bg-destructive/5 p-3 text-xs text-muted-foreground leading-relaxed">
          <span className="text-destructive font-medium">合规声明：</span>
          本研究观点由 AI 基于用户提供的研究资料生成，属于研究训练输出，
          <strong className="text-foreground"> 不构成任何形式的投资建议、交易指令或收益承诺。</strong>
          所有判断均基于用户提供的有限资料，存在重大不确定性。投资决策需由专业人士独立作出。
        </div>
      </div>
    ),
  },
]

export function MemoPanel({ companyName = '—', stockCode = '—', industry = '—', memo, evidenceItems = [] }: MemoPanelProps) {
  const [activeSection, setActiveSection] = useState<string>('overview')
  const evidenceById = new Map(evidenceItems.map(item => [item.evidence_id, item]))

  const handleDownload = () => {
    const content = memo?.markdown || `# ${companyName}（${stockCode}）价值投资研究 Memo\n\n*本 Memo 由 Value Investing Research Coach 生成，不构成投资建议*\n\n---\n\n当前尚未生成正式 Memo。`
    const blob = new Blob([content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${stockCode}_研究Memo.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (memo) {
    return (
      <div className="mx-auto max-w-screen-2xl px-6 py-8">
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-3 space-y-3">
            <div className="rounded-lg border border-border bg-card p-4 space-y-1">
              <div className="mb-3">
                <div className="text-sm font-semibold text-foreground">{companyName}</div>
                <div className="text-xs text-muted-foreground font-mono">{stockCode} · {industry}</div>
              </div>

              <div className="grid grid-cols-2 gap-1.5 mb-3">
                <div className="rounded bg-secondary/50 border border-border/50 px-2 py-1.5">
                  <div className="text-[10px] text-muted-foreground">置信度</div>
                  <div className="text-[11px] font-semibold text-primary">{memo.confidence}</div>
                </div>
                <div className="rounded bg-secondary/50 border border-border/50 px-2 py-1.5">
                  <div className="text-[10px] text-muted-foreground">证据数</div>
                  <div className="text-[11px] font-semibold text-foreground">{evidenceItems.length || memo.source_ids.length}</div>
                </div>
              </div>

              <div className="space-y-0.5">
                {memo.sections.map((section, idx) => (
                  <button
                    key={section.section_id}
                    onClick={() => {
                      setActiveSection(section.section_id)
                      document.getElementById(`section-${section.section_id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                    }}
                    className={`w-full flex items-center gap-2 rounded px-2 py-1.5 text-left text-xs transition-all ${
                      activeSection === section.section_id
                        ? 'bg-accent text-foreground'
                        : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
                    }`}
                  >
                    <span className="font-mono text-[10px] text-muted-foreground shrink-0 w-5">{String(idx + 1).padStart(2, '0')}</span>
                    <span className="flex-1 truncate">{section.title}</span>
                  </button>
                ))}
              </div>

              <div className="pt-2 border-t border-border mt-2">
                <button
                  onClick={handleDownload}
                  className="w-full flex items-center justify-center gap-2 rounded-md border border-border bg-secondary/50 px-3 py-2 text-xs text-foreground hover:bg-secondary transition-all"
                >
                  下载 Markdown
                </button>
              </div>
            </div>
          </div>

          <div className="col-span-9 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-foreground">价值投资买方研究 Memo</h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  后端 Agent 生成 · 不构成投资建议 · Memo ID {memo.memo_id}
                </p>
              </div>
              <Badge className="bg-primary/15 text-primary border-primary/30 text-xs">{memo.confidence}</Badge>
            </div>

            <Accordion type="multiple" defaultValue={memo.sections.slice(0, 4).map(section => section.section_id)} className="space-y-3">
              {memo.sections.map((section, idx) => (
                <AccordionItem
                  key={section.section_id}
                  value={section.section_id}
                  id={`section-${section.section_id}`}
                  className="rounded-lg border border-border bg-card overflow-hidden data-[state=open]:border-primary/30"
                >
                  <AccordionTrigger className="px-4 py-3 hover:no-underline hover:bg-accent/30 transition-colors [&[data-state=open]]:bg-accent/20">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs text-muted-foreground shrink-0">{String(idx + 1).padStart(2, '0')}</span>
                      <span className="text-sm font-medium text-foreground">{section.title}</span>
                      <Badge variant="outline" className="text-[10px] h-5 border-border text-muted-foreground">{section.confidence}</Badge>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="px-4 pb-4 pt-1">
                    <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">{section.body}</div>
                    <EvidenceTraceList evidenceIds={section.evidence_ids} evidenceById={evidenceById} />
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-screen-2xl px-6 py-8">
      <div className="grid grid-cols-12 gap-6">
        {/* Left: Sidebar nav */}
        <div className="col-span-3 space-y-3">
          <div className="rounded-lg border border-border bg-card p-4 space-y-1">
            {/* Header */}
            <div className="mb-3">
              <div className="text-sm font-semibold text-foreground">{companyName}</div>
              <div className="text-xs text-muted-foreground font-mono">{stockCode} · {industry}</div>
            </div>

            {/* Summary metrics */}
            <div className="grid grid-cols-2 gap-1.5 mb-3">
              {[
                { label: '现金流', score: '优', color: 'text-success' },
                { label: '分红', score: '可持续', color: 'text-success' },
                { label: '资产负债表', score: '安全', color: 'text-success' },
                { label: '商业模式', score: '稳固', color: 'text-success' },
                { label: '估值保护', score: '偏高', color: 'text-warning' },
                { label: '价值陷阱', score: '3项关注', color: 'text-warning' },
              ].map(item => (
                <div key={item.label} className="rounded bg-secondary/50 border border-border/50 px-2 py-1.5">
                  <div className="text-[10px] text-muted-foreground">{item.label}</div>
                  <div className={`text-[11px] font-semibold ${item.color}`}>{item.score}</div>
                </div>
              ))}
            </div>

            {/* Nav links */}
            <div className="space-y-0.5">
              {memoSections.map(section => (
                <button
                  key={section.id}
                  onClick={() => {
                    setActiveSection(section.id)
                    document.getElementById(`section-${section.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                  }}
                  className={`w-full flex items-center gap-2 rounded px-2 py-1.5 text-left text-xs transition-all ${
                    activeSection === section.id
                      ? 'bg-accent text-foreground'
                      : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
                  }`}
                >
                  <span className="font-mono text-[10px] text-muted-foreground shrink-0 w-5">{section.icon}</span>
                  <span className="flex-1 truncate">{section.title}</span>
                  {section.badge && (
                    <span className={`text-[9px] px-1 rounded border ${section.badge.color} shrink-0`}>{section.badge.label}</span>
                  )}
                </button>
              ))}
            </div>

            <div className="pt-2 border-t border-border mt-2">
              <button
                onClick={handleDownload}
                className="w-full flex items-center justify-center gap-2 rounded-md border border-border bg-secondary/50 px-3 py-2 text-xs text-foreground hover:bg-secondary transition-all"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 16 16">
                  <path d="M8 2v8M5 7l3 3 3-3M3 13h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                下载 Markdown
              </button>
            </div>
          </div>

          {/* Evidence legend */}
          <div className="rounded-lg border border-border bg-card p-3 space-y-2">
            <div className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">内容标注说明</div>
            {Object.entries(tagConfig).map(([key, cfg]) => (
              <div key={key} className="flex items-center gap-2 text-[11px]">
                <span className={`inline-flex rounded px-1.5 py-0.5 text-[9px] font-medium border ${cfg.color}`}>{cfg.label}</span>
                <span className="text-muted-foreground">
                  {key === 'fact' ? '来自资料的可溯源事实' :
                   key === 'opinion' ? '管理层/卖方/市场观点' :
                   key === 'assumption' ? '对未来的待验证假设' :
                   'AI 基于事实的推理分析'}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Memo content */}
        <div className="col-span-9 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-foreground">价值投资买方研究 Memo</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                所有关键结论均标注来源类型 · 不构成投资建议 · 来源标注完整率 92%
              </p>
            </div>
            <Badge className="bg-muted text-muted-foreground border-border text-xs">研究待完善</Badge>
          </div>

          <Accordion type="multiple" defaultValue={['overview', 'cashflow', 'dividend', 'valuetrap', 'view']} className="space-y-3">
            {memoSections.map(section => (
              <AccordionItem
                key={section.id}
                value={section.id}
                id={`section-${section.id}`}
                className="rounded-lg border border-border bg-card overflow-hidden data-[state=open]:border-primary/30"
              >
                <AccordionTrigger className="px-4 py-3 hover:no-underline hover:bg-accent/30 transition-colors [&[data-state=open]]:bg-accent/20">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs text-muted-foreground shrink-0">{section.icon}</span>
                    <span className="text-sm font-medium text-foreground">{section.title}</span>
                    {section.badge && (
                      <Badge className={`text-[10px] h-5 ${section.badge.color}`}>{section.badge.label}</Badge>
                    )}
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 pt-1">
                  {section.content}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
    </div>
  )
}
