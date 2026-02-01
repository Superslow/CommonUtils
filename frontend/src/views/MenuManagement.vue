<template>
  <div class="menu-management-page">
    <el-card>
      <template #header>
        <span>菜单管理</span>
      </template>
      <p class="desc">调整菜单顺序与是否在顶栏显示。拖拽行可调整顺序。</p>
      <el-table :data="menuItems" border row-key="path" style="width: 100%">
        <el-table-column type="index" label="序号" width="60" />
        <el-table-column prop="label" label="名称" width="140" />
        <el-table-column prop="path" label="路径" width="180" />
        <el-table-column label="顶栏可见" width="100">
          <template #default="{ row }">
            <el-switch v-model="row.visible" />
          </template>
        </el-table-column>
        <el-table-column label="上移/下移" width="140">
          <template #default="{ row, $index }">
            <el-button link type="primary" :disabled="$index === 0" @click="moveUp($index)">上移</el-button>
            <el-button link type="primary" :disabled="$index === menuItems.length - 1" @click="moveDown($index)">下移</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 16px">
        <el-button type="primary" @click="save">保存</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const menuItems = ref([])

function load() {
  api.get('/site/menu').then(r => {
    if (r.success && r.data && r.data.length) {
      menuItems.value = r.data.map((x, i) => ({ ...x, sort_order: x.sort_order ?? i }))
    }
  }).catch(() => ElMessage.error('加载失败'))
}

function moveUp(i) {
  if (i <= 0) return
  const arr = [...menuItems.value]
  ;[arr[i - 1], arr[i]] = [arr[i], arr[i - 1]]
  menuItems.value = arr.map((x, j) => ({ ...x, sort_order: j }))
}

function moveDown(i) {
  if (i >= menuItems.value.length - 1) return
  const arr = [...menuItems.value]
  ;[arr[i], arr[i + 1]] = [arr[i + 1], arr[i]]
  menuItems.value = arr.map((x, j) => ({ ...x, sort_order: j }))
}

function save() {
  const items = menuItems.value.map((x, i) => ({
    label: x.label,
    path: x.path,
    sort_order: i,
    visible: x.visible !== false
  }))
  api.put('/site/menu', { items })
    .then(r => {
      if (r.success) {
        ElMessage.success('已保存')
        window.dispatchEvent(new CustomEvent('site-menu-updated'))
      } else {
        ElMessage.error(r.error || '保存失败')
      }
    })
    .catch(e => ElMessage.error(e.response?.data?.error || e.message || '保存失败'))
}

onMounted(load)
</script>

<style scoped>
.menu-management-page {
  max-width: 720px;
  margin: 0 auto;
}

.desc {
  color: #606266;
  font-size: 14px;
  margin-bottom: 16px;
}
</style>
