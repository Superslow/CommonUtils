<template>
  <div class="user-management-page">
    <el-card>
      <template #header>
        <span>用户管理</span>
      </template>
      <div class="toolbar-row">
        <el-button @click="loadUsers">刷新</el-button>
      </div>
      <el-table :data="users" border style="width: 100%; margin-top: 12px;">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" width="160" />
        <el-table-column label="管理员" width="160" class-name="admin-col">
          <template #default="{ row }">
            <span class="admin-cell">
              <el-switch
                :model-value="!!row.is_admin"
                :disabled="row.id === currentUserId"
                @change="(v) => setAdmin(row.id, v)"
              />
              <span v-if="row.id === currentUserId" class="self-hint">（当前用户）</span>
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const users = ref([])
const currentUserId = ref(null)

function loadUsers() {
  api.get('/auth/me').then(r => {
    if (r.success && r.data) currentUserId.value = r.data.id
  }).catch(() => {})
  api.get('/users').then(r => {
    if (r.success) users.value = r.data
    else ElMessage.error(r.error || '加载失败')
  }).catch(e => {
    ElMessage.error(e.response?.data?.error === '无权限' ? '仅管理员可访问' : (e.message || '加载失败'))
  })
}

function setAdmin(uid, isAdmin) {
  api.put(`/users/${uid}`, { is_admin: isAdmin })
    .then(r => {
      if (r.success) {
        ElMessage.success(isAdmin ? '已设为管理员' : '已取消管理员')
        loadUsers()
      } else {
        ElMessage.error(r.error || '操作失败')
      }
    })
    .catch(e => ElMessage.error(e.response?.data?.error || e.message || '操作失败'))
}

onMounted(loadUsers)
</script>

<style scoped>
.user-management-page {
  max-width: 900px;
  margin: 0 auto;
}

.admin-cell {
  white-space: nowrap;
}
.self-hint {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}

.toolbar-row {
  display: flex;
  gap: 10px;
  margin-bottom: 0;
}
</style>
