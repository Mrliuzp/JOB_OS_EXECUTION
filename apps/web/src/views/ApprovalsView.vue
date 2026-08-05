<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, fetchApprovals, type ApprovalItem } from '../services/api'

const items = ref<ApprovalItem[]>([])
const loadingId = ref('')

async function load(): Promise<void> {
  try {
    items.value = await fetchApprovals()
  } catch {
    items.value = []
  }
}

async function resolve(item: ApprovalItem, approved: boolean): Promise<void> {
  loadingId.value = item.id
  try {
    await api.post(`/approvals/${item.id}/${approved ? 'approve' : 'reject'}`)
    await load()
  } finally {
    loadingId.value = ''
  }
}

onMounted(load)
</script>

<template>
  <section>
    <h2>人工审批</h2>
    <el-alert
      title="薪资、Offer、合同、身份信息和高风险动作始终需要人工确认"
      type="info"
      :closable="false"
    />
    <el-table :data="items">
      <el-table-column prop="approval_type" label="类型" />
      <el-table-column prop="reason" label="原因" />
      <el-table-column prop="entity_type" label="对象" />
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button
            size="small"
            type="primary"
            :loading="loadingId === scope.row.id"
            @click="resolve(scope.row, true)"
          >批准</el-button>
          <el-button
            size="small"
            type="danger"
            :loading="loadingId === scope.row.id"
            @click="resolve(scope.row, false)"
          >拒绝</el-button>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>
