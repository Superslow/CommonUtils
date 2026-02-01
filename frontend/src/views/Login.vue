<template>
  <div class="login-page">
    <el-card class="login-card">
      <template #header>
        <span>登录 / 注册</span>
      </template>
      <el-tabs v-model="tab" class="login-tabs">
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" label-width="80px" @submit.prevent="handleLogin">
            <el-form-item label="用户名">
              <el-input v-model="loginForm.username" placeholder="用户名" autocomplete="username" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="loginForm.password" type="password" placeholder="密码" show-password autocomplete="current-password" @keyup.enter="handleLogin" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" @click="handleLogin" style="width: 100%">登录</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="注册" name="register">
          <el-form :model="registerForm" label-width="80px">
            <el-form-item label="用户名">
              <el-input v-model="registerForm.username" placeholder="至少 2 个字符" autocomplete="username" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="registerForm.password" type="password" placeholder="至少 6 位" show-password autocomplete="new-password" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" @click="handleRegister" style="width: 100%">注册</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const router = useRouter()
const route = useRoute()
const tab = ref('login')
const loading = ref(false)

const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', password: '' })

function getRedirect() {
  const r = route.query.redirect
  return r && r.startsWith('/') ? r : '/data-construction'
}

function setToken(token) {
  localStorage.setItem('token', token)
}

function handleLogin() {
  if (!loginForm.username?.trim() || !loginForm.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  api.post('/auth/login', { username: loginForm.username.trim(), password: loginForm.password })
    .then((res) => {
      if (res.success && res.data?.token) {
        setToken(res.data.token)
        ElMessage.success('登录成功')
        router.replace(getRedirect())
      } else {
        ElMessage.error(res.error || '登录失败')
      }
    })
    .catch((err) => {
      const msg = err.response?.data?.error || err.message || '登录失败'
      ElMessage.error(msg)
    })
    .finally(() => { loading.value = false })
}

function handleRegister() {
  if (!registerForm.username?.trim() || registerForm.username.trim().length < 2) {
    ElMessage.warning('用户名至少 2 个字符')
    return
  }
  if (!registerForm.password || registerForm.password.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  loading.value = true
  api.post('/auth/register', { username: registerForm.username.trim(), password: registerForm.password })
    .then((res) => {
      if (res.success && res.data?.token) {
        setToken(res.data.token)
        ElMessage.success('注册成功，已自动登录')
        router.replace(getRedirect())
      } else {
        ElMessage.error(res.error || '注册失败')
      }
    })
    .catch((err) => {
      const msg = err.response?.data?.error || err.message || '注册失败'
      ElMessage.error(msg)
    })
    .finally(() => { loading.value = false })
}
</script>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 400px;
}

.login-tabs {
  margin-top: 8px;
}
</style>
