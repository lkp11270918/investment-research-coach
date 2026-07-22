'use client'

import { useEffect, useState } from 'react'
import { Calculator, Check } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { updateValuationAssumptions, type ResearchQuality, type ValuationAssumptions } from '@/lib/api'

const defaults: ValuationAssumptions = { method: 'auto', cash_flow_type: 'auto', forecast_years: 5, bear_growth: -.05, base_growth: .03, bull_growth: .08, wacc: .10, cost_of_equity: .11, terminal_growth: .02, margin_of_safety_required: .25, confirmed: false }
const scenarioLabels: Record<string, string> = { bear: '悲观', base: '基准', bull: '乐观' }

export function ValuationPanel({ projectId, quality, onUpdated }: { projectId: string; quality: ResearchQuality; onUpdated: (next: ResearchQuality) => void }) {
  const [form, setForm] = useState<ValuationAssumptions>(quality.valuation_assumptions || defaults)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => setForm(quality.valuation_assumptions || defaults), [quality.valuation_assumptions])

  const save = async (confirmed: boolean) => {
    setBusy(true); setError(null)
    try {
      const nextForm = { ...form, confirmed }
      const valuation = await updateValuationAssumptions(projectId, nextForm)
      setForm(nextForm)
      onUpdated({ ...quality, valuation_analysis: valuation, valuation_assumptions: nextForm })
    } catch (e) { setError(e instanceof Error ? e.message : '估值假设保存失败') } finally { setBusy(false) }
  }
  const valuation = quality.valuation_analysis
  return <div className="mb-4 rounded-lg border border-border bg-card p-5">
    <div className="mb-4 flex items-start justify-between"><div><div className="flex items-center gap-2 text-sm font-semibold text-foreground"><Calculator className="h-4 w-4 text-primary" />估值与安全边际</div><div className="mt-1 text-xs text-muted-foreground">{valuation.method_reason || '系统将根据行业和现金流口径选择方法'}</div></div><Badge className={valuation.formal_conclusion_allowed ? 'border-success/30 bg-success/10 text-success' : 'border-warning/30 bg-warning/10 text-warning'}>{valuation.formal_conclusion_allowed ? '正式结论可用' : '训练草案'}</Badge></div>
    {error && <div className="mb-3 text-xs text-destructive">{error}</div>}
    <div className="grid grid-cols-4 gap-3"><MethodSelect value={form.method} onChange={value => setForm({ ...form, method: value })} /><PercentField label="WACC" value={form.wacc} onChange={value => setForm({ ...form, wacc: value })} /><PercentField label="股权成本" value={form.cost_of_equity} onChange={value => setForm({ ...form, cost_of_equity: value })} /><PercentField label="永续增长率" value={form.terminal_growth} onChange={value => setForm({ ...form, terminal_growth: value })} /><PercentField label="悲观增长" value={form.bear_growth} onChange={value => setForm({ ...form, bear_growth: value })} /><PercentField label="基准增长" value={form.base_growth} onChange={value => setForm({ ...form, base_growth: value })} /><PercentField label="乐观增长" value={form.bull_growth} onChange={value => setForm({ ...form, bull_growth: value })} /><PercentField label="最低安全边际" value={form.margin_of_safety_required} onChange={value => setForm({ ...form, margin_of_safety_required: value })} /></div>
    <div className="mt-4 grid grid-cols-3 gap-3">{valuation.scenarios.map(item => <div key={item.name} className="rounded-md border border-border bg-secondary/20 p-3"><div className="flex items-center justify-between text-xs font-medium text-foreground"><span>{scenarioLabels[item.name] || item.name}</span>{item.meets_required_margin != null && <span className={item.meets_required_margin ? 'text-success' : 'text-warning'}>{item.meets_required_margin ? '达到门槛' : '未达门槛'}</span>}</div><div className="mt-2 font-mono text-lg text-primary">{item.estimated_value_per_share ?? '-'}</div><div className="text-[10px] text-muted-foreground">每股价值 · 安全边际 {item.margin_of_safety_percent ?? '-'}%</div></div>)}</div>
    <div className="mt-4 grid grid-cols-[1fr_auto] items-end gap-4"><div className="text-xs leading-relaxed text-muted-foreground"><div>{valuation.conclusion}</div>{valuation.reverse_assumptions.map(item => <div key={item}>{item}</div>)}{valuation.missing_inputs.map(item => <span key={item} className="mr-2 text-warning">缺少：{item}</span>)}{valuation.warnings.map(item => <div key={item} className="text-warning">{item}</div>)}</div><div className="flex gap-2"><Button variant="outline" onClick={() => save(false)} disabled={busy}>保存草案</Button><Button onClick={() => save(true)} disabled={busy || !valuation.scenarios.length}><Check className="h-4 w-4" />确认估值假设</Button></div></div>
  </div>
}

function PercentField({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) { return <label className="text-xs text-muted-foreground">{label}<div className="relative mt-1"><input type="number" step="0.1" value={Number((value * 100).toFixed(2))} onChange={e => onChange(Number(e.target.value) / 100)} className="h-9 w-full rounded-md border border-border bg-input px-3 pr-7 text-xs text-foreground" /><span className="absolute right-3 top-2 text-xs">%</span></div></label> }
function MethodSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) { return <label className="text-xs text-muted-foreground">估值方法<select value={value} onChange={e => onChange(e.target.value)} className="mt-1 h-9 w-full rounded-md border border-border bg-input px-3 text-xs text-foreground"><option value="auto">行业自动选择</option><option value="fcff">FCFF</option><option value="fcfe">FCFE</option><option value="ddm">股利折现</option><option value="relative">相对估值</option></select></label> }
