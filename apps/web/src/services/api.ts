import axios from 'axios'

// API 默认只连接本机 JobOS 服务。
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1',
  timeout: 15000,
})

export interface DashboardSummary {
  jobs: number
  eligible_jobs: number
  applications: number
  submitted: number
  interviews: number
  offers: number
  inbound_messages: number
  reply_rate: number
  interview_rate: number
  offer_rate: number
  note: string
}

export interface ApprovalItem {
  id: string
  approval_type: string
  reason: string
  entity_type: string
  entity_id: string
  status: string
}

export async function fetchSummary(): Promise<DashboardSummary> {
  const response = await api.get<DashboardSummary>('/analytics/summary')
  return response.data
}

export async function fetchApprovals(): Promise<ApprovalItem[]> {
  const response = await api.get<ApprovalItem[]>('/approvals')
  return response.data
}
