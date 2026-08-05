<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../services/api'
interface ApplicationItem { id: string; job_id: string; status: string; autonomy_level: string }
const items = ref<ApplicationItem[]>([])
onMounted(async () => { try { items.value = (await api.get<ApplicationItem[]>('/applications')).data } catch { items.value = [] } })
</script>
<template><section><h2>申请</h2><el-table :data="items"><el-table-column prop="id" label="申请 ID"/><el-table-column prop="job_id" label="职位 ID"/><el-table-column prop="status" label="状态"/><el-table-column prop="autonomy_level" label="自动化等级"/></el-table></section></template>
