<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../services/api'

interface JobItem { id: string; title: string; company_name: string; status: string; work_mode: string; employment_type: string }
const jobs = ref<JobItem[]>([])
onMounted(async () => {
  try { jobs.value = (await api.get<JobItem[]>('/jobs')).data } catch { jobs.value = [] }
})
</script>
<template><section><h2>职位</h2><el-table :data="jobs"><el-table-column prop="title" label="职位"/><el-table-column prop="company_name" label="公司"/><el-table-column prop="work_mode" label="方式"/><el-table-column prop="employment_type" label="类型"/><el-table-column prop="status" label="状态"/></el-table></section></template>
