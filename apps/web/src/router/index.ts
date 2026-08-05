import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', component: () => import('../views/DashboardView.vue') },
    { path: '/jobs', component: () => import('../views/JobsView.vue') },
    { path: '/resumes', component: () => import('../views/ResumesView.vue') },
    { path: '/applications', component: () => import('../views/ApplicationsView.vue') },
    { path: '/messages', component: () => import('../views/MessagesView.vue') },
    { path: '/approvals', component: () => import('../views/ApprovalsView.vue') },
    { path: '/providers', component: () => import('../views/ProvidersView.vue') },
    { path: '/analytics', component: () => import('../views/AnalyticsView.vue') },
    { path: '/system', component: () => import('../views/SystemView.vue') },
  ],
})

export default router
