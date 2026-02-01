<template>
  <div class="ip-page">
    <el-card>
      <template #header>
        <span>IP网段判断</span>
      </template>

      <el-form :model="form" label-width="120px">
        <el-form-item label="IP地址">
          <el-input v-model="form.ip" placeholder="输入IP地址，如：192.168.1.1" @keyup.enter="check">
            <template #append>
              <el-button @click="check">检查</el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="网段（可选）">
          <el-input v-model="form.network" placeholder="输入CIDR格式网段，如：192.168.1.0/24" />
        </el-form-item>
      </el-form>

      <el-divider v-if="result" />

      <div v-if="result" class="result">
        <el-alert
          :type="result.valid ? 'success' : 'error'"
          :title="result.valid ? 'IP地址有效' : 'IP地址无效'"
          :description="result.error"
          :closable="false"
          style="margin-bottom: 20px"
          v-if="!result.valid"
        />

        <h3>IP信息：</h3>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="IP地址">{{ result.ip }}</el-descriptions-item>
          <el-descriptions-item label="版本">IPv{{ result.version }}</el-descriptions-item>
          <el-descriptions-item label="是否有效">
            <el-tag :type="result.valid ? 'success' : 'danger'">
              {{ result.valid ? '是' : '否' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="是否私有">
            <el-tag :type="result.is_private ? 'warning' : 'info'">
              {{ result.is_private ? '是' : '否' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="是否公网">
            <el-tag :type="result.is_public ? 'success' : 'info'">
              {{ result.is_public ? '是' : '否' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="是否组播">
            <el-tag :type="result.is_multicast ? 'warning' : 'info'">
              {{ result.is_multicast ? '是' : '否' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="是否保留">
            <el-tag :type="result.is_reserved ? 'warning' : 'info'">
              {{ result.is_reserved ? '是' : '否' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="form.network && result.network" style="margin-top: 20px">
          <h3>网段信息：</h3>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="网段">{{ result.network }}</el-descriptions-item>
            <el-descriptions-item label="是否在网段内">
              <el-tag :type="result.in_network ? 'success' : 'danger'">
                {{ result.in_network ? '是' : '否' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="网络地址">{{ result.network_address }}</el-descriptions-item>
            <el-descriptions-item label="广播地址">{{ result.broadcast_address }}</el-descriptions-item>
            <el-descriptions-item label="子网掩码">{{ result.netmask }}</el-descriptions-item>
            <el-descriptions-item label="主机掩码">{{ result.hostmask }}</el-descriptions-item>
            <el-descriptions-item label="地址数量">{{ result.num_addresses }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const form = ref({
  ip: '',
  network: ''
})

const result = ref(null)
const currentIp = ref(null)

onMounted(async () => {
  try {
    const res = await api.get('/ip/current')
    currentIp.value = res?.ip ?? ''
  } catch {
    currentIp.value = ''
  }
})

const check = async () => {
  if (!form.value.ip) {
    ElMessage.warning('请输入IP地址')
    return
  }

  try {
    const response = await api.post('/ip/check', {
      ip: form.value.ip,
      network: form.value.network || undefined
    })
    
    if (response.success) {
      result.value = response.data
      if (response.data.valid) {
        ElMessage.success('IP地址检查完成')
      } else {
        ElMessage.warning('IP地址无效')
      }
    } else {
      ElMessage.error(response.error || '检查失败')
    }
  } catch (error) {
    ElMessage.error('检查失败：' + (error.response?.data?.error || error.message))
  }
}
</script>

<style scoped>
.ip-page {
  max-width: 1400px;
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