<template>
  <el-container>
    <el-header class="app-header">
      <h1 class="title">通用工具类集合</h1>
      <div class="header-right">
        <template v-if="authUser">
          <span class="header-user">{{ authUser.username }}</span>
          <el-tag v-if="authUser.is_admin" type="danger" size="small">管理员</el-tag>
          <el-button type="primary" link @click="handleLogout">退出</el-button>
        </template>
        <el-button v-else type="primary" link @click="goLogin">登录</el-button>
      </div>
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
import api from './api'

const route = useRoute()
const router = useRouter()
const activeMenu = computed(() => route.path || '/')
const authUser = ref(null)

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

function handleLogout() {
  localStorage.removeItem('token')
  authUser.value = null
  router.push('/')
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

.header-user {
  font-size: 14px;
  margin-right: 4px;
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