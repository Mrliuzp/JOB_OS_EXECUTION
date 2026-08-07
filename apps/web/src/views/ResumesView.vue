<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { api } from '../services/api'

type ArtifactType = 'html' | 'pdf'
type TagType = 'success' | 'warning' | 'danger' | 'info'

interface ResumeItem {
  id: string
  title: string
  version_type: string
  language: string
  validation_status: string
  rendered_text_path: string | null
  rendered_pdf_path: string | null
  created_at: string
}

interface RenderResult {
  html: string
  pdf: string
}

const resumes = ref<ResumeItem[]>([])
const loading = ref(false)
const renderingId = ref<string | null>(null)
const downloadingKey = ref<string | null>(null)

async function loadResumes() {
  loading.value = true
  try {
    resumes.value = (await api.get<ResumeItem[]>('/resumes')).data
  } catch {
    resumes.value = []
    ElMessage.error('简历列表加载失败，请确认 API 服务正在运行')
  } finally {
    loading.value = false
  }
}

async function renderResume(item: ResumeItem) {
  renderingId.value = item.id
  try {
    const result = (await api.post<RenderResult>(`/resumes/${item.id}/render`)).data
    item.rendered_text_path = result.html
    item.rendered_pdf_path = result.pdf
    ElMessage.success('简历文件已生成')
  } catch {
    ElMessage.error('简历渲染失败，请检查 API 日志和 Playwright 环境')
  } finally {
    renderingId.value = null
  }
}

async function downloadResume(item: ResumeItem, artifactType: ArtifactType) {
  const key = `${item.id}-${artifactType}`
  downloadingKey.value = key
  try {
    const response = await api.get<Blob>(`/resumes/${item.id}/download/${artifactType}`, {
      responseType: 'blob',
    })
    const objectUrl = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = `resume-${item.id}.${artifactType}`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(objectUrl)
  } catch {
    ElMessage.error('简历下载失败，请先重新生成文件')
  } finally {
    downloadingKey.value = null
  }
}

function validationTagType(status: string): TagType {
  if (status === 'valid') return 'success'
  if (status === 'invalid') return 'danger'
  if (status === 'pending') return 'warning'
  return 'info'
}

function validationLabel(status: string): string {
  const labels: Record<string, string> = {
    valid: '事实校验通过',
    invalid: '事实校验失败',
    pending: '等待校验',
  }
  return labels[status] ?? status
}

function versionLabel(versionType: string): string {
  return versionType === 'tailored' ? '职位定制' : versionType
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

onMounted(loadResumes)
</script>

<template>
  <section>
    <div class="page-header">
      <div>
        <h2>简历</h2>
        <p class="description">查看事实校验结果，生成并下载定制简历文件。</p>
      </div>
      <el-button :loading="loading" @click="loadResumes">刷新</el-button>
    </div>

    <el-table v-if="resumes.length > 0" v-loading="loading" :data="resumes">
      <el-table-column prop="title" label="简历标题" min-width="240" />
      <el-table-column label="版本" width="110">
        <template #default="scope">
          {{ versionLabel(scope.row.version_type) }}
        </template>
      </el-table-column>
      <el-table-column prop="language" label="语言" width="90" />
      <el-table-column label="事实校验" width="150">
        <template #default="scope">
          <el-tag :type="validationTagType(scope.row.validation_status)">
            {{ validationLabel(scope.row.validation_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="180">
        <template #default="scope">
          {{ formatTime(scope.row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="310" fixed="right">
        <template #default="scope">
          <el-button
            size="small"
            :loading="renderingId === scope.row.id"
            @click="renderResume(scope.row)"
          >
            {{ scope.row.rendered_pdf_path ? '重新生成' : '生成文件' }}
          </el-button>
          <el-button
            size="small"
            type="primary"
            :disabled="!scope.row.rendered_pdf_path"
            :loading="downloadingKey === `${scope.row.id}-pdf`"
            @click="downloadResume(scope.row, 'pdf')"
          >
            下载 PDF
          </el-button>
          <el-button
            size="small"
            :disabled="!scope.row.rendered_text_path"
            :loading="downloadingKey === `${scope.row.id}-html`"
            @click="downloadResume(scope.row, 'html')"
          >
            下载 HTML
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty
      v-else-if="!loading"
      description="暂无定制简历，请先在职位流程中生成简历"
    />
  </section>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
}

.description {
  margin: 6px 0 0;
  color: #6b7280;
}
</style>
