<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../services/api'
const status = ref<Record<string, string>>({})
onMounted(async () => { try { status.value = (await api.get<Record<string, string>>('/system/health')).data } catch { status.value = { status: 'offline' } } })
</script>
<template><section><h2>系统状态</h2><el-descriptions border><el-descriptions-item v-for="(value, key) in status" :key="key" :label="key">{{ value }}</el-descriptions-item></el-descriptions></section></template>
