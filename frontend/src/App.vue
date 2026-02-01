<template>
  <el-container>
    <el-header class="app-header">
      <h1 class="title">通用工具类集合</h1>
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
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => route.path || '/')
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
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 0 20px;
}

.app-header .title {
  font-size: 24px;
  font-weight: 500;
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