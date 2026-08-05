<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../services/api'
interface ConversationItem { id: string; recruiter_name: string | null; recruiter_company: string | null; unread_count: number }
const items = ref<ConversationItem[]>([])
onMounted(async () => { try { items.value = (await api.get<ConversationItem[]>('/conversations')).data } catch { items.value = [] } })
</script>
<template><section><h2>HR 消息</h2><el-table :data="items"><el-table-column prop="recruiter_name" label="招聘者"/><el-table-column prop="recruiter_company" label="公司"/><el-table-column prop="unread_count" label="未读"/></el-table></section></template>
