'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, Check, FileSearch, Plus, RefreshCw, ShieldCheck, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import {
  answerDefense,
  fetchDefenseSessions,
  fetchEvidenceGraph,
  fetchEvidenceGraphHistory,
  fetchResearchProject,
  fetchResearchMap,
  fetchResearchMapHistory,
  fetchResearchJudgment,
  fetchResearchQuality,
  fetchResearchProjects,
  fetchResearchTasks,
  fetchThesisHistory,
  reviewEvidenceNode,
  reviewEvidenceEdge,
  reviewMaterialBlock,
  updateResearchTask,
  saveThesis,
  startDefense,
  type DefenseSession,
  type EvidenceGraph,
  type EvidenceGraphNode,
  type EvidenceGraphEdge,
  type ResearchMap,
  type ResearchJudgment,
  type ResearchQuality,
  type ProjectMaterial,
  type ResearchProjectSummary,
  type ResearchTask,
  type ThesisDraft,
  type ThesisVersion,
} from '@/lib/api'

interface ResearchWorkspacePanelProps {
  isLoggedIn: boolean
  projectId: string | null
  companyName?: string
  onLogin: () => void
  section?: 'map' | 'evidence' | 'thesis' | 'defense'
  onNewResearch?: () => void
  onAddMaterials?: (projectId: string, company: { stockCode: string; companyName: string; industry: string }) => void
  onProjectChange?: (projectId: string) => void
}

const emptyDraft: ThesisDraft = {
  core_view: '',
  core_variables: [0, 1, 2].map(() => ({ name: '', rationale: '', evidence_ids: [] })),
  supporting_evidence_ids: [],
  counter_evidence_ids: [],
  assumptions: [],
  falsification_conditions: [],
  unknowns: [],
  scenarios: ['bull', 'base', 'bear'].map(name => ({ name, assumptions: [], outcome: '', trigger_conditions: [] })),
  user_internal_label: '观察',
}

const questionStatus = {
  unanswered: { label: '未回答', className: 'border-border bg-secondary text-muted-foreground' },
  partial: { label: '部分回答', className: 'border-warning/30 bg-warning/10 text-warning' },
  answered: { label: '已回答', className: 'border-success/30 bg-success/10 text-success' },
  conflicted: { label: '存在冲突', className: 'border-destructive/30 bg-destructive/10 text-destructive' },
} as const

const roleLabels = {
  portfolio_manager: '基金经理',
  investment_director: '投资总监',
  industry_researcher: '行业研究员',
  financial_researcher: '财务研究员',
  risk_manager: '风控负责人',
} as const

export function ResearchWorkspacePanel({ isLoggedIn, projectId, companyName, onLogin, section = 'map', onNewResearch, onAddMaterials, onProjectChange }: ResearchWorkspacePanelProps) {
  const [researchMap, setResearchMap] = useState<ResearchMap | null>(null)
  const [mapHistoryCount, setMapHistoryCount] = useState(0)
  const [graphHistoryCount, setGraphHistoryCount] = useState(0)
  const [judgment, setJudgment] = useState<ResearchJudgment | null>(null)
  const [quality, setQuality] = useState<ResearchQuality | null>(null)
  const [projects, setProjects] = useState<ResearchProjectSummary[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(projectId)
  const [graph, setGraph] = useState<EvidenceGraph | null>(null)
  const [theses, setTheses] = useState<ThesisVersion[]>([])
  const [defenses, setDefenses] = useState<DefenseSession[]>([])
  const [materials, setMaterials] = useState<ProjectMaterial[]>([])
  const [tasks, setTasks] = useState<ResearchTask[]>([])
  const [draft, setDraft] = useState<ThesisDraft>(emptyDraft)
  const [answer, setAnswer] = useState('')
  const [answerEvidenceIds, setAnswerEvidenceIds] = useState<string[]>([])
  const [taskEvidenceIds, setTaskEvidenceIds] = useState<Record<string, string[]>>({})
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isLoggedIn) return
    let cancelled = false
    fetchResearchProjects()
      .then(items => {
        if (cancelled) return
        setProjects(items)
        setSelectedProjectId(current => projectId || current || items[0]?.project_id || null)
      })
      .catch(error => !cancelled && setError(error instanceof Error ? error.message : '研究项目加载失败'))
    return () => { cancelled = true }
  }, [isLoggedIn, projectId])

  useEffect(() => {
    if (!isLoggedIn || !selectedProjectId) return
    let cancelled = false
    setLoading(true)
    setError(null)
    setResearchMap(null)
    setGraph(null)
    setTheses([])
    setDefenses([])
    setDraft(emptyDraft)
    Promise.all([
      fetchResearchMap(selectedProjectId),
      fetchEvidenceGraph(selectedProjectId),
      fetchThesisHistory(selectedProjectId),
      fetchDefenseSessions(selectedProjectId),
      fetchResearchProject(selectedProjectId),
      fetchResearchTasks(selectedProjectId),
      fetchResearchMapHistory(selectedProjectId),
      fetchEvidenceGraphHistory(selectedProjectId),
      fetchResearchJudgment(selectedProjectId),
      fetchResearchQuality(selectedProjectId),
    ])
      .then(([nextMap, nextGraph, nextTheses, nextDefenses, detail, nextTasks, mapHistory, graphHistory, nextJudgment, nextQuality]) => {
        if (cancelled) return
        setResearchMap(nextMap)
        setGraph(nextGraph)
        setTheses(nextTheses)
        setDefenses(nextDefenses)
        setMaterials(detail.materials)
        setTasks(nextTasks)
        setMapHistoryCount(mapHistory.length)
        setGraphHistoryCount(graphHistory.length)
        setJudgment(nextJudgment)
        setQuality(nextQuality)
        if (nextTheses.length) setDraft(nextTheses[nextTheses.length - 1].draft)
      })
      .catch(error => !cancelled && setError(error instanceof Error ? error.message : '研究工作台加载失败'))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [isLoggedIn, selectedProjectId])

  if (!isLoggedIn) {
    return <WorkspaceEmpty title="登录后使用研究工作台" description="研究地图、证据确认、Thesis版本和投委会答辩需要沉淀到你的研究项目。" action="登录" onAction={onLogin} />
  }
  if (!selectedProjectId) {
    return <WorkspaceEmpty title="还没有可用的研究项目" description="请先在资料输入页完成一次公司分析，系统会自动建立研究项目。" />
  }

  const activeProject = projects.find(project => project.project_id === selectedProjectId)
  const activeCompanyName = activeProject?.company_profile.company_name || companyName
  const evidenceNodes = graph?.nodes.filter(node => node.evidence_id) || []
  const activeDefense = [...defenses].reverse().find(session => session.status === 'active')
  const currentTurn = activeDefense?.turns[activeDefense.turns.length - 1]

  const handleReview = async (node: EvidenceGraphNode, status: EvidenceGraphNode['verification_status']) => {
    if (!selectedProjectId) return
    try {
      setGraph(await reviewEvidenceNode(selectedProjectId, node.node_id, status))
      setQuality(await fetchResearchQuality(selectedProjectId))
    } catch (error) {
      setError(error instanceof Error ? error.message : '证据状态更新失败')
    }
  }

  const handleRelationReview = async (edge: EvidenceGraphEdge, relation: EvidenceGraphEdge['relation']) => {
    if (!selectedProjectId) return
    try {
      setGraph(await reviewEvidenceEdge(selectedProjectId, edge.edge_id, relation))
      setQuality(await fetchResearchQuality(selectedProjectId))
    } catch (error) {
      setError(error instanceof Error ? error.message : '关系修正失败')
    }
  }

  const handleBlockReview = async (material: ProjectMaterial, blockId: string, confirmed: boolean) => {
    if (!selectedProjectId) return
    try {
      const updated = await reviewMaterialBlock(selectedProjectId, material.material_id, blockId, confirmed)
      setMaterials(current => current.map(item => item.material_id === updated.material_id ? updated : item))
      const [nextGraph, nextQuality] = await Promise.all([fetchEvidenceGraph(selectedProjectId), fetchResearchQuality(selectedProjectId)])
      setGraph(nextGraph)
      setQuality(nextQuality)
    } catch (error) {
      setError(error instanceof Error ? error.message : '多模态内容确认失败')
    }
  }

  const handleCompleteTask = async (task: ResearchTask) => {
    if (!selectedProjectId) return
    setSaving(true); setError('')
    try {
      const updated = await updateResearchTask(selectedProjectId, task.task_id, 'completed', taskEvidenceIds[task.task_id] || [])
      setTasks(current => current.map(item => item.task_id === updated.task_id ? updated : item))
      setResearchMap(await fetchResearchMap(selectedProjectId))
    } catch (error) { setError(error instanceof Error ? error.message : '任务完成失败') } finally { setSaving(false) }
  }

  const handleSaveThesis = async () => {
    if (!selectedProjectId) return
    setSaving(true)
    setError(null)
    try {
      const saved = await saveThesis(selectedProjectId, draft)
      setTheses(previous => [...previous, saved])
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Thesis保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleStartDefense = async () => {
    if (!selectedProjectId) return
    setSaving(true)
    setError(null)
    try {
      const session = await startDefense(selectedProjectId)
      setDefenses(previous => [...previous, session])
    } catch (error) {
      setError(error instanceof Error ? error.message : '答辩启动失败')
    } finally {
      setSaving(false)
    }
  }

  const handleAnswer = async () => {
    if (!activeDefense || !answer.trim()) return
    setSaving(true)
    setError(null)
    try {
      const session = await answerDefense(activeDefense.session_id, answer, answerEvidenceIds)
      setDefenses(previous => previous.map(item => item.session_id === session.session_id ? session : item))
      setAnswer('')
      setAnswerEvidenceIds([])
    } catch (error) {
      setError(error instanceof Error ? error.message : '回答提交失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-screen-xl px-6 py-8">
      <div className="mb-5 flex items-end justify-between gap-4">
        <div>
          <div className="mb-1 text-xs font-medium uppercase tracking-wider text-primary">Research Workspace</div>
          <h1 className="text-xl font-semibold text-foreground">{activeCompanyName || '公司'}研究工作台</h1>
          <p className="mt-1 text-sm text-muted-foreground">从研究问题、证据确认到投资逻辑和答辩的完整训练过程。</p>
        </div>
        <div className="flex items-center gap-2">
          {onNewResearch && <Button variant="outline" size="sm" onClick={onNewResearch}><Plus className="h-3.5 w-3.5" />新建研究</Button>}
          {onAddMaterials && activeProject && <Button variant="outline" size="sm" onClick={() => onAddMaterials(activeProject.project_id, { stockCode: activeProject.company_profile.ticker || '', companyName: activeProject.company_profile.company_name, industry: activeProject.company_profile.industry })}><FileSearch className="h-3.5 w-3.5" />补充材料</Button>}
          {projects.length > 1 && (
            <select
              value={selectedProjectId}
              onChange={event => { setSelectedProjectId(event.target.value); onProjectChange?.(event.target.value) }}
              className="h-8 rounded-md border border-border bg-secondary px-3 text-xs text-foreground outline-none focus:border-primary"
              aria-label="选择研究项目"
            >
              {projects.map(project => <option key={project.project_id} value={project.project_id}>{project.company_profile.company_name} · {project.run_count}次研究</option>)}
            </select>
          )}
          <Badge className="border-border bg-secondary text-muted-foreground font-mono">{selectedProjectId}</Badge>
        </div>
      </div>

      {error && <div className="mb-4 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</div>}
      {loading ? (
        <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">正在加载研究项目...</div>
      ) : (
        <Tabs value={section}>

          <TabsContent value="map">
            <div className="mb-4 rounded-lg border border-border bg-card p-5">
              <div className="mb-3 flex items-center justify-between">
                <div><div className="text-sm font-semibold text-foreground">研究完成度</div><div className="mt-1 text-[10px] text-muted-foreground">计划 v{researchMap?.version || 1} · {mapHistoryCount} 个历史版本 · {researchMap?.planner_model}</div></div>
                <span className="font-mono text-sm text-primary">{researchMap?.completion_rate || 0}%</span>
              </div>
              <Progress value={researchMap?.completion_rate || 0} />
              {!!researchMap?.next_questions.length && (
                <div className="mt-4 border-t border-border pt-4">
                  <div className="mb-2 text-xs font-medium text-muted-foreground">下一步优先研究</div>
                  {researchMap.next_questions.map(question => <div key={question} className="mt-1 text-sm text-foreground">· {question}</div>)}
                </div>
              )}
              {!!researchMap?.core_variables.length && <div className="mt-4 border-t border-border pt-4"><div className="mb-2 text-xs font-medium text-muted-foreground">公司核心变量</div><div className="flex flex-wrap gap-2">{researchMap.core_variables.map(item => <Badge key={item} className="border-primary/20 bg-primary/5 text-primary">{item}</Badge>)}</div></div>}
              {!!researchMap?.material_requests.length && <div className="mt-4 text-xs text-muted-foreground">资料缺口：{researchMap.material_requests.join('、')}</div>}
            </div>
            <div className="space-y-2">
              {researchMap?.questions.map(question => {
                const status = questionStatus[question.status]
                return (
                  <div key={question.question_id} className="rounded-lg border border-border bg-card p-4">
                    <div className="flex items-start gap-3">
                      <span className="mt-0.5 font-mono text-[10px] text-muted-foreground">{question.question_id}</span>
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium text-foreground">{question.question}</div>
                        <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                          <span>{question.evidence_ids.length} 条证据</span>
                          {question.missing_materials.map(item => <span key={item}>待补：{item}</span>)}
                        </div>
                      </div>
                      <Badge className={status.className}>{status.label}</Badge>
                    </div>
                  </div>
                )
              })}
            </div>
          </TabsContent>

          <TabsContent value="evidence">
            {quality && <div className="mb-4 grid grid-cols-3 gap-4"><div className="rounded-lg border border-border bg-card p-4"><div className="text-xs text-muted-foreground">证据图谱质量</div><div className="mt-1 font-mono text-xl text-primary">{quality.evidence_graph_quality.score ?? 0}</div><div className="mt-2 text-[10px] text-muted-foreground">可追溯 {quality.evidence_graph_quality.traceability_rate ?? 0}% · 已确认 {quality.evidence_graph_quality.verified_rate ?? 0}% · 关系覆盖 {quality.evidence_graph_quality.relation_coverage ?? 0}%</div>{quality.evidence_graph_quality.issues?.map(item=><div key={item} className="mt-1 text-[10px] text-warning">{item}</div>)}</div><div className="rounded-lg border border-border bg-card p-4"><div className="text-xs text-muted-foreground">估值与安全边际</div><div className="mt-2 text-xs text-foreground">{quality.valuation_analysis.conclusion || '资料不足'}</div><div className="mt-2 flex gap-2">{Object.entries(quality.valuation_analysis.multiples || {}).map(([key,value])=><Badge key={key} className="border-border bg-secondary text-muted-foreground">{key.toUpperCase()} {value}</Badge>)}</div>{quality.valuation_analysis.scenarios?.map(item=><div key={item.name} className="mt-1 text-[10px] text-muted-foreground">{item.name}：{item.estimated_value_per_share ?? '-'} · 安全边际 {item.margin_of_safety_percent ?? '-'}%</div>)}</div><div className="rounded-lg border border-border bg-card p-4"><div className="text-xs text-muted-foreground">财务异常</div><div className="mt-1 font-mono text-xl text-warning">{quality.financial_anomalies.length}</div>{quality.financial_anomalies.slice(0,4).map(item=><div key={item.anomaly_id} className="mt-2 text-[10px] text-muted-foreground"><span className="text-warning">{item.description}</span><div>{item.verification_question}</div></div>)}</div></div>}
            <div className="mb-5 rounded-lg border border-border bg-card p-4">
              <div className="mb-3 flex items-center justify-between"><div><div className="text-sm font-semibold text-foreground">项目资料库</div><div className="mt-1 text-[10px] text-muted-foreground">证据图谱 v{graph?.version || 1} · {graphHistoryCount} 个历史版本</div></div><span className="font-mono text-xs text-muted-foreground">{materials.length} 份</span></div>
              <div className="grid grid-cols-2 gap-2 xl:grid-cols-3">{materials.map(material => <div key={material.material_id} className="rounded-md border border-border bg-secondary/20 p-3"><div className="truncate text-xs font-medium text-foreground">{material.title}</div><div className="mt-1 flex gap-2 text-[10px] text-muted-foreground"><span>v{material.version}</span><span>{material.source_type}</span><span>{material.modality}</span></div>{material.period_covered && <div className="mt-1 text-[10px] text-muted-foreground">期间：{material.period_covered}</div>}{material.parse_warnings.map(item => <div key={item} className="mt-1 line-clamp-2 text-[10px] text-warning">{item}</div>)}{material.blocks.filter(block => block.requires_confirmation).slice(0, 3).map(block => <div key={block.block_id} className="mt-2 rounded border border-warning/30 bg-warning/5 p-2"><div className="line-clamp-2 text-[10px] text-foreground">{block.content}</div><div className="mt-1 text-[9px] text-muted-foreground">{block.speaker ? `${block.speaker} · ` : ''}{block.start_seconds != null ? `${block.start_seconds}s · ` : ''}{block.region ? `区域 ${Math.round((block.region.x || 0) * 100)}%,${Math.round((block.region.y || 0) * 100)}%` : block.extraction_method}</div><div className="mt-2 flex items-center justify-between"><span className="text-[9px] text-warning">待人工确认</span><div className="flex gap-1"><button title="确认内容" onClick={() => handleBlockReview(material, block.block_id, true)} className="rounded border border-border p-1 text-success"><Check className="h-3 w-3" /></button><button title="否定内容" onClick={() => handleBlockReview(material, block.block_id, false)} className="rounded border border-border p-1 text-destructive"><X className="h-3 w-3" /></button></div></div></div>)}</div>)}</div>
            </div>
            {judgment && (judgment.view_points.length > 0 || judgment.red_team_challenges.length > 0) && <div className="mb-4 grid grid-cols-2 gap-4"><div className="rounded-lg border border-border bg-card p-4"><div className="mb-3 flex items-center justify-between"><div className="text-sm font-semibold text-foreground">观点比较</div><span className="text-[10px] text-muted-foreground">{judgment.sell_side_source_count} 个卖方来源</span></div>{judgment.view_points.map(point => <div key={`${point.point_type}-${point.topic}`} className="mt-2 rounded-md border border-border bg-secondary/20 p-3"><Badge className="border-border bg-secondary text-muted-foreground">{point.point_type}</Badge><div className="mt-2 text-xs font-medium text-foreground">{point.topic}</div><div className="mt-1 text-xs text-muted-foreground">{point.detail}</div>{point.buyer_verification_question && <div className="mt-2 text-[10px] text-warning">买方验证：{point.buyer_verification_question}</div>}</div>)}</div><div className="rounded-lg border border-border bg-card p-4"><div className="mb-3 flex items-center justify-between"><div className="text-sm font-semibold text-foreground">Red Team</div><span className="text-[10px] text-destructive">{judgment.unresolved_critical_count} 个关键缺口</span></div>{judgment.red_team_challenges.map(item => <div key={item.challenge_id} className="mt-2 rounded-md border border-border bg-secondary/20 p-3"><div className="flex items-center justify-between"><span className="text-xs font-medium text-foreground">{item.title}</span><Badge className={item.severity === 'critical' ? 'border-destructive/30 bg-destructive/10 text-destructive' : 'border-warning/30 bg-warning/10 text-warning'}>{item.severity}</Badge></div><div className="mt-1 text-xs text-muted-foreground">{item.mechanism}</div><div className="mt-2 text-[10px] text-warning">推翻测试：{item.falsification_test}</div></div>)}</div></div>}
            {!!graph?.conflicts.length && (
              <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/5 p-4">
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-destructive"><AlertTriangle className="h-4 w-4" />来源冲突</div>
                {graph.conflicts.map(conflict => <div key={conflict} className="mt-1 text-xs text-muted-foreground">{conflict}</div>)}
              </div>
            )}
            {!!graph?.edges.length && (
              <div className="mb-4 rounded-lg border border-border bg-card p-4">
                <div className="mb-3 flex items-center justify-between"><div className="text-sm font-semibold text-foreground">证据关系</div><span className="font-mono text-xs text-muted-foreground">{graph.edges.length} 条</span></div>
                <div className="max-h-72 space-y-2 overflow-y-auto">
                  {graph.edges.filter(edge => ['supports', 'contradicts', 'depends_on', 'questioned_by', 'duplicates'].includes(edge.relation)).slice(0, 100).map(edge => (
                    <div key={edge.edge_id} className="grid grid-cols-[1fr_132px] items-center gap-3 rounded-md border border-border bg-secondary/20 p-3">
                      <div className="min-w-0"><div className="truncate text-xs text-foreground">{edge.from_node_id} → {edge.to_node_id}</div><div className="mt-1 line-clamp-2 text-[10px] text-muted-foreground">{edge.rationale || '暂无关系说明'} · {edge.relation_source}{edge.reviewed_by_user ? ' · 已人工确认' : ''}</div></div>
                      <select value={edge.relation} onChange={event => handleRelationReview(edge, event.target.value as EvidenceGraphEdge['relation'])} aria-label="修正证据关系" className="h-8 rounded-md border border-border bg-input px-2 text-xs text-foreground outline-none focus:border-primary">
                        <option value="supports">支持</option><option value="contradicts">反驳</option><option value="depends_on">依赖</option><option value="questioned_by">质疑</option><option value="duplicates">重复</option>
                      </select>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="space-y-2">
              {evidenceNodes.map(node => (
                <div key={node.node_id} className="rounded-lg border border-border bg-card p-4">
                  <div className="flex items-start gap-3">
                    <FileSearch className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                    <div className="min-w-0 flex-1">
                      <div className="mb-1 flex flex-wrap items-center gap-2">
                        <Badge className="border-border bg-secondary text-muted-foreground">{node.node_type}</Badge>
                        <span className="font-mono text-[10px] text-muted-foreground">{node.evidence_id}</span>
                      </div>
                      <div className="text-sm leading-relaxed text-foreground">{node.label}</div>
                      <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-muted-foreground">{Object.entries(node.metadata).filter(([key, value]) => key !== 'source_refs' && value != null && value !== '').slice(0, 5).map(([key, value]) => <span key={key}>{key}：{String(value)}</span>)}</div>
                      {Array.isArray(node.metadata.source_refs) && node.metadata.source_refs.map((ref, index) => { const source = ref as Record<string, unknown>; return <div key={index} className="mt-2 rounded border border-border/60 bg-secondary/20 px-2 py-1.5 text-[10px] text-muted-foreground"><span className="font-mono">{String(source.source_id || '')}</span>{source.page ? ` · 第${source.page}页` : ''}{source.sheet ? ` · ${source.sheet}` : ''}{source.row_id ? ` · 第${source.row_id}行` : ''}{source.excerpt ? <div className="mt-1 line-clamp-2 text-foreground">{String(source.excerpt)}</div> : null}</div> })}
                    </div>
                    <div className="flex shrink-0 items-center gap-1">
                      <button title="确认该证据" onClick={() => handleReview(node, 'verified')} className="rounded-md border border-border p-1.5 text-muted-foreground hover:border-success/40 hover:text-success"><Check className="h-3.5 w-3.5" /></button>
                      <button title="否定该证据" onClick={() => handleReview(node, 'unsupported')} className="rounded-md border border-border p-1.5 text-muted-foreground hover:border-destructive/40 hover:text-destructive"><X className="h-3.5 w-3.5" /></button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="thesis">
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_320px]">
              <div className="space-y-4 rounded-lg border border-border bg-card p-5">
                <Field label="核心观点"><Textarea value={draft.core_view} onChange={event => setDraft({ ...draft, core_view: event.target.value })} className="min-h-24 bg-secondary/30" placeholder="写下当前核心研究观点，不写买入或卖出建议" /></Field>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                  {draft.core_variables.map((variable, index) => (
                    <div key={`variable-${index}`} className="rounded-md border border-border bg-secondary/20 p-3">
                      <div className="mb-2 text-xs font-medium text-muted-foreground">核心变量 {index + 1}</div>
                      <input value={variable.name} onChange={event => setDraft({ ...draft, core_variables: draft.core_variables.map((item, itemIndex) => itemIndex === index ? { ...item, name: event.target.value } : item) })} className="mb-2 h-9 w-full rounded-md border border-border bg-input px-3 text-sm text-foreground outline-none focus:border-primary" placeholder="变量名称" />
                      <Textarea value={variable.rationale} onChange={event => setDraft({ ...draft, core_variables: draft.core_variables.map((item, itemIndex) => itemIndex === index ? { ...item, rationale: event.target.value } : item) })} className="min-h-20 bg-input text-xs" placeholder="为什么重要" />
                    </div>
                  ))}
                </div>
                <EvidencePicker title="最强支持证据" nodes={evidenceNodes} selected={draft.supporting_evidence_ids} onChange={ids => setDraft({ ...draft, supporting_evidence_ids: ids })} />
                <EvidencePicker title="最强反证" nodes={evidenceNodes} selected={draft.counter_evidence_ids} onChange={ids => setDraft({ ...draft, counter_evidence_ids: ids })} />
                <ListField label="关键假设" value={draft.assumptions} onChange={assumptions => setDraft({ ...draft, assumptions })} placeholder="每行一个结论成立的假设" />
                <ListField label="推翻条件" value={draft.falsification_conditions} onChange={falsification_conditions => setDraft({ ...draft, falsification_conditions })} placeholder="每行一个可观察的推翻条件" />
                <ListField label="当前未知" value={draft.unknowns} onChange={unknowns => setDraft({ ...draft, unknowns })} placeholder="每行一个仍然不知道的问题" />
                <div className="grid grid-cols-3 gap-3">{draft.scenarios.map((scenario, index) => <div key={scenario.name} className="rounded-md border border-border bg-secondary/20 p-3"><div className="mb-2 text-xs font-medium text-foreground">{{ bull: '乐观情景', base: '基准情景', bear: '悲观情景' }[scenario.name] || scenario.name}</div><Textarea value={scenario.assumptions.join('\n')} onChange={event => setDraft({ ...draft, scenarios: draft.scenarios.map((item, i) => i === index ? { ...item, assumptions: event.target.value.split('\n').filter(Boolean) } : item) })} className="mb-2 min-h-20 bg-input text-xs" placeholder="关键假设" /><Textarea value={scenario.outcome} onChange={event => setDraft({ ...draft, scenarios: draft.scenarios.map((item, i) => i === index ? { ...item, outcome: event.target.value } : item) })} className="mb-2 min-h-20 bg-input text-xs" placeholder="可能结果" /><Textarea value={scenario.trigger_conditions.join('\n')} onChange={event => setDraft({ ...draft, scenarios: draft.scenarios.map((item, i) => i === index ? { ...item, trigger_conditions: event.target.value.split('\n').filter(Boolean) } : item) })} className="min-h-20 bg-input text-xs" placeholder="可观察触发条件" /></div>)}</div>
                <Button onClick={handleSaveThesis} disabled={saving}>{saving ? '正在保存...' : `保存 Thesis v${theses.length + 1}`}</Button>
              </div>
              <div className="space-y-3">
                {[...theses].reverse().map(thesis => (
                  <div key={thesis.thesis_id} className="rounded-lg border border-border bg-card p-4">
                    <div className="mb-2 flex items-center justify-between"><span className="text-sm font-semibold text-foreground">版本 {thesis.version} · 图谱v{thesis.evidence_graph_version || '-'}</span><Badge className={thesis.assessment.status === 'pass' ? 'border-success/30 bg-success/10 text-success' : 'border-warning/30 bg-warning/10 text-warning'}>{thesis.assessment.evidence_coverage}%</Badge></div>
                    <p className="text-xs leading-relaxed text-muted-foreground">{thesis.draft.core_view}</p>
                    {!!thesis.assessment.issues.length && <div className="mt-3 border-t border-border pt-3">{thesis.assessment.issues.map(issue => <div key={issue} className="mt-1 text-xs text-warning">· {issue}</div>)}</div>}
                    {!!thesis.assessment.ai_suggestions.length && <div className="mt-3 border-t border-border pt-3">{thesis.assessment.ai_suggestions.map(item => <div key={item} className="mt-1 text-xs text-muted-foreground">建议：{item}</div>)}</div>}
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="defense">
            {!activeDefense && (
              <div className="rounded-lg border border-border bg-card p-6 text-center">
                <ShieldCheck className="mx-auto h-8 w-8 text-primary" />
                <div className="mt-3 text-sm font-semibold text-foreground">AI投委会答辩</div>
                <p className="mx-auto mt-1 max-w-lg text-xs leading-relaxed text-muted-foreground">基金经理、行业研究员、财务研究员和风控负责人将根据你的Thesis与证据逐轮追问。</p>
                <Button className="mt-4" onClick={handleStartDefense} disabled={saving || !theses.length}>{theses.length ? '开始答辩' : '请先保存 Thesis'}</Button>
              </div>
            )}
            {activeDefense && currentTurn && (
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_320px]">
                <div className="rounded-lg border border-border bg-card p-5">
                  <div className="mb-2 flex items-center gap-2"><Badge className="border-primary/30 bg-primary/10 text-primary">{roleLabels[currentTurn.role]}</Badge><span className="font-mono text-[10px] text-muted-foreground">{currentTurn.turn_id}</span></div>
                  <div className="text-base font-medium leading-relaxed text-foreground">{currentTurn.question}</div>
                  <Textarea value={answer} onChange={event => setAnswer(event.target.value)} className="mt-5 min-h-40 bg-secondary/30" placeholder="直接回答问题，并说明证据、假设、不确定性和推翻条件" />
                  <div className="mt-4"><EvidencePicker title="本次回答引用的证据" nodes={evidenceNodes} selected={answerEvidenceIds} onChange={setAnswerEvidenceIds} /></div>
                  <Button className="mt-4" onClick={handleAnswer} disabled={saving || !answer.trim()}>{saving ? '正在提交...' : '提交回答'}</Button>
                </div>
                <DefenseHistory session={activeDefense} />
              </div>
            )}
            {!activeDefense && defenses.filter(item => item.status === 'completed').map(session => <DefenseHistory key={session.session_id} session={session} />)}
            {!!tasks.length && <div className="mt-5 rounded-lg border border-border bg-card p-4"><div className="mb-3 flex items-center justify-between"><div className="text-sm font-semibold text-foreground">研究改进任务</div><span className="text-xs text-muted-foreground">{tasks.filter(task => task.status === 'open').length} 项待完成</span></div>{tasks.map(task => <div key={task.task_id} className="mt-2 rounded-md border border-border bg-secondary/20 p-3"><div className="flex items-center justify-between"><div className="text-xs font-medium text-foreground">{task.title}</div><Badge className={task.status === 'completed' ? 'border-success/30 bg-success/10 text-success' : 'border-warning/30 bg-warning/10 text-warning'}>{task.status === 'completed' ? '已完成' : '待完成'}</Badge></div><div className="mt-1 text-xs text-muted-foreground">{task.detail}</div>{task.status === 'open' && <div className="mt-3"><EvidencePicker title="完成任务所依据的已确认事实" nodes={evidenceNodes.filter(node => node.verification_status === 'verified')} selected={taskEvidenceIds[task.task_id] || []} onChange={ids => setTaskEvidenceIds(current => ({ ...current, [task.task_id]: ids }))} /><Button size="sm" className="mt-2" disabled={saving || !(taskEvidenceIds[task.task_id] || []).length} onClick={() => handleCompleteTask(task)}><Check className="h-3.5 w-3.5" />完成任务</Button></div>}{task.status === 'completed' && <div className="mt-2 text-[10px] text-muted-foreground">完成证据：{task.completion_evidence_ids.join('、')}</div>}</div>)}</div>}
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}

function WorkspaceEmpty({ title, description, action, onAction }: { title: string; description: string; action?: string; onAction?: () => void }) {
  return <div className="mx-auto max-w-screen-xl px-6 py-16"><div className="mx-auto max-w-md rounded-lg border border-border bg-card p-6 text-center"><div className="text-lg font-semibold text-foreground">{title}</div><p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>{action && onAction && <Button className="mt-5" onClick={onAction}>{action}</Button>}</div></div>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="mb-2 block text-xs font-medium text-muted-foreground">{label}</span>{children}</label>
}

function ListField({ label, value, onChange, placeholder }: { label: string; value: string[]; onChange: (value: string[]) => void; placeholder: string }) {
  return <Field label={label}><Textarea value={value.join('\n')} onChange={event => onChange(event.target.value.split('\n').map(item => item.trim()).filter(Boolean))} className="min-h-24 bg-secondary/30" placeholder={placeholder} /></Field>
}

function EvidencePicker({ title, nodes, selected, onChange }: { title: string; nodes: EvidenceGraphNode[]; selected: string[]; onChange: (ids: string[]) => void }) {
  return <div><div className="mb-2 text-xs font-medium text-muted-foreground">{title}</div><div className="max-h-44 space-y-1 overflow-y-auto rounded-md border border-border bg-secondary/20 p-2">{nodes.length ? nodes.map(node => { const id = node.evidence_id as string; const checked = selected.includes(id); return <label key={node.node_id} className="flex cursor-pointer items-start gap-2 rounded px-2 py-1.5 hover:bg-accent/30"><input type="checkbox" checked={checked} onChange={() => onChange(checked ? selected.filter(item => item !== id) : [...selected, id])} className="mt-0.5 accent-[var(--primary)]" /><span className="line-clamp-2 text-xs leading-relaxed text-foreground">{node.label}</span></label> }) : <div className="p-2 text-xs text-muted-foreground">暂无可选证据</div>}</div></div>
}

function DefenseHistory({ session }: { session: DefenseSession }) {
  return <div className="space-y-2"><div className="flex items-center justify-between"><div><div className="text-xs font-medium text-muted-foreground">答辩记录</div><div className="mt-1 text-[9px] text-muted-foreground">{session.question_model}{session.targeted_gaps.length ? ` · 针对${session.targeted_gaps.length}项历史短板` : ''}</div></div>{session.overall_score != null && <Badge className="border-primary/30 bg-primary/10 text-primary">{session.overall_score}分</Badge>}</div>{session.turns.filter(turn => turn.answer).map(turn => <div key={turn.turn_id} className="rounded-lg border border-border bg-card p-3"><div className="flex items-center justify-between"><span className="text-xs font-medium text-foreground">{roleLabels[turn.role]}</span>{turn.passed ? <Check className="h-3.5 w-3.5 text-success" /> : <RefreshCw className="h-3.5 w-3.5 text-warning" />}</div><div className="mt-2 line-clamp-3 text-xs leading-relaxed text-muted-foreground">{turn.answer}</div>{Object.keys(turn.score_breakdown).length > 0 && <div className="mt-2 flex flex-wrap gap-2 text-[9px] text-muted-foreground">{Object.entries(turn.score_breakdown).map(([key, value]) => <span key={key}>{key} {value}</span>)}</div>}{turn.feedback && <div className="mt-2 border-t border-border pt-2 text-xs text-warning">{turn.feedback}</div>}</div>)}</div>
}
