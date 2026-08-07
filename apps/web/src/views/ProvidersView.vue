<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../services/api'
interface ProviderItem { name: string; capabilities: Record<string, boolean> }
const items = ref<ProviderItem[]>([])
onMounted(async () => { try { items.value = (await api.get<ProviderItem[]>('/providers')).data } catch { items.value = [] } })
</script>
<template><section><h2>招聘平台</h2><el-alert title="登录必须在独立 Chrome Profile 中由你手动完成；系统不会保存密码或处理验证码" type="warning" :closable="false"/><el-table :data="items"><el-table-column prop="name" label="Provider"/><el-table-column label="能力"><template #default="scope">{{ Object.keys(scope.row.capabilities).filter((key) => scope.row.capabilities[key]).join('、') }}</template></el-table-column></el-table></section></template>
