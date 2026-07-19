'use client'

import { useEffect, useMemo, useState } from 'react'
import { Check, Sparkles, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { MemoPanel } from '@/components/memo-panel'
import { decideMemoSuggestion, fetchEvidenceGraph, fetchMemoVersions, requestMemoSuggestions, saveMemoVersion, type BackendMemo, type BackendMemoSection, type EvidenceGraphNode, type MemoVersion } from '@/lib/api'

export function MemoCoauthorPanel({ projectId, companyName, stockCode, industry, memo, evidenceItems = [] }: { projectId?: string | null; companyName?: string; stockCode?: string; industry?: string; memo?: BackendMemo | null; evidenceItems?: Parameters<typeof MemoPanel>[0]['evidenceItems'] }) {
  const [versions, setVersions] = useState<MemoVersion[]>([])
  const [sections, setSections] = useState<BackendMemoSection[]>(memo?.sections || [])
  const [evidenceNodes, setEvidenceNodes] = useState<EvidenceGraphNode[]>([])
  const [selectedSection, setSelectedSection] = useState(0)
  const [summary, setSummary] = useState('完善研究观点与证据')
  const [requestFormal, setRequestFormal] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    if (!projectId) return
    const [history, graph] = await Promise.all([fetchMemoVersions(projectId), fetchEvidenceGraph(projectId)])
    setVersions(history)
    setEvidenceNodes(graph.nodes.filter(node => Boolean(node.evidence_id)))
    const latest = history.at(-1)
    if (latest) setSections(latest.sections)
  }

  useEffect(() => { load().catch(error => setError(error instanceof Error ? error.message : 'Memo加载失败')) }, [projectId])

  const latest = versions.at(-1)
  const current = sections[selectedSection]
  const changedSections = useMemo(() => {
    if (versions.length < 2) return []
    const previous = new Map(versions[versions.length - 2].sections.map(item => [item.section_id, item]))
    return versions[versions.length - 1].sections.filter(item => previous.get(item.section_id)?.body !== item.body).map(item => item.title)
  }, [versions])

  if (!projectId) return <MemoPanel companyName={companyName} stockCode={stockCode} industry={industry} memo={memo} evidenceItems={evidenceItems} />

  const save = async () => {
    setBusy(true); setError('')
    try {
      const saved = await saveMemoVersion(projectId, sections, summary, requestFormal)
      setVersions(current => [...current, saved]); setRequestFormal(false)
    } catch (error) { setError(error instanceof Error ? error.message : 'Memo保存失败') } finally { setBusy(false) }
  }

  const suggest = async () => {
    if (!latest) return
    setBusy(true); setError('')
    try { const updated = await requestMemoSuggestions(projectId, latest.memo_version_id); setVersions(current => current.map(item => item.memo_version_id === updated.memo_version_id ? updated : item)) }
    catch (error) { setError(error instanceof Error ? error.message : '建议生成失败') } finally { setBusy(false) }
  }

  const decide = async (suggestionId: string, status: 'accepted' | 'rejected') => {
    if (!latest) return
    const suggestion = latest.suggestions.find(item => item.suggestion_id === suggestionId)
    if (status === 'accepted' && suggestion) setSections(current => current.map(section => section.section_id === suggestion.section_id ? { ...section, body: suggestion.proposed_body, evidence_ids: suggestion.evidence_ids.length ? suggestion.evidence_ids : section.evidence_ids } : section))
    const updated = await decideMemoSuggestion(projectId, latest.memo_version_id, suggestionId, status)
    setVersions(current => current.map(item => item.memo_version_id === updated.memo_version_id ? updated : item))
  }

  return <div className="mx-auto max-w-screen-2xl px-6 py-8">
    <div className="mb-5 flex items-end justify-between"><div><div className="mb-1 text-xs font-medium uppercase tracking-wider text-primary">Co-writing Mode</div><h1 className="text-xl font-semibold text-foreground">共同完成研究 Memo</h1><p className="mt-1 text-sm text-muted-foreground">AI提出建议，用户决定观点；每次保存形成独立版本。</p></div><div className="flex gap-2"><Button variant="outline" onClick={suggest} disabled={busy || !latest}><Sparkles className="h-4 w-4" />AI修改建议</Button><Button onClick={save} disabled={busy || !sections.length}>{busy ? '处理中...' : `保存 v${versions.length + 1}`}</Button></div></div>
    {error && <div className="mb-4 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</div>}
    <div className="grid grid-cols-[220px_minmax(0,1fr)_320px] gap-5">
      <div className="space-y-2 border-r border-border pr-4"><div className="mb-2 text-xs font-medium text-muted-foreground">报告章节</div>{sections.map((section, index) => <button key={section.section_id} onClick={() => setSelectedSection(index)} className={`w-full rounded-md border px-3 py-2 text-left text-xs ${index === selectedSection ? 'border-primary/40 bg-primary/10 text-foreground' : 'border-border bg-card text-muted-foreground'}`}>{String(index + 1).padStart(2, '0')} · {section.title}</button>)}</div>
      <div>{current ? <><div className="mb-2 flex items-center justify-between"><div className="text-sm font-semibold text-foreground">{current.title}</div><Badge className="border-border bg-secondary text-muted-foreground">{current.confidence}</Badge></div><Textarea value={current.body} onChange={event => setSections(items => items.map((item, index) => index === selectedSection ? { ...item, body: event.target.value } : item))} className="min-h-[360px] bg-card text-sm leading-relaxed" /><div className="mt-4"><div className="mb-2 text-xs font-medium text-muted-foreground">本章节证据</div><div className="max-h-52 space-y-1 overflow-y-auto rounded-md border border-border bg-card p-2">{evidenceNodes.map(node => { const id = node.evidence_id as string; const checked = current.evidence_ids.includes(id); return <label key={node.node_id} className="flex cursor-pointer items-start gap-2 rounded px-2 py-1.5 hover:bg-accent/30"><input type="checkbox" checked={checked} onChange={() => setSections(items => items.map((item, index) => index === selectedSection ? { ...item, evidence_ids: checked ? item.evidence_ids.filter(value => value !== id) : [...item.evidence_ids, id] } : item))} className="mt-0.5 accent-[var(--primary)]" /><span className="line-clamp-2 text-xs text-foreground">{node.label}</span></label> })}</div></div><div className="mt-4 grid grid-cols-[1fr_auto] gap-3"><input value={summary} onChange={event => setSummary(event.target.value)} className="h-9 rounded-md border border-border bg-input px-3 text-xs text-foreground" placeholder="本次修改说明" /><label className="flex items-center gap-2 text-xs text-muted-foreground"><input type="checkbox" checked={requestFormal} onChange={event => setRequestFormal(event.target.checked)} />申请正式版本</label></div></> : <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">尚无 Memo 初稿</div>}</div>
      <div className="space-y-4"><div className="rounded-lg border border-border bg-card p-4"><div className="mb-3 flex items-center justify-between"><div className="text-sm font-semibold text-foreground">版本历史</div><span className="font-mono text-xs text-muted-foreground">{versions.length}</span></div>{[...versions].reverse().map(version => <button key={version.memo_version_id} onClick={() => { setSections(version.sections); setSelectedSection(0) }} className="mb-2 w-full rounded-md border border-border bg-secondary/20 p-3 text-left"><div className="flex items-center justify-between"><span className="text-xs font-medium text-foreground">v{version.version} · {version.created_by}</span><Badge className={version.gate_status === 'formal' ? 'border-success/30 bg-success/10 text-success' : 'border-warning/30 bg-warning/10 text-warning'}>{version.gate_status}</Badge></div><div className="mt-1 text-[10px] text-muted-foreground">{version.change_summary || '未填写修改说明'}</div>{version.gate_issues.slice(0, 2).map(issue => <div key={issue} className="mt-1 text-[10px] text-warning">· {issue}</div>)}</button>)}{!!changedSections.length && <div className="mt-2 text-[10px] text-muted-foreground">最近变更：{changedSections.join('、')}</div>}</div>{latest?.suggestions.some(item => item.status === 'pending') && <div className="rounded-lg border border-border bg-card p-4"><div className="mb-3 text-sm font-semibold text-foreground">待处理建议</div>{latest.suggestions.filter(item => item.status === 'pending').map(item => <div key={item.suggestion_id} className="mb-3 rounded-md border border-border bg-secondary/20 p-3"><div className="text-xs leading-relaxed text-foreground">{item.rationale}</div><div className="mt-2 flex gap-2"><button title="接受建议" onClick={() => decide(item.suggestion_id, 'accepted')} className="rounded border border-border p-1.5 text-success"><Check className="h-3.5 w-3.5" /></button><button title="拒绝建议" onClick={() => decide(item.suggestion_id, 'rejected')} className="rounded border border-border p-1.5 text-destructive"><X className="h-3.5 w-3.5" /></button></div></div>)}</div>}</div>
    </div>
  </div>
}
