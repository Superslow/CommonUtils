<template>
  <el-container>
    <el-alert
      v-if="announcement && announcement.content"
      type="info"
      :title="announcement.content"
      :closable="false"
      class="app-announcement"
      show-icon
    />
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
                <el-dropdown-item v-if="authUser.is_admin" command="menu-management">菜单管理</el-dropdown-item>
                <el-dropdown-item v-if="authUser.is_admin" command="announcement">发布公告</el-dropdown-item>
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

    <!-- 发布公告弹窗 -->
    <el-dialog v-model="announcementDialogVisible" title="发布公告" width="560px" @close="announcementForm = ''">
      <el-input v-model="announcementForm" type="textarea" :rows="6" placeholder="输入公告内容，留空可清空公告" />
      <template #footer>
        <el-button @click="announcementDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAnnouncement">发布</el-button>
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
      <el-menu-item v-for="item in menuItems" :key="item.path" v-show="item.visible !== false" :index="item.path">
        {{ item.label }}
      </el-menu-item>
    </el-menu>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
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
const menuItems = ref([])
const announcement = ref(null)
const announcementDialogVisible = ref(false)
const announcementForm = ref('')

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
    return
  }
  if (cmd === 'menu-management') {
    router.push('/menu-management')
    return
  }
  if (cmd === 'announcement') {
    announcementForm.value = announcement.value?.content || ''
    announcementDialogVisible.value = true
  }
}

function loadMenu() {
  api.get('/site/menu').then(r => {
    if (r.success && r.data && r.data.length) menuItems.value = r.data
    else menuItems.value = [
      { label: '首页', path: '/', sort_order: 0, visible: true },
      { label: '时间戳转换', path: '/timestamp', sort_order: 1, visible: true },
      { label: 'JSON校验', path: '/json', sort_order: 2, visible: true },
      { label: '编码转换', path: '/encode', sort_order: 3, visible: true },
      { label: 'MD5计算', path: '/md5', sort_order: 4, visible: true },
      { label: 'IP网段', path: '/ip', sort_order: 5, visible: true },
      { label: 'Cron解析', path: '/cron', sort_order: 6, visible: true },
      { label: '日期格式', path: '/date-format', sort_order: 7, visible: true },
      { label: '数据构造', path: '/data-construction', sort_order: 8, visible: true }
    ]
  }).catch(() => {
    menuItems.value = [
      { label: '首页', path: '/', sort_order: 0, visible: true },
      { label: '时间戳转换', path: '/timestamp', sort_order: 1, visible: true },
      { label: 'JSON校验', path: '/json', sort_order: 2, visible: true },
      { label: '编码转换', path: '/encode', sort_order: 3, visible: true },
      { label: 'MD5计算', path: '/md5', sort_order: 4, visible: true },
      { label: 'IP网段', path: '/ip', sort_order: 5, visible: true },
      { label: 'Cron解析', path: '/cron', sort_order: 6, visible: true },
      { label: '日期格式', path: '/date-format', sort_order: 7, visible: true },
      { label: '数据构造', path: '/data-construction', sort_order: 8, visible: true }
    ]
  })
}

function loadAnnouncement() {
  api.get('/site/announcement').then(r => {
    if (r.success && r.data) announcement.value = r.data
    else announcement.value = null
  }).catch(() => { announcement.value = null })
}

function submitAnnouncement() {
  api.post('/site/announcement', { content: announcementForm.value })
    .then(r => {
      if (r.success) {
        ElMessage.success('公告已发布')
        announcementDialogVisible.value = false
        loadAnnouncement()
      } else {
        ElMessage.error(r.error || '发布失败')
      }
    })
    .catch(e => ElMessage.error(e.response?.data?.error || e.message || '发布失败'))
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

onMounted(() => {
  loadAuthUser()
  loadMenu()
  loadAnnouncement()
  window.addEventListener('site-menu-updated', loadMenu)
})
onUnmounted(() => {
  window.removeEventListener('site-menu-updated', loadMenu)
})
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

.app-announcement {
  border-radius: 0;
  margin: 0;
}

.app-main {
  padding: 28px 48px;
  max-width: 1800px;
  margin: 0 auto;
  min-height: calc(100vh - 120px);
  width: 100%;
}
</style>