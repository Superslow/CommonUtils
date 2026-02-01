<template>
  <el-container>
    <el-header class="app-header">
      <h1 class="title">通用工具类集合</h1>
      <div class="header-right">
        <template v-if="authUser">
          <el-dropdown trigger="click" @command="handleUserCommand">
            <span class="header-user-dropdown">
              {{ authUser.username }}
              <el-tag v-if="authUser.is_admin" type="danger" size="small">管理员</el-tag>
              <el-icon class="el-icon--right"><arrow-down /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="change-password">修改密码</el-dropdown-item>
                <el-dropdown-item v-if="authUser.is_admin" command="user-management">用户管理</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <el-button v-else type="primary" link @click="goLogin">登录</el-button>
      </div>

    <!-- 修改密码弹窗 -->
    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="400px" @close="resetPasswordForm">
      <el-form :model="passwordForm" label-width="90px">
        <el-form-item label="原密码" required>
          <el-input v-model="passwordForm.old_password" type="password" placeholder="原密码" show-password />
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input v-model="passwordForm.new_password" type="password" placeholder="至少 6 位" show-password />
        </el-form-item>
        <el-form-item label="确认新密码" required>
          <el-input v-model="passwordForm.confirm_password" type="password" placeholder="再次输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitChangePassword">确定</el-button>
      </template>
    </el-dialog>
    </el-header>
    <el-menu
      :default-active="activeMenu"
      class="app-menu"
      mode="horizontal"
      router
      :ellipsis="false"
    >
      <el-menu-item index="/">首页</el-menu-item>
      <el-menu-item index="/timestamp">时间戳转换</el-menu-item>
      <el-menu-item index="/json">JSON校验</el-menu-item>
      <el-menu-item index="/encode">编码转换</el-menu-item>
      <el-menu-item index="/md5">MD5计算</el-menu-item>
      <el-menu-item index="/ip">IP网段</el-menu-item>
      <el-menu-item index="/cron">Cron解析</el-menu-item>
      <el-menu-item index="/date-format">日期格式</el-menu-item>
      <el-menu-item index="/data-construction">数据构造</el-menu-item>
    </el-menu>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'
import api from './api'

const route = useRoute()
const router = useRouter()
const activeMenu = computed(() => route.path || '/')
const authUser = ref(null)
const passwordDialogVisible = ref(false)
const passwordForm = ref({ old_password: '', new_password: '', confirm_password: '' })

function getToken() {
  try {
    return localStorage.getItem('token')
  } catch {
    return null
  }
}

function loadAuthUser() {
  const token = getToken()
  if (!token || !token.trim()) {
    authUser.value = null
    return
  }
  api.get('/auth/me').then(r => {
    if (r.success && r.data) authUser.value = r.data
    else authUser.value = null
  }).catch(() => { authUser.value = null })
}

function goLogin() {
  const redirect = route.path === '/login' ? undefined : route.fullPath
  router.push(redirect ? { path: '/login', query: { redirect } } : '/login')
}

function handleUserCommand(cmd) {
  if (cmd === 'logout') {
    localStorage.removeItem('token')
    authUser.value = null
    router.push('/')
    return
  }
  if (cmd === 'change-password') {
    passwordDialogVisible.value = true
    return
  }
  if (cmd === 'user-management') {
    router.push('/user-management')
  }
}

function resetPasswordForm() {
  passwordForm.value = { old_password: '', new_password: '', confirm_password: '' }
}

function submitChangePassword() {
  const { old_password, new_password, confirm_password } = passwordForm.value
  if (!old_password || !new_password) {
    ElMessage.warning('请填写原密码和新密码')
    return
  }
  if (new_password.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (new_password !== confirm_password) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  api.post('/auth/change-password', { old_password, new_password })
    .then(r => {
      if (r.success) {
        ElMessage.success('密码已修改')
        passwordDialogVisible.value = false
        resetPasswordForm()
      } else {
        ElMessage.error(r.error || '修改失败')
      }
    })
    .catch(e => ElMessage.error(e.response?.data?.error || e.message || '修改失败'))
}

onMounted(loadAuthUser)
watch(() => route.path, loadAuthUser)
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 0 20px;
}

.app-header .title {
  font-size: 24px;
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-right .el-button,
.header-right .el-tag {
  color: rgba(255, 255, 255, 0.95);
}

.header-user-dropdown {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.95);
}
.header-user-dropdown .el-icon--right {
  margin-left: 4px;
}

.app-menu {
  border-bottom: 1px solid #e6e6e6;
  padding: 0 24px;
  flex-shrink: 0;
}

.app-menu .el-menu-item {
  font-size: 14px;
}

.app-main {
  padding: 28px 48px;
  max-width: 1800px;
  margin: 0 auto;
  min-height: calc(100vh - 120px);
  width: 100%;
}
</style>