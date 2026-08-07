import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import DashboardView from './DashboardView.vue'

vi.mock('../services/api', () => ({
  fetchSummary: async () => ({ jobs: 1, eligible_jobs: 1, applications: 0, submitted: 0, interviews: 0, offers: 0, inbound_messages: 0, reply_rate: 0, interview_rate: 0, offer_rate: 0, note: '仅表示相关性' }),
}))

describe('DashboardView', () => {
  it('显示求职总览标题', () => {
    const wrapper = mount(DashboardView, { global: { stubs: ['el-alert', 'el-row', 'el-col', 'el-card'] } })
    expect(wrapper.text()).toContain('求职总览')
  })
})
