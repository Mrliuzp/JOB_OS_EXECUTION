<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchSummary, type DashboardSummary } from '../services/api'

const summary = ref<DashboardSummary | null>(null)
const error = ref('')

onMounted(async () => {
  try {
    summary.value = await fetchSummary()
  } catch {
    error.value = 'API 尚未启动，当前显示空状态。'
  }
})
</script>

<template>
  <section>
    <h2>求职总览</h2>
    <el-alert v-if="error" :title="error" type="warning" :closable="false" />
    <el-row v-if="summary" :gutter="16">
      <el-col v-for="item in [
        ['发现职位', summary.jobs],
        ['符合规则', summary.eligible_jobs],
        ['已提交', summary.submitted],
        ['面试', summary.interviews],
        ['Offer', summary.offers],
        ['HR 消息', summary.inbound_messages],
      ]" :key="item[0]" :span="8">
        <el-card class="metric"><strong>{{ item[1] }}</strong><span>{{ item[0] }}</span></el-card>
      </el-col>
    </el-row>
    <p v-if="summary" class="note">{{ summary.note }}</p>
  </section>
</template>
