<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '../stores/app'

const route = useRoute()
const store = useAppStore()

const menus = [
  ['/', '总览'],
  ['/jobs', '职位'],
  ['/resumes', '简历'],
  ['/applications', '申请'],
  ['/messages', '消息'],
  ['/approvals', '审批'],
  ['/providers', '平台'],
  ['/analytics', '分析'],
  ['/system', '系统'],
]

onMounted(() => store.connectWorkerStatus())
</script>

<template>
  <el-container class="layout">
    <el-aside width="220px" class="sidebar">
      <h1>JobOS-CN</h1>
      <p>AI 求职操作系统</p>
      <el-menu :default-active="route.path" router>
        <el-menu-item v-for="item in menus" :key="item[0]" :index="item[0]">
          {{ item[1] }}
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">Worker：{{ store.workerStatus }}</el-header>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
</template>
