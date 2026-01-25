<template>
  <div class="encode-page">
    <el-card>
      <template #header>
        <span>编码转换</span>
      </template>

      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="编码转换" name="convert">
          <el-form :model="convertForm" label-width="120px">
            <el-form-item label="原始文本">
              <el-input v-model="convertForm.text" type="textarea" :rows="5" />
            </el-form-item>
            <el-form-item label="源编码">
              <el-select v-model="convertForm.from_encoding" style="width: 100%">
                <el-option label="UTF-8" value="utf-8" />
                <el-option label="GBK" value="gbk" />
                <el-option label="GB2312" value="gb2312" />
                <el-option label="ASCII" value="ascii" />
                <el-option label="ISO-8859-1" value="iso-8859-1" />
              </el-select>
            </el-form-item>
            <el-form-item label="目标编码">
              <el-select v-model="convertForm.to_encoding" style="width: 100%">
                <el-option label="UTF-8" value="utf-8" />
                <el-option label="GBK" value="gbk" />
                <el-option label="GB2312" value="gb2312" />
                <el-option label="ASCII" value="ascii" />
                <el-option label="ISO-8859-1" value="iso-8859-1" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="doConvert">转换</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="Base64编码" name="base64_encode">
          <el-form label-width="120px">
            <el-form-item label="原始文本">
              <el-input v-model="base64EncodeText" type="textarea" :rows="5" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="doBase64Encode">编码</el-button>
            </el-form-item>
            <el-form-item label="编码结果" v-if="base64EncodeResult">
              <el-input v-model="base64EncodeResult" type="textarea" :rows="5" readonly />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="Base64解码" name="base64_decode">
          <el-form label-width="120px">
            <el-form-item label="Base64文本">
              <el-input v-model="base64DecodeText" type="textarea" :rows="5" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="doBase64Decode">解码</el-button>
            </el-form-item>
            <el-form-item label="解码结果" v-if="base64DecodeResult">
              <el-input v-model="base64DecodeResult" type="textarea" :rows="5" readonly />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="URL编码" name="url_encode">
          <el-form label-width="120px">
            <el-form-item label="原始文本">
              <el-input v-model="urlEncodeText" type="textarea" :rows="5" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="doUrlEncode">编码</el-button>
            </el-form-item>
            <el-form-item label="编码结果" v-if="urlEncodeResult">
              <el-input v-model="urlEncodeResult" type="textarea" :rows="5" readonly />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="URL解码" name="url_decode">
          <el-form label-width="120px">
            <el-form-item label="URL编码文本">
              <el-input v-model="urlDecodeText" type="textarea" :rows="5" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="doUrlDecode">解码</el-button>
            </el-form-item>
            <el-form-item label="解码结果" v-if="urlDecodeResult">
              <el-input v-model="urlDecodeResult" type="textarea" :rows="5" readonly />
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <el-divider v-if="convertResult" />

      <div v-if="convertResult" class="result">
        <h3>转换结果：</h3>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="原始文本">{{ convertResult.original }}</el-descriptions-item>
          <el-descriptions-item label="转换结果">{{ convertResult.converted || convertResult.encoded || convertResult.decoded }}</el-descriptions-item>
          <el-descriptions-item label="十六进制" v-if="convertResult.hex">{{ convertResult.hex }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const activeTab = ref('convert')

const convertForm = ref({
  text: '',
  from_encoding: 'utf-8',
  to_encoding: 'utf-8'
})

const base64EncodeText = ref('')
const base64EncodeResult = ref('')
const base64DecodeText = ref('')
const base64DecodeResult = ref('')
const urlEncodeText = ref('')
const urlEncodeResult = ref('')
const urlDecodeText = ref('')
const urlDecodeResult = ref('')

const convertResult = ref(null)

const handleTabChange = () => {
  convertResult.value = null
}

const doConvert = async () => {
  if (!convertForm.value.text) {
    ElMessage.warning('请输入原始文本')
    return
  }

  try {
    const response = await api.post('/encode/convert', {
      text: convertForm.value.text,
      from_encoding: convertForm.value.from_encoding,
      to_encoding: convertForm.value.to_encoding,
      operation: 'convert'
    })
    
    if (response.success) {
      convertResult.value = response.data
    } else {
      ElMessage.error(response.error || '转换失败')
    }
  } catch (error) {
    ElMessage.error('转换失败：' + (error.response?.data?.error || error.message))
  }
}

const doBase64Encode = async () => {
  if (!base64EncodeText.value) {
    ElMessage.warning('请输入原始文本')
    return
  }

  try {
    const response = await api.post('/encode/convert', {
      text: base64EncodeText.value,
      operation: 'base64_encode'
    })
    
    if (response.success) {
      base64EncodeResult.value = response.data.encoded
    } else {
      ElMessage.error(response.error || '编码失败')
    }
  } catch (error) {
    ElMessage.error('编码失败：' + (error.response?.data?.error || error.message))
  }
}

const doBase64Decode = async () => {
  if (!base64DecodeText.value) {
    ElMessage.warning('请输入Base64文本')
    return
  }

  try {
    const response = await api.post('/encode/convert', {
      text: base64DecodeText.value,
      operation: 'base64_decode'
    })
    
    if (response.success) {
      base64DecodeResult.value = response.data.decoded
    } else {
      ElMessage.error(response.error || '解码失败')
    }
  } catch (error) {
    ElMessage.error('解码失败：' + (error.response?.data?.error || error.message))
  }
}

const doUrlEncode = async () => {
  if (!urlEncodeText.value) {
    ElMessage.warning('请输入原始文本')
    return
  }

  try {
    const response = await api.post('/encode/convert', {
      text: urlEncodeText.value,
      operation: 'url_encode'
    })
    
    if (response.success) {
      urlEncodeResult.value = response.data.encoded
    } else {
      ElMessage.error(response.error || '编码失败')
    }
  } catch (error) {
    ElMessage.error('编码失败：' + (error.response?.data?.error || error.message))
  }
}

const doUrlDecode = async () => {
  if (!urlDecodeText.value) {
    ElMessage.warning('请输入URL编码文本')
    return
  }

  try {
    const response = await api.post('/encode/convert', {
      text: urlDecodeText.value,
      operation: 'url_decode'
    })
    
    if (response.success) {
      urlDecodeResult.value = response.data.decoded
    } else {
      ElMessage.error(response.error || '解码失败')
    }
  } catch (error) {
    ElMessage.error('解码失败：' + (error.response?.data?.error || error.message))
  }
}
</script>

<style scoped>
.encode-page {
  max-width: 1000px;
  margin: 0 auto;
}

.result {
  margin-top: 20px;
}

.result h3 {
  margin-bottom: 15px;
  color: #333;
}
</style>