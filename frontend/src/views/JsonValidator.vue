<template>
  <div class="json-page">
    <el-card class="json-card">
      <template #header>
        <span>JSON格式化校验</span>
      </template>

      <el-form label-width="90px" class="json-form">
        <el-form-item label="JSON内容">
          <el-input
            v-model="jsonText"
            type="textarea"
            :rows="14"
            placeholder="输入JSON字符串"
            class="json-textarea"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="validate">校验并格式化</el-button>
          <el-button @click="clear">清空</el-button>
        </el-form-item>
      </el-form>

      <el-divider />

      <div v-if="result" class="result-section">
        <el-alert
          :type="result.valid ? 'success' : 'error'"
          :title="result.valid ? 'JSON格式正确' : 'JSON格式错误'"
          :description="result.error"
          :closable="false"
          class="result-alert"
        />

        <div v-if="result.valid" class="formatted-wrap">
          <h3 class="result-title">格式化结果：</h3>
          <el-input
            v-model="result.formatted"
            type="textarea"
            :rows="20"
            readonly
            class="json-textarea"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const jsonText = ref('')
const result = ref(null)

const validate = async () => {
  if (!jsonText.value.trim()) {
    ElMessage.warning('请输入JSON内容')
    return
  }

  try {
    const response = await api.post('/json/validate', {
      json: jsonText.value
    })
    
    if (response.success) {
      result.value = response.data
      if (response.data.valid) {
        ElMessage.success('JSON格式正确')
      } else {
        ElMessage.error('JSON格式错误')
      }
    }
  } catch (error) {
    ElMessage.error('校验失败：' + (error.response?.data?.error || error.message))
  }
}

const clear = () => {
  jsonText.value = ''
  result.value = null
}
</script>

<style scoped>
.json-page {
  max-width: 1600px;
  margin: 0 auto;
}

.json-card {
  padding: 0;
}

.json-card :deep(.el-card__body) {
  padding: 28px 56px 32px;
}

.json-form {
  margin-bottom: 8px;
}

.json-textarea :deep(.el-textarea__inner) {
  padding: 14px 18px;
  font-family: inherit;
}

.result-section {
  margin-top: 8px;
}

.result-alert {
  margin-bottom: 24px;
}

.result-title {
  margin-bottom: 14px;
  font-size: 15px;
  color: #303133;
}

.formatted-wrap .json-textarea {
  margin-top: 4px;
}
</style>