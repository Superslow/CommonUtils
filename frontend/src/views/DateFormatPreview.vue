<template>
  <div class="date-format-page">
    <el-card>
      <template #header>
        <span>日期格式预览</span>
      </template>
      <p class="desc">用于校验「当前时间」类参数的 strftime 格式是否达到预期，与数据构造任务中「当前时间」使用同一规则。</p>
      <el-form label-width="100px">
        <el-form-item label="格式字符串">
          <el-input
            v-model="format"
            placeholder="如 %Y-%m-%d %H:%M:%S，留空为默认 yyyy-MM-dd HH:mm:ss"
            clearable
            @input="preview"
          />
        </el-form-item>
        <el-form-item label="当前时间渲染">
          <el-input :model-value="formatted" readonly>
            <template #append>
              <el-button type="primary" @click="preview">刷新</el-button>
            </template>
          </el-input>
        </el-form-item>
      </el-form>
      <el-alert v-if="error" type="error" :title="error" show-icon style="margin-top: 12px" />
      <div v-if="!error && formatDoc" class="format-doc">
        <p>常用占位：%Y 年(4位) %m 月 %d 日 %H 时(24) %M 分 %S 秒 %f 微秒（Python）。</p>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const format = ref('%Y-%m-%d %H:%M:%S')
const formatted = ref('')
const error = ref('')
const formatDoc = ref(true)

function preview() {
  error.value = ''
  const f = (format.value || '').trim() || '%Y-%m-%d %H:%M:%S'
  api.post('/date-format/preview', { format: f })
    .then(r => {
      if (r.success && r.data) {
        formatted.value = r.data.formatted
      } else {
        error.value = r.error || '请求失败'
      }
    })
    .catch(e => {
      error.value = e.response?.data?.error || e.message || '请求失败'
      formatted.value = ''
    })
}

onMounted(preview)
</script>

<style scoped>
.date-format-page {
  max-width: 640px;
  margin: 0 auto;
}

.desc {
  color: #606266;
  font-size: 14px;
  margin-bottom: 20px;
}

.format-doc {
  margin-top: 16px;
  font-size: 12px;
  color: #909399;
}
</style>
