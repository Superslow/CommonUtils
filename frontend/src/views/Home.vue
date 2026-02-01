<template>
  <div class="home">
    <el-row :gutter="20">
      <el-col :xs="24" :sm="12" :md="8" v-for="tool in tools" :key="tool.path">
        <el-card class="tool-card" @click="goToTool(tool.path)" shadow="hover">
          <div class="tool-icon">
            <el-icon :size="40"><component :is="tool.icon" /></el-icon>
          </div>
          <h3>{{ tool.title }}</h3>
          <p>{{ tool.description }}</p>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { Clock, Document, Connection, Files, Monitor, Timer, DataAnalysis } from '@element-plus/icons-vue'

const router = useRouter()

const tools = [
  {
    title: '时间戳转换',
    description: '时间戳与日期时间相互转换',
    icon: 'Clock',
    path: '/timestamp'
  },
  {
    title: 'JSON格式化校验',
    description: 'JSON格式验证和美化',
    icon: 'Document',
    path: '/json'
  },
  {
    title: '编码转换',
    description: '文本编码转换和Base64编解码',
    icon: 'Connection',
    path: '/encode'
  },
  {
    title: '文件MD5计算',
    description: '计算文件的MD5哈希值',
    icon: 'Files',
    path: '/md5'
  },
  {
    title: 'IP网段判断',
    description: 'IP地址归属和网段判断',
    icon: 'Monitor',
    path: '/ip'
  },
  {
    title: 'Cron表达式解析',
    description: '解析Cron表达式并查看执行时间',
    icon: 'Timer',
    path: '/cron'
  },
  {
    title: '数据构造',
    description: '定时构造 Kafka 消息 / ClickHouse 数据，模板+参数渲染',
    icon: 'DataAnalysis',
    path: '/data-construction'
  }
]

const goToTool = (path) => {
  router.push(path)
}
</script>

<style scoped>
.home {
  padding: 20px;
}

.tool-card {
  margin-bottom: 20px;
  cursor: pointer;
  transition: transform 0.2s;
  height: 180px;
}

.tool-card:hover {
  transform: translateY(-5px);
}

.tool-icon {
  text-align: center;
  color: #667eea;
  margin-bottom: 10px;
}

.tool-card h3 {
  text-align: center;
  margin: 10px 0;
  color: #333;
}

.tool-card p {
  text-align: center;
  color: #666;
  font-size: 14px;
}
</style>