<template>
  <div class="data-construction-page">
    <div class="page-header">
      <span class="user-info">{{ currentUser?.username || '—' }} <el-tag v-if="currentUser?.is_admin" type="danger" size="small">管理员</el-tag></span>
      <el-button type="primary" link @click="logout">退出</el-button>
    </div>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="Agent 管理" name="agents">
        <el-button type="primary" @click="showAgentDialog()">新增 Agent</el-button>
        <el-table :data="agents" border style="width: 100%; margin-top: 16px;">
          <el-table-column prop="name" label="名称" width="120" />
          <el-table-column prop="url" label="URL" min-width="200" />
          <el-table-column v-if="currentUser?.is_admin" prop="creator_username" label="创建者" width="100" />
          <el-table-column prop="status" label="状态" width="80" />
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="checkAgentRow(row)">校验</el-button>
              <el-button v-if="row.is_owner" link type="primary" @click="showAgentDialog(row)">编辑</el-button>
              <el-button v-if="row.is_owner" link type="danger" @click="deleteAgent(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="数据构造任务" name="tasks">
        <el-button type="primary" @click="showTaskDialog()">新增任务</el-button>
        <el-table :data="tasks" border style="width: 100%; margin-top: 16px;">
          <el-table-column prop="name" label="任务名" width="140" />
          <el-table-column prop="task_type" label="类型" width="100" />
          <el-table-column prop="cron_expr" label="Cron" width="120" />
          <el-table-column prop="batch_size" label="每批条数" width="90" />
          <el-table-column prop="agent_name" label="Agent" width="120" />
          <el-table-column v-if="currentUser?.is_admin" prop="creator_username" label="创建者" width="100" />
          <el-table-column prop="status" label="状态" width="80" />
          <el-table-column label="操作" width="260" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.is_owner" link type="success" @click="startTask(row)" :disabled="row.status === 'running'">启动</el-button>
              <el-button v-if="row.is_owner" link type="warning" @click="stopTask(row)" :disabled="row.status !== 'running'">停止</el-button>
              <el-button link type="primary" @click="showExecutions(row)">执行记录</el-button>
              <el-button v-if="row.is_owner" link type="primary" @click="showTaskDialog(row)">编辑</el-button>
              <el-button v-if="row.is_owner" link type="danger" @click="deleteTask(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane v-if="currentUser?.is_admin" label="用户管理" name="users">
        <el-table :data="users" border style="width: 100%; margin-top: 16px;">
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="username" label="用户名" width="140" />
          <el-table-column prop="is_admin" label="管理员" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_admin ? 'danger' : 'info'">{{ row.is_admin ? '是' : '否' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="注册时间" width="180" />
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- Agent 弹窗 -->
    <el-dialog v-model="agentDialogVisible" :title="editingAgent ? '编辑 Agent' : '新增 Agent'" width="560px">
      <el-form :model="agentForm" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="agentForm.name" placeholder="Agent 名称" />
        </el-form-item>
        <el-form-item label="URL" required>
          <el-input v-model="agentForm.url" placeholder="http://host:5001" />
        </el-form-item>
        <el-form-item :required="!editingAgent">
          <template #label>Token</template>
          <el-input v-model="agentForm.token" type="password" :placeholder="editingAgent ? '编辑时留空则保持原 Token' : 'Agent 启动时控制台输出的 Token'" show-password />
        </el-form-item>
        <el-form-item label="Kafka 配置">
          <el-input v-model="agentForm.kafkaConfigStr" type="textarea" :rows="4" placeholder='可选，JSON，如 {"bootstrap_servers":"localhost:9092","topic":"test"}' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="agentDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAgent">确定</el-button>
      </template>
    </el-dialog>

    <!-- 校验 Agent 弹窗 -->
    <el-dialog v-model="checkDialogVisible" title="校验 Agent" width="400px">
      <el-form label-width="80px">
        <el-form-item label="URL">
          <el-input v-model="checkForm.url" placeholder="http://host:5001" />
        </el-form-item>
        <el-form-item label="Token">
          <el-input v-model="checkForm.token" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="checkDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="doCheckAgent">校验</el-button>
      </template>
      <el-alert v-if="checkResult !== null" :type="checkResult ? 'success' : 'error'" :title="checkResult ? 'Agent 可用' : 'Agent 不可用'" style="margin-top: 12px;" />
    </el-dialog>

    <!-- 任务弹窗 -->
    <el-dialog v-model="taskDialogVisible" :title="editingTask ? '编辑任务' : '新增任务'" width="900px">
      <el-form :model="taskForm" label-width="120px">
        <el-form-item label="任务名称" required>
          <el-input v-model="taskForm.name" placeholder="任务名称" />
        </el-form-item>
        <el-form-item label="任务类型" required>
          <el-select v-model="taskForm.task_type" placeholder="类型">
            <el-option label="Kafka" value="kafka" />
            <el-option label="ClickHouse" value="clickhouse" />
          </el-select>
        </el-form-item>
        <el-form-item label="Cron 表达式" required>
          <el-input v-model="taskForm.cron_expr" placeholder="5 字段：* * * * * 每分钟；6 字段 Quartz：0 * * * * ? 每分钟" />
        </el-form-item>
        <el-form-item label="每批条数" required>
          <el-input-number v-model="taskForm.batch_size" :min="1" :max="1000" />
        </el-form-item>
        <el-form-item label="执行 Agent" required>
          <el-select v-model="taskForm.agent_id" placeholder="选择 Agent" filterable style="width: 100%">
            <el-option v-for="a in agents" :key="a.id" :label="a.name" :value="a.id" />
          </el-select>
        </el-form-item>
        <template v-if="taskForm.task_type === 'kafka'">
          <el-divider content-position="left">Kafka 连接配置</el-divider>
          <el-form-item label="Bootstrap" required>
            <el-input v-model="taskForm.kafkaBootstrap" placeholder="如 localhost:9092 或 host1:9092,host2:9092" />
          </el-form-item>
          <el-form-item label="Topic" required>
            <el-input v-model="taskForm.kafkaTopic" placeholder="主题名" />
          </el-form-item>
          <el-form-item label="用户名">
            <el-input v-model="taskForm.kafkaUsername" placeholder="可选" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="taskForm.kafkaPassword" type="password" show-password placeholder="可选" />
          </el-form-item>
          <el-form-item label="CA 证书">
            <el-input v-model="taskForm.kafkaSslCafile" placeholder="服务端 CA 证书路径" style="max-width: 360px">
              <template #append>
                <el-upload :show-file-list="false" :before-upload="(f) => { uploadCert(f, 'kafkaSslCafile'); return false }" accept=".pem,.crt,.cer">
                  <el-button type="primary">上传</el-button>
                </el-upload>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item label="客户端证书">
            <el-input v-model="taskForm.kafkaSslCertfile" placeholder="客户端证书路径" style="max-width: 360px">
              <template #append>
                <el-upload :show-file-list="false" :before-upload="(f) => { uploadCert(f, 'kafkaSslCertfile'); return false }" accept=".pem,.crt,.cer">
                  <el-button type="primary">上传</el-button>
                </el-upload>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item label="客户端私钥">
            <el-input v-model="taskForm.kafkaSslKeyfile" placeholder="客户端私钥路径" style="max-width: 360px">
              <template #append>
                <el-upload :show-file-list="false" :before-upload="(f) => { uploadCert(f, 'kafkaSslKeyfile'); return false }" accept=".pem,.key">
                  <el-button type="primary">上传</el-button>
                </el-upload>
              </template>
            </el-input>
          </el-form-item>
        </template>
        <template v-else>
          <el-divider content-position="left">ClickHouse 连接配置</el-divider>
          <el-form-item label="Host" required>
            <el-input v-model="taskForm.chHost" placeholder="如 localhost" />
          </el-form-item>
          <el-form-item label="Port" required>
            <el-input-number v-model="taskForm.chPort" :min="1" :max="65535" />
          </el-form-item>
          <el-form-item label="用户">
            <el-input v-model="taskForm.chUser" placeholder="默认 default" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="taskForm.chPassword" type="password" show-password placeholder="可选" />
          </el-form-item>
        </template>
        <el-form-item v-if="taskForm.task_type === 'kafka'" label="消息模板(JSON)">
          <el-input v-model="taskForm.template_content" type="textarea" :rows="12" placeholder='可变字段用 {param} 包裹，如 {"id":{id},"time":{now}}' />
          <el-button type="primary" link @click="parseTemplateParams">识别可变参数</el-button>
          <span v-if="templateParams.length"> 已识别: {{ templateParams.join(", ") }}</span>
        </el-form-item>
        <el-form-item v-else label="SQL 模板">
          <el-input v-model="taskForm.template_content" type="textarea" :rows="10" placeholder='一组 SQL，可变处用 {param}，可 JSON 数组' />
          <el-button type="primary" link @click="parseTemplateParams">识别可变参数</el-button>
        </el-form-item>
        <el-form-item v-if="templateParams.length" label="参数配置">
          <div v-for="p in paramConfigList" :key="p.param" style="display:flex;align-items:center;margin-bottom:8px">
            <span style="width:100px">{{ p.param }}</span>
            <el-select v-model="p.type" placeholder="类型" style="width:160px">
              <el-option label="固定内容" value="fixed" />
              <el-option label="当前时间" value="current_time" />
              <el-option label="13位时间戳" value="timestamp_13" />
              <el-option label="10位时间戳" value="timestamp_10" />
              <el-option label="轮询" value="round_robin" />
              <el-option label="批次号" value="batch" />
            </el-select>
            <el-input v-model="p.value" placeholder="值(轮询用逗号分隔)" style="margin-left:8px;flex:1" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="taskDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitTask">确定</el-button>
      </template>
    </el-dialog>

    <!-- 执行记录弹窗 -->
    <el-dialog v-model="executionsDialogVisible" title="执行记录" width="800px">
      <el-table :data="executions" border max-height="400">
        <el-table-column prop="batch_no" label="批次" width="80" />
        <el-table-column prop="executed_at" label="执行时间" width="180" />
        <el-table-column prop="success" label="成功" width="70">
          <template #default="{ row }">{{ row.success ? '是' : '否' }}</template>
        </el-table-column>
        <el-table-column prop="records_count" label="条数" width="80" />
        <el-table-column prop="result_message" label="结果" show-overflow-tooltip />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const router = useRouter()
const activeTab = ref('agents')
const currentUser = ref(null)
const agents = ref([])
const tasks = ref([])
const users = ref([])
const agentDialogVisible = ref(false)
const editingAgent = ref(null)
const agentForm = ref({ name: '', url: '', token: '', kafkaConfigStr: '' })
const checkDialogVisible = ref(false)
const checkForm = ref({ url: '', token: '' })
const checkResult = ref(null)
const taskDialogVisible = ref(false)
const editingTask = ref(null)
const taskForm = ref({
  name: '', task_type: 'kafka', cron_expr: '* * * * *', batch_size: 1, agent_id: null,
  template_content: '',
  kafkaBootstrap: '', kafkaTopic: '', kafkaUsername: '', kafkaPassword: '',
  kafkaSslCafile: '', kafkaSslCertfile: '', kafkaSslKeyfile: '',
  chHost: 'localhost', chPort: 9000, chUser: 'default', chPassword: ''
})
const templateParams = ref([])
const paramConfigList = ref([])
const executionsDialogVisible = ref(false)
const executions = ref([])
const currentTaskId = ref(null)

function loadCurrentUser() {
  api.get('/auth/me').then(r => { if (r.success) currentUser.value = r.data }).catch(() => { currentUser.value = null })
}
function logout() {
  localStorage.removeItem('token')
  currentUser.value = null
  router.push('/login?redirect=/data-construction')
}

const loadAgents = () => api.get('/agents').then(r => { if (r.success) agents.value = r.data })
const loadTasks = () => api.get('/data-tasks').then(r => { if (r.success) tasks.value = r.data })
const loadUsers = () => api.get('/users').then(r => { if (r.success) users.value = r.data })

loadCurrentUser()
watch(activeTab, (t) => {
  if (t === 'agents') loadAgents()
  else if (t === 'tasks') loadTasks()
  else if (t === 'users') loadUsers()
}, { immediate: true })

function showAgentDialog(row) {
  editingAgent.value = row || null
  agentForm.value = row
    ? { name: row.name, url: row.url, token: '', kafkaConfigStr: (row.kafka_config && typeof row.kafka_config === 'object') ? JSON.stringify(row.kafka_config, null, 2) : '' }
    : { name: '', url: '', token: '', kafkaConfigStr: '' }
  agentDialogVisible.value = true
}

function submitAgent() {
  const token = (agentForm.value.token || '').trim()
  if (!editingAgent.value && !token) {
    ElMessage.warning('新增 Agent 时 Token 必填')
    return
  }
  const payload = { name: agentForm.value.name, url: agentForm.value.url }
  if (token) payload.token = token
  if (agentForm.value.kafkaConfigStr.trim()) {
    try { payload.kafka_config = JSON.parse(agentForm.value.kafkaConfigStr) } catch (e) { ElMessage.error('Kafka 配置不是合法 JSON'); return }
  }
  const req = editingAgent.value
    ? api.put(`/agents/${editingAgent.value.id}`, payload)
    : api.post('/agents', payload)
  req.then(r => { if (r.success) { ElMessage.success('保存成功'); agentDialogVisible.value = false; loadAgents() } else ElMessage.error(r.error || '失败') }).catch(e => ElMessage.error(e.response?.data?.error || e.message))
}

function checkAgentRow(row) {
  checkForm.value = { url: row.url, token: '' }
  checkResult.value = null
  checkDialogVisible.value = true
}

function doCheckAgent() {
  api.post('/agents/check', { url: checkForm.value.url, token: checkForm.value.token }).then(r => {
    if (r.success) { checkResult.value = r.data.available } else ElMessage.error(r.error)
  }).catch(e => { checkResult.value = false; ElMessage.error(e.response?.data?.error || e.message) })
}

function deleteAgent(row) {
  ElMessageBox.confirm('确定删除该 Agent？', '提示', { type: 'warning' }).then(() => {
    api.delete(`/agents/${row.id}`).then(r => { if (r.success) { ElMessage.success('已删除'); loadAgents() } else ElMessage.error(r.error) })
  }).catch(() => {})
}

function showTaskDialog(row) {
  editingTask.value = row || null
  if (row) {
    const k = row.connector_config?.kafka || {}
    const c = row.connector_config?.clickhouse || {}
    taskForm.value = {
      name: row.name, task_type: row.task_type, cron_expr: row.cron_expr, batch_size: row.batch_size, agent_id: row.agent_id,
      template_content: row.template_content,
      kafkaBootstrap: k.bootstrap_servers || '', kafkaTopic: k.topic || '', kafkaUsername: k.username || '', kafkaPassword: k.password || '',
      kafkaSslCafile: k.ssl_cafile || '', kafkaSslCertfile: k.ssl_certfile || '', kafkaSslKeyfile: k.ssl_keyfile || '',
      chHost: c.host || 'localhost', chPort: c.port ?? 9000, chUser: c.user || 'default', chPassword: c.password || ''
    }
    templateParams.value = []
    paramConfigList.value = []
    if (row.param_config && row.param_config.length) {
      templateParams.value = row.param_config.map(x => x.param)
      paramConfigList.value = row.param_config
    }
  } else {
    taskForm.value = {
      name: '', task_type: 'kafka', cron_expr: '* * * * *', batch_size: 1, agent_id: null, template_content: '',
      kafkaBootstrap: '', kafkaTopic: '', kafkaUsername: '', kafkaPassword: '',
      kafkaSslCafile: '', kafkaSslCertfile: '', kafkaSslKeyfile: '',
      chHost: 'localhost', chPort: 9000, chUser: 'default', chPassword: ''
    }
    templateParams.value = []
    paramConfigList.value = []
  }
  taskDialogVisible.value = true
}

async function uploadCert(file, fieldName) {
  const formData = new FormData()
  formData.append('file', file)
  try {
    const r = await api.post('/upload/cert', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
    if (r.success && r.data && r.data.path) {
      taskForm.value[fieldName] = r.data.path
      ElMessage.success('上传成功')
    } else {
      ElMessage.error(r.error || '上传失败')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.error || e.message || '上传失败')
  }
  return false
}

function parseTemplateParams() {
  api.post('/template/params', { template: taskForm.value.template_content }).then(r => {
    if (r.success && r.data.length) {
      templateParams.value = r.data
      const existing = paramConfigList.value.map(x => x.param)
      paramConfigList.value = r.data.map(p => existing.includes(p) ? paramConfigList.value.find(x => x.param === p) : { param: p, type: 'fixed', value: '' })
    } else {
      templateParams.value = []
      paramConfigList.value = []
    }
  }).catch(e => ElMessage.error(e.message))
}

function submitTask() {
  if (!taskForm.value.agent_id) {
    ElMessage.warning('请选择执行 Agent')
    return
  }
  let connector_config = {}
  if (taskForm.value.task_type === 'kafka') {
    if (!taskForm.value.kafkaBootstrap?.trim() || !taskForm.value.kafkaTopic?.trim()) {
      ElMessage.error('请填写 Kafka Bootstrap 和 Topic')
      return
    }
    connector_config.kafka = {
      bootstrap_servers: taskForm.value.kafkaBootstrap.trim(),
      topic: taskForm.value.kafkaTopic.trim(),
      username: taskForm.value.kafkaUsername?.trim() || undefined,
      password: taskForm.value.kafkaPassword?.trim() || undefined,
      ssl_cafile: taskForm.value.kafkaSslCafile?.trim() || undefined,
      ssl_certfile: taskForm.value.kafkaSslCertfile?.trim() || undefined,
      ssl_keyfile: taskForm.value.kafkaSslKeyfile?.trim() || undefined
    }
  } else {
    connector_config.clickhouse = {
      host: taskForm.value.chHost?.trim() || 'localhost',
      port: taskForm.value.chPort ?? 9000,
      user: taskForm.value.chUser?.trim() || 'default',
      password: taskForm.value.chPassword?.trim() || undefined
    }
  }
  const payload = {
    name: taskForm.value.name, task_type: taskForm.value.task_type, cron_expr: taskForm.value.cron_expr,
    batch_size: taskForm.value.batch_size, agent_id: taskForm.value.agent_id, template_content: taskForm.value.template_content,
    param_config: paramConfigList.value.length ? paramConfigList.value : null, connector_config
  }
  const p = editingTask.value ? api.put(`/data-tasks/${editingTask.value.id}`, payload) : api.post('/data-tasks', payload)
  p.then(r => { if (r.success) { ElMessage.success('保存成功'); taskDialogVisible.value = false; loadTasks() } else ElMessage.error(r.error || '失败') }).catch(e => ElMessage.error(e.response?.data?.error || e.message))
}

function startTask(row) {
  api.post(`/data-tasks/${row.id}/start`).then(r => { if (r.success) { ElMessage.success('已启动'); loadTasks() } else ElMessage.error(r.error) })
}

function stopTask(row) {
  api.post(`/data-tasks/${row.id}/stop`).then(r => { if (r.success) { ElMessage.success('已停止'); loadTasks() } else ElMessage.error(r.error) })
}

function deleteTask(row) {
  ElMessageBox.confirm('确定删除该任务？', '提示', { type: 'warning' }).then(() => {
    api.delete(`/data-tasks/${row.id}`).then(r => { if (r.success) { ElMessage.success('已删除'); loadTasks() } else ElMessage.error(r.error) })
  }).catch(() => {})
}

function showExecutions(row) {
  currentTaskId.value = row.id
  api.get(`/data-tasks/${row.id}/executions`).then(r => { if (r.success) executions.value = r.data; executionsDialogVisible.value = true })
}
</script>

<style scoped>
.data-construction-page {
  max-width: 1600px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-bottom: 16px;
}

.user-info {
  font-size: 14px;
  color: #606266;
}
</style>
