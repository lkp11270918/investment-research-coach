export type FrontendMaterial = {
  id: string
  type: string
  name: string
  status: 'ready' | 'missing'
  content?: string
  file?: File
  files?: File[]
}

export type BackendMemoSection = {
  section_id: string
  title: string
  body: string
  evidence_ids: string[]
  confidence: 'high' | 'medium' | 'low'
}

export type BackendMemo = {
  memo_id: string
  confidence: 'high' | 'medium' | 'low'
  sections: BackendMemoSection[]
  source_ids: string[]
  disclaimer: string
  markdown?: string | null
}

export type BackendFinding = {
  title: string
  detail: string
  classification: string
  evidence_ids: string[]
  confidence: 'high' | 'medium' | 'low'
}

export type BackendAgentOutput = {
  agent_name: string
  status: 'pass' | 'partial' | 'fail'
  summary: string
  findings: BackendFinding[]
  evidence_ids: string[]
  missing_materials: string[]
  confidence: 'high' | 'medium' | 'low'
  warnings: string[]
}

export type BackendEvidenceItem = {
  evidence_id: string
  category: string
  statement: string
  metric_name?: string | null
  metric_value?: string | number | null
  period?: string | null
  unit?: string | null
  confidence: 'high' | 'medium' | 'low'
  verification_status: string
  source_refs?: Array<{
    source_id: string
    excerpt?: string | null
    page?: string | null
    paragraph_id?: string | null
    row_id?: string | null
    url?: string | null
  }>
}

export type AnalyzeResult = {
  run_id: string
  status: string
  project_id?: string | null
  state: {
    company_profile?: {
      ticker?: string | null
      company_name: string
      industry: string
    }
    memo?: BackendMemo | null
    pre_memo_gate?: unknown
    post_memo_gate?: unknown
    evidence_items?: BackendEvidenceItem[]
    workflow_status?: string
    agent_outputs: Record<string, BackendAgentOutput>
  }
}

export type CompanyProfile = {
  ticker?: string | null
  company_name: string
  industry: string
  market?: string | null
  research_language?: 'zh' | 'en'
  user_mode?: 'to_c' | 'to_b'
}

export type ResearchProjectSummary = {
  project_id: string
  company_profile: CompanyProfile
  research_objective?: string | null
  investment_horizon?: string | null
  initial_view?: string | null
  key_question?: string | null
  status: 'active' | 'archived'
  run_count: number
  created_at: string
  updated_at: string
}

export type ProjectMaterial = {
  material_id: string
  project_id: string
  run_id: string
  version: number
  title: string
  source_type: string
  modality: string
  file_name?: string | null
  period_covered?: string | null
  publisher?: string | null
  published_at?: string | null
  parse_warnings: string[]
  created_at: string
}

export type ResearchTask = {
  task_id: string
  title: string
  detail: string
  source_type: string
  source_id: string
  priority: number
  status: string
  evidence_ids: string[]
}

export type ResearchProjectDetail = { project: ResearchProjectSummary; timeline: ResearchRunSummary[]; materials: ProjectMaterial[] }

export type EvidenceGraphNode = {
  node_id: string
  node_type: string
  label: string
  evidence_id?: string | null
  source_id?: string | null
  confidence: 'high' | 'medium' | 'low'
  verification_status: 'verified' | 'partially_supported' | 'unsupported' | 'to_be_verified'
  metadata: Record<string, unknown>
}

export type EvidenceGraphEdge = {
  edge_id: string
  from_node_id: string
  to_node_id: string
  relation: 'from_source' | 'supports' | 'contradicts' | 'depends_on' | 'duplicates' | 'mentions' | 'questioned_by'
  rationale?: string | null
  confidence: 'high' | 'medium' | 'low'
}

export type EvidenceGraph = {
  nodes: EvidenceGraphNode[]
  edges: EvidenceGraphEdge[]
  conflicts: string[]
  updated_at: string
}

export type ResearchQuestion = {
  question_id: string
  category: string
  question: string
  priority: number
  status: 'unanswered' | 'partial' | 'answered' | 'conflicted'
  evidence_ids: string[]
  missing_materials: string[]
  rationale?: string | null
  required_evidence_types: string[]
}

export type ResearchMap = {
  project_id: string
  industry: string
  questions: ResearchQuestion[]
  next_questions: string[]
  completion_rate: number
  updated_at: string
}

export type ThesisDraft = {
  core_view: string
  core_variables: Array<{ name: string; rationale: string; evidence_ids: string[] }>
  supporting_evidence_ids: string[]
  counter_evidence_ids: string[]
  assumptions: string[]
  falsification_conditions: string[]
  unknowns: string[]
  scenarios: Array<{ name: string; assumptions: string[]; outcome: string; trigger_conditions: string[] }>
  user_internal_label?: string | null
}

export type ThesisVersion = {
  thesis_id: string
  project_id: string
  version: number
  draft: ThesisDraft
  assessment: {
    status: 'pass' | 'partial' | 'fail'
    issues: string[]
    evidence_coverage: number
    sell_side_repetition_risk: boolean
    confidence: 'high' | 'medium' | 'low'
    ai_suggestions: string[]
    relevant_support_ids: string[]
    relevant_counter_ids: string[]
  }
  created_at: string
}

export type DefenseTurn = {
  turn_id: string
  role: 'portfolio_manager' | 'investment_director' | 'industry_researcher' | 'financial_researcher' | 'risk_manager'
  question: string
  thesis_reference?: string | null
  evidence_ids: string[]
  answer?: string | null
  answer_evidence_ids: string[]
  score?: number | null
  feedback?: string | null
  passed?: boolean | null
  score_breakdown: Record<string, number>
}

export type DefenseSession = {
  session_id: string
  project_id: string
  thesis_id: string
  status: 'active' | 'completed'
  turns: DefenseTurn[]
  overall_score?: number | null
  improvement_tasks: string[]
  created_at: string
  updated_at: string
}

export type CapabilityProfile = {
  profile_id: string
  user_id: string
  dimensions: Array<{
    dimension: string
    score: number | null
    evidence: string[]
    repeated_errors: string[]
    sample_count: number
    confidence: 'high' | 'medium' | 'low'
    trend: 'improving' | 'declining' | 'stable' | 'insufficient_data'
    change?: number | null
  }>
  strengths: string[]
  priorities: string[]
  recommended_tasks: string[]
  sample_count: number
  created_at: string
}

export type ResearchRunSummary = {
  run_id: string
  run_type: 'analysis' | 'review' | string
  company_name: string
  ticker?: string | null
  industry?: string | null
  memo_confidence?: 'high' | 'medium' | 'low' | null
  material_count: number
  evidence_count: number
  created_at: string
}

export type ResearchRunDetail = {
  summary: ResearchRunSummary
  state: AnalyzeResult['state']
}

export type AuthUser = {
  user_id: string
  email: string
  name?: string | null
  created_at: string
}

export type AuthResult = {
  access_token: string
  token_type: 'bearer'
  user: AuthUser
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000'
const TOKEN_STORAGE_KEY = 'research_coach_access_token'

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function storeToken(token: string) {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token)
}

export function clearStoredToken() {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY)
}

async function parseError(response: Response): Promise<string> {
  const text = await response.text()
  try {
    const parsed = JSON.parse(text)
    return parsed.detail || text
  } catch {
    return text || `请求失败：${response.status}`
  }
}

export async function registerUser(input: {
  email: string
  password: string
  name?: string
}): Promise<AuthResult> {
  const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function loginUser(input: {
  email: string
  password: string
}): Promise<AuthResult> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function fetchCurrentUser(token: string): Promise<AuthUser> {
  const response = await fetch(`${API_BASE_URL}/api/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

const sourceTypeByMaterialId: Record<string, string> = {
  financial: 'financial_table',
  annual: 'annual_report_summary',
  management: 'management_note',
  sellside: 'sell_side_summary',
  news: 'news_summary',
  notes: 'user_note',
}

export async function analyzeCompany(input: {
  stockCode: string
  companyName: string
  industry: string
  materials: FrontendMaterial[]
  projectId?: string | null
  researchObjective?: string
  investmentHorizon?: string
  initialView?: string
  keyQuestion?: string
}): Promise<AnalyzeResult> {
  const companyProfile: CompanyProfile = {
    ticker: input.stockCode,
    company_name: input.companyName,
    industry: input.industry || '未指定行业',
    market: 'A股',
    research_language: 'zh',
    user_mode: 'to_c',
  }
  const textMaterials = input.materials
    .filter(material => material.status === 'ready' && material.content?.trim())
    .map(material => ({
      title: material.name || material.type,
      content: material.content || '',
      source_type: sourceTypeByMaterialId[material.id] || 'other',
      usage_rights_confirmed: true,
    }))
  const fileMaterials = input.materials.flatMap(material => {
    const files = material.files?.length ? material.files : material.file ? [material.file] : []
    return files.map(file => ({ materialId: material.id, file }))
  })

  const formData = new FormData()
  let projectId: string | null = input.projectId || null
  if (getStoredToken()) {
    if (!projectId) {
      const project = await createResearchProject({ company_profile: companyProfile, research_objective: input.researchObjective, investment_horizon: input.investmentHorizon, initial_view: input.initialView, key_question: input.keyQuestion })
      projectId = project.project_id
    }
    formData.append('project_id', projectId)
  }
  formData.append('company_profile', JSON.stringify(companyProfile))
  formData.append('text_materials', JSON.stringify(textMaterials))
  formData.append('options', JSON.stringify({ skip_post_gate: false, enable_parallel: true }))
  for (const material of fileMaterials) {
    formData.append('material_ids', material.materialId)
    formData.append('files', material.file)
  }

  const response = await fetch(`${API_BASE_URL}/api/analyze-files`, {
    method: 'POST',
    headers: getStoredToken() ? { Authorization: `Bearer ${getStoredToken()}` } : undefined,
    body: formData,
  })

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  const result: AnalyzeResult = await response.json()
  return { ...result, project_id: projectId }
}

export async function reviewMemo(input: {
  memoText: string
  companyName?: string
  industry?: string
}): Promise<AnalyzeResult> {
  const response = await fetch(`${API_BASE_URL}/api/review`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(getStoredToken() ? { Authorization: `Bearer ${getStoredToken()}` } : {}),
    },
    body: JSON.stringify({
      company_profile: {
        company_name: input.companyName || '未指定公司',
        industry: input.industry || '未指定行业',
        user_mode: 'to_c',
      },
      memo_text: input.memoText,
      materials: [
        {
          title: '用户提交的研究 Memo',
          content: input.memoText,
          source_type: 'user_note',
          usage_rights_confirmed: true,
        },
      ],
    }),
  })

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  return response.json()
}

export async function fetchResearchRuns(): Promise<ResearchRunSummary[]> {
  const token = getStoredToken()
  if (!token) throw new Error('请先登录后查看历史研究')
  const response = await fetch(`${API_BASE_URL}/api/runs`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function fetchResearchRun(runId: string): Promise<ResearchRunDetail> {
  const token = getStoredToken()
  if (!token) throw new Error('请先登录后查看历史研究')
  const response = await fetch(`${API_BASE_URL}/api/runs/${runId}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

function authHeaders(json = false): HeadersInit {
  const token = getStoredToken()
  if (!token) throw new Error('请先登录后使用研究工作台')
  return {
    Authorization: `Bearer ${token}`,
    ...(json ? { 'Content-Type': 'application/json' } : {}),
  }
}

export async function createResearchProject(input: {
  company_profile: CompanyProfile
  research_objective?: string
  investment_horizon?: string
  initial_view?: string
  key_question?: string
}): Promise<ResearchProjectSummary> {
  const response = await fetch(`${API_BASE_URL}/api/projects`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify(input),
  })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function fetchResearchProjects(): Promise<ResearchProjectSummary[]> {
  const response = await fetch(`${API_BASE_URL}/api/projects`, { headers: authHeaders() })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function fetchResearchProject(projectId: string): Promise<ResearchProjectDetail> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}`, { headers: authHeaders() })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function fetchResearchTasks(projectId: string): Promise<ResearchTask[]> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/tasks`, { headers: authHeaders() })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function fetchEvidenceGraph(projectId: string): Promise<EvidenceGraph> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/evidence-graph`, { headers: authHeaders() })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function reviewEvidenceNode(projectId: string, nodeId: string, verificationStatus: EvidenceGraphNode['verification_status']): Promise<EvidenceGraph> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/evidence-graph/nodes/${encodeURIComponent(nodeId)}`, {
    method: 'PATCH',
    headers: authHeaders(true),
    body: JSON.stringify({ verification_status: verificationStatus }),
  })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function fetchResearchMap(projectId: string): Promise<ResearchMap> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/research-map`, { headers: authHeaders() })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function fetchThesisHistory(projectId: string): Promise<ThesisVersion[]> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/thesis`, { headers: authHeaders() })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function saveThesis(projectId: string, draft: ThesisDraft): Promise<ThesisVersion> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/thesis`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify(draft),
  })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function fetchDefenseSessions(projectId: string): Promise<DefenseSession[]> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/defense`, { headers: authHeaders() })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function startDefense(projectId: string): Promise<DefenseSession> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/defense`, { method: 'POST', headers: authHeaders() })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function answerDefense(sessionId: string, answer: string, evidenceIds: string[]): Promise<DefenseSession> {
  const response = await fetch(`${API_BASE_URL}/api/defense/${sessionId}/answer`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({ answer, evidence_ids: evidenceIds }),
  })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function refreshCapabilityProfile(): Promise<CapabilityProfile> {
  const response = await fetch(`${API_BASE_URL}/api/capability-profile`, { method: 'POST', headers: authHeaders() })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function fetchCapabilityProfileHistory(): Promise<CapabilityProfile[]> {
  const response = await fetch(`${API_BASE_URL}/api/capability-profile/history`, { headers: authHeaders() })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}
