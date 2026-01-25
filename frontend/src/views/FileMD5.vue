<template>
  <div class="md5-page">
    <el-card>
      <template #header>
        <span>文件MD5值计算</span>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="文件上传" name="file">
          <el-upload
            class="upload-demo"
            drag
            :auto-upload="false"
            :on-change="handleFileChange"
            :file-list="fileList"
            :limit="1"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或<em>点击上传</em>
            </div>
          </el-upload>

          <el-button
            type="primary"
            @click="calculateMD5"
            :disabled="!selectedFile"
            style="margin-top: 20px; width: 100%"
          >
            计算MD5
          </el-button>
        </el-tab-pane>

        <el-tab-pane label="文本内容" name="text">
          <el-form label-width="100px">
            <el-form-item label="文本内容">
              <el-input
                v-model="textContent"
                type="textarea"
                :rows="10"
                placeholder="输入要计算MD5的文本内容"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="calculateTextMD5" :disabled="!textContent">
                计算MD5
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <el-divider v-if="result" />

      <div v-if="result" class="result">
        <h3>计算结果：</h3>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="文件名" v-if="result.filename">{{ result.filename }}</el-descriptions-item>
          <el-descriptions-item label="MD5值">
            <el-input v-model="result.md5" readonly>
              <template #append>
                <el-button @click="copyMD5">复制</el-button>
              </template>
            </el-input>
          </el-descriptions-item>
          <el-descriptions-item label="文件大小">{{ formatSize(result.size) }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import api from '../api'

const activeTab = ref('file')
const fileList = ref([])
const selectedFile = ref(null)
const textContent = ref('')
const result = ref(null)

const handleFileChange = (file) => {
  selectedFile.value = file.raw
  fileList.value = [file]
}

const calculateMD5 = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请选择文件')
    return
  }

  const formData = new FormData()
  formData.append('file', selectedFile.value)

  try {
    const response = await api.post('/file/md5', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    
    if (response.success) {
      result.value = response.data
      ElMessage.success('MD5计算完成')
    } else {
      ElMessage.error(response.error || '计算失败')
    }
  } catch (error) {
    ElMessage.error('计算失败：' + (error.response?.data?.error || error.message))
  }
}

const calculateTextMD5 = async () => {
  if (!textContent.value) {
    ElMessage.warning('请输入文本内容')
    return
  }

  try {
    const response = await api.post('/file/md5', {
      content: textContent.value
    })
    
    if (response.success) {
      result.value = response.data
      ElMessage.success('MD5计算完成')
    } else {
      ElMessage.error(response.error || '计算失败')
    }
  } catch (error) {
    ElMessage.error('计算失败：' + (error.response?.data?.error || error.message))
  }
}

const copyMD5 = () => {
  if (result.value && result.value.md5) {
    navigator.clipboard.writeText(result.value.md5).then(() => {
      ElMessage.success('已复制到剪贴板')
    })
  }
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}
</script>

<style scoped>
.md5-page {
  max-width: 800px;
  margin: 0 auto;
}

.upload-demo {
  width: 100%;
}

.result {
  margin-top: 20px;
}

.result h3 {
  margin-bottom: 15px;
  color: #333;
}
</style>