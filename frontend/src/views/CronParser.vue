<template>
  <div class="cron-page">
    <el-card>
      <template #header>
        <span>Cron表达式解析</span>
      </template>

      <el-form :model="form" label-width="120px">
        <el-form-item label="Cron表达式">
          <el-input v-model="form.cron" placeholder="输入Cron表达式，如：0 0 12 * * ?" @keyup.enter="parse">
            <template #append>
              <el-button @click="parse">解析</el-button>
            </template>
          </el-input>
          <div class="cron-hint">
            <p>格式：分 时 日 月 周</p>
            <p>示例：0 0 12 * * ? (每天12点执行)</p>
          </div>
        </el-form-item>
        <el-form-item label="显示次数">
          <el-input-number v-model="form.count" :min="1" :max="50" />
        </el-form-item>
      </el-form>

      <el-divider v-if="result" />

      <div v-if="result">
        <el-alert
          :type="result.valid ? 'success' : 'error'"
          :title="result.valid ? 'Cron表达式有效' : 'Cron表达式无效'"
          :description="result.error || result.description"
          :closable="false"
          style="margin-bottom: 20px"
        />

        <div v-if="result.valid">
          <h3>表达式字段：</h3>
          <el-descriptions :column="5" border style="margin-bottom: 20px">
            <el-descriptions-item label="分钟">{{ result.fields.minute }}</el-descriptions-item>
            <el-descriptions-item label="小时">{{ result.fields.hour }}</el-descriptions-item>
            <el-descriptions-item label="日期">{{ result.fields.day }}</el-descriptions-item>
            <el-descriptions-item label="月份">{{ result.fields.month }}</el-descriptions-item>
            <el-descriptions-item label="星期">{{ result.fields.weekday }}</el-descriptions-item>
          </el-descriptions>

          <h3>未来执行时间：</h3>
          <el-table :data="result.next_times" border style="width: 100%">
            <el-table-column prop="time" label="执行时间" width="200" />
            <el-table-column prop="timestamp" label="时间戳" width="150" />
            <el-table-column prop="weekday" label="星期（英文）" width="150" />
            <el-table-column prop="weekday_cn" label="星期（中文）" />
          </el-table>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const form = ref({
  cron: '',
  count: 10
})

const result = ref(null)

const parse = async () => {
  if (!form.value.cron) {
    ElMessage.warning('请输入Cron表达式')
    return
  }

  try {
    const response = await api.post('/cron/parse', {
      cron: form.value.cron,
      count: form.value.count
    })
    
    if (response.success) {
      result.value = response.data
      if (response.data.valid) {
        ElMessage.success('解析成功')
      } else {
        ElMessage.error('Cron表达式无效')
      }
    } else {
      ElMessage.error(response.error || '解析失败')
    }
  } catch (error) {
    ElMessage.error('解析失败：' + (error.response?.data?.error || error.message))
  }
}
</script>

<style scoped>
.cron-page {
  max-width: 1400px;
  margin: 0 auto;
}

.cron-hint {
  margin-top: 5px;
  font-size: 12px;
  color: #666;
}

.cron-hint p {
  margin: 2px 0;
}

.result {
  margin-top: 20px;
}

.result h3 {
  margin-bottom: 15px;
  color: #333;
}
</style>