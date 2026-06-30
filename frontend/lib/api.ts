export type FrontendMaterial = {
  id: string
  type: string
  name: string
  status: 'ready' | 'missing'
  content?: string
  file?: File
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

export type AnalyzeResult = {
  run_id: string
  status: string
  state: {
    memo?: BackendMemo | null
    pre_memo_gate?: unknown
    post_memo_gate?: unknown
    agent_outputs: Record<string, unknown>
  }
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
}): Promise<AnalyzeResult> {
  const companyProfile = {
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
  const fileMaterials = input.materials.filter(material => material.status === 'ready' && material.file)

  const formData = new FormData()
  formData.append('company_profile', JSON.stringify(companyProfile))
  formData.append('text_materials', JSON.stringify(textMaterials))
  formData.append('options', JSON.stringify({ skip_post_gate: false, enable_parallel: true }))
  for (const material of fileMaterials) {
    formData.append('material_ids', material.id)
    formData.append('files', material.file as File)
  }

  const response = await fetch(`${API_BASE_URL}/api/analyze-files`, {
    method: 'POST',
    headers: getStoredToken() ? { Authorization: `Bearer ${getStoredToken()}` } : undefined,
    body: formData,
  })

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  return response.json()
}
