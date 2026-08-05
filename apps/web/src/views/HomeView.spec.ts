import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import HomeView from './HomeView.vue'

describe('HomeView', () => {
  it('renders the JobOS-CN product identity', () => {
    const wrapper = mount(HomeView)

    expect(wrapper.text()).toContain('JobOS-CN')
    expect(wrapper.text()).toContain('AI 求职操作系统')
  })
})
