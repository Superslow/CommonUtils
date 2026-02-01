<template>
  <div class="timestamp-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>时间戳转换</span>
          <el-button type="primary" @click="getCurrentTime">获取当前时间</el-button>
        </div>
      </template>

      <el-form :model="form" label-width="120px">
        <el-form-item label="时间戳">
          <el-input v-model="form.timestamp" placeholder="输入时间戳（秒或毫秒）" @keyup.enter="convert">
            <template #append>
              <el-button @click="convert">转换</el-button>
            </template>
          </el-input>
        </el-form-item>
      </el-form>

      <el-divider />

      <div v-if="result" class="result">
        <h3>转换结果：</h3>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="时间戳（秒）">{{ result.timestamp }}</el-descriptions-item>
          <el-descriptions-item label="时间戳（毫秒）">{{ result.timestamp_ms }}</el-descriptions-item>
          <el-descriptions-item label="日期时间">{{ result.datetime }}</el-descriptions-item>
          <el-descriptions-item label="日期">{{ result.date }}</el-descriptions-item>
          <el-descriptions-item label="时间">{{ result.time }}</el-descriptions-item>
          <el-descriptions-item label="ISO格式">{{ result.iso }}</el-descriptions-item>
          <el-descriptions-item label="星期">{{ result.weekday_cn }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const form = ref({
  timestamp: ''
})

const result = ref(null)

const convert = async () => {
  if (!form.value.timestamp) {
    ElMessage.warning('请输入时间戳')
    return
  }

  try {
    const response = await api.post('/timestamp/convert', {
      timestamp: parseInt(form.value.timestamp)
    })
    
    if (response.success) {
      result.value = response.data
    } else {
      ElMessage.error(response.error || '转换失败')
    }
  } catch (error) {
    ElMessage.error('转换失败：' + (error.response?.data?.error || error.message))
  }
}

const getCurrentTime = async () => {
  try {
    const response = await api.get('/timestamp/current')
    if (response.success) {
      form.value.timestamp = response.data.timestamp.toString()
      result.value = response.data
    }
  } catch (error) {
    ElMessage.error('获取当前时间失败')
  }
}
</script>

<style scoped>
.timestamp-page {
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.result {
  margin-top: 20px;
}

.result h3 {
  margin-bottom: 15px;
  color: #333;
}
</style>