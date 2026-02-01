<template>
  <el-container>
    <el-header class="app-header">
      <h1 class="title">通用工具类集合</h1>
      <div v-if="announcement && announcement.content" class="announcement-wrap" ref="announcementWrapRef">
        <el-icon class="announcement-icon"><BellFilled /></el-icon>
        <div class="announcement-marquee-wrap" ref="marqueeWrapRef">
          <div class="announcement-inner" :class="{ 'is-scroll': needMarquee }">
            <span class="announcement-text">{{ announcement.content }}</span>
            <span v-if="needMarquee" class="announcement-text announcement-text-dup">{{ announcement.content }}</span>
          </div>
        </div>
      </div>
      <div class="header-right">
        <template v-if="authUser">
          <el-dropdown trigger="click" @command="handleUserCommand">
            <span class="header-user-dropdown">
              {{ authUser.username }}
              <el-tag v-if="authUser.is_admin" class="admin-vip-tag" size="small">VIP 管理员</el-tag>
              <el-icon class="el-icon--right"><arrow-down /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="user-info">修改用户信息</el-dropdown-item>
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

    <!-- 修改用户信息弹窗 -->
    <el-dialog v-model="userInfoDialogVisible" title="修改用户信息" width="420px" :close-on-click-modal="false" @close="resetUserInfoForm">
      <el-form :model="userInfoForm" label-width="100px">
        <el-form-item label="用户名" required>
          <el-input v-model="userInfoForm.username" placeholder="至少 2 个字符" maxlength="64" show-word-limit />
        </el-form-item>
        <el-form-item label="当前密码" required>
          <el-input v-model="userInfoForm.password" type="password" placeholder="用于验证身份" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="userInfoForm.new_password" type="password" placeholder="留空则不修改密码，至少 6 位" show-password />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="userInfoForm.confirm_password" type="password" placeholder="与新密码一致" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userInfoDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitUserInfo">确定</el-button>
      </template>
    </el-dialog>

    <!-- 发布公告弹窗 -->
    <el-dialog v-model="announcementDialogVisible" title="发布公告" width="560px" :close-on-click-modal="false" @close="announcementForm = ''">
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
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown, BellFilled } from '@element-plus/icons-vue'
import api from './api'

const route = useRoute()
const router = useRouter()
const activeMenu = computed(() => route.path || '/')
const authUser = ref(null)
const userInfoDialogVisible = ref(false)
const userInfoForm = ref({ username: '', password: '', new_password: '', confirm_password: '' })
const menuItems = ref([])
const announcement = ref(null)
const announcementDialogVisible = ref(false)
const announcementForm = ref('')
const announcementWrapRef = ref(null)
const marqueeWrapRef = ref(null)
const needMarquee = ref(false)

function checkMarquee() {
  const wrap = marqueeWrapRef.value
  const inner = wrap?.querySelector('.announcement-inner')
  if (!wrap || !inner || !announcement.value?.content) {
    needMarquee.value = false
    return
  }
  needMarquee.value = inner.scrollWidth > wrap.clientWidth
}

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
  if (cmd === 'user-info') {
    userInfoForm.value.username = authUser.value?.username || ''
    userInfoForm.value.password = ''
    userInfoForm.value.new_password = ''
    userInfoForm.value.confirm_password = ''
    userInfoDialogVisible.value = true
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
  return api.get('/site/announcement').then(r => {
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

function resetUserInfoForm() {
  userInfoForm.value = { username: '', password: '', new_password: '', confirm_password: '' }
}

function submitUserInfo() {
  const { username, password, new_password, confirm_password } = userInfoForm.value
  const un = (username || '').trim()
  if (!password) {
    ElMessage.warning('请填写当前密码以验证身份')
    return
  }
  if (!un && !new_password) {
    ElMessage.warning('请填写新用户名和/或新密码')
    return
  }
  if (un && un.length < 2) {
    ElMessage.warning('用户名至少 2 个字符')
    return
  }
  if (new_password && new_password.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (new_password && new_password !== confirm_password) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  const body = { password, username: un || undefined, new_password: new_password || undefined }
  api.put('/auth/me', body)
    .then(r => {
      if (r.success) {
        ElMessage.success('用户信息已更新')
        userInfoDialogVisible.value = false
        resetUserInfoForm()
        loadAuthUser()
      } else {
        ElMessage.error(r.error || '修改失败')
      }
    })
    .catch(e => ElMessage.error(e.response?.data?.error || e.message || '修改失败'))
}

onMounted(() => {
  loadAuthUser()
  loadMenu()
  loadAnnouncement().then(() => nextTick(checkMarquee))
  window.addEventListener('site-menu-updated', loadMenu)
  window.addEventListener('resize', checkMarquee)
})
onUnmounted(() => {
  window.removeEventListener('site-menu-updated', loadMenu)
  window.removeEventListener('resize', checkMarquee)
})
watch(announcement, () => nextTick(checkMarquee), { deep: true })
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
  flex-wrap: nowrap;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 0 20px;
  min-width: 0;
}

.app-header .title {
  font-size: 24px;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-right .el-button {
  color: rgba(255, 255, 255, 0.95);
}

/* 金色 VIP 管理员标识 */
.admin-vip-tag {
  background: linear-gradient(135deg, #d4af37 0%, #f4e4a6 50%, #c9a227 100%) !important;
  border: 1px solid rgba(255, 215, 0, 0.6) !important;
  color: #2c1810 !important;
  font-weight: 600;
}
.header-right .admin-vip-tag {
  color: #2c1810 !important;
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
  flex-wrap: nowrap;
  overflow-x: auto;
}

.app-menu .el-menu-item {
  font-size: 14px;
}

/* 公告：标题与账号之间，喇叭图标 + 长文滚动，略偏右 */
.announcement-wrap {
  flex: 1;
  min-width: 0;
  max-width: 60%;
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 20px 0 48px;
  color: rgba(255, 255, 255, 0.95);
  font-size: 14px;
}
.announcement-icon {
  font-size: 18px;
  flex-shrink: 0;
  animation: announcement-bell 2s ease-in-out infinite;
}
@keyframes announcement-bell {
  0%, 100% { transform: scale(1) rotate(0deg); }
  15% { transform: scale(1.1) rotate(-8deg); }
  30% { transform: scale(1.1) rotate(8deg); }
  45% { transform: scale(1.1) rotate(-6deg); }
  60% { transform: scale(1.1) rotate(6deg); }
  75% { transform: scale(1.05) rotate(-2deg); }
}
.announcement-marquee-wrap {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}
.announcement-inner {
  display: inline-block;
  white-space: nowrap;
}
.announcement-inner.is-scroll {
  display: inline-flex;
  animation: announcement-marquee 25s linear infinite;
}
.announcement-inner.is-scroll .announcement-text {
  flex-shrink: 0;
  padding-right: 3em;
}
.announcement-text-dup {
  padding-right: 3em;
}
@keyframes announcement-marquee {
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

.app-main {
  padding: 28px 80px;
  max-width: 1800px;
  margin: 0 auto;
  min-height: calc(100vh - 120px);
  width: 100%;
}
</style>