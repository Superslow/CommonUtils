<template>
  <div class="data-construction-page">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="Agent 管理" name="agents">
        <div class="toolbar-row">
          <el-button type="primary" @click="showAgentDialog()">新增 Agent</el-button>
          <el-button @click="loadAgents">刷新</el-button>
          <span class="status-hint">状态每 30 秒自动更新</span>
        </div>
        <el-table :data="agents" border class="single-line-table" style="width: 100%; margin-top: 16px;">
          <el-table-column prop="name" label="名称" min-width="200" show-overflow-tooltip />
          <el-table-column prop="url" label="URL" min-width="240" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'online' ? 'success' : row.status === 'offline' ? 'danger' : 'info'" size="small">
                {{ row.status === 'online' ? '在线' : row.status === 'offline' ? '离线' : '未知' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right" align="left">
            <template #default="{ row }">
              <span class="op-cell">
                <el-button link type="primary" @click="checkAgentRow(row)">校验</el-button>
                <el-button v-if="row.is_owner" link type="primary" @click="showAgentDialog(row)">编辑</el-button>
                <el-button v-if="row.is_owner" link type="danger" @click="deleteAgent(row)">删除</el-button>
              </span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane v-if="currentUser?.is_admin" label="Kafka 证书管理" name="kafka-certs">
        <div class="toolbar-row">
          <el-button type="primary" @click="showCertUpload()">上传证书</el-button>
          <el-button @click="loadKafkaCerts">刷新</el-button>
        </div>
        <el-table :data="kafkaCerts" border class="single-line-table" style="width: 100%; margin-top: 16px;">
          <el-table-column prop="name" label="证书名称" width="200" />
          <el-table-column prop="created_at" label="上传时间" width="180" />
          <el-table-column label="操作" width="120" fixed="right" align="left">
            <template #default="{ row }">
              <el-button link type="danger" @click="deleteKafkaCert(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="数据构造任务" name="tasks">
        <div class="toolbar-row">
          <el-button type="primary" @click="showTaskDialog()">新增任务</el-button>
          <el-button @click="loadTasks">刷新</el-button>
        </div>
        <el-table :data="tasks" border class="single-line-table" style="width: 100%; margin-top: 16px;">
          <el-table-column prop="name" label="任务名" min-width="220" show-overflow-tooltip />
          <el-table-column prop="task_type" label="类型" width="100" />
          <el-table-column prop="cron_expr" label="Cron" width="120" show-overflow-tooltip />
          <el-table-column prop="batch_size" label="每批条数" width="90" />
          <el-table-column prop="agent_name" label="Agent" min-width="200" show-overflow-tooltip />
          <el-table-column v-if="currentUser?.is_admin" prop="creator_username" label="创建者" width="100" />
          <el-table-column label="状态" width="140" min-width="140">
            <template #default="{ row }">
              <div class="status-cell">
                <span>{{ row.status === 'running' ? '运行中' : row.status === 'stopped' ? '已停止' : '已暂停' }}</span>
                <span v-if="row.status !== 'running' && row.stop_reason" class="stop-reason" :title="row.stop_reason">
                  {{ row.stop_reason }}
                </span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="340" min-width="340" fixed="right" align="left">
            <template #default="{ row }">
              <span class="op-cell">
                <el-button v-if="row.is_owner" link type="success" @click="startTask(row)" :disabled="row.status === 'running'">启动</el-button>
                <el-button v-if="row.is_owner" link type="warning" @click="stopTask(row)" :disabled="row.status !== 'running'">停止</el-button>
                <el-button link type="primary" @click="showExecutions(row)">执行记录</el-button>
                <el-button v-if="row.is_owner" link type="primary" @click="showTaskDialog(row)">编辑</el-button>
                <el-button v-if="row.is_owner" link type="danger" @click="deleteTask(row)">删除</el-button>
              </span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- Agent 弹窗 -->
    <el-dialog v-model="agentDialogVisible" :title="editingAgent ? '编辑 Agent' : '新增 Agent'" width="560px" :close-on-click-modal="false">
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
    <el-dialog v-model="checkDialogVisible" title="校验 Agent" width="400px" :close-on-click-modal="false">
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
    <el-dialog v-model="taskDialogVisible" :title="editingTask ? '编辑任务' : '新增任务'" width="900px" :close-on-click-modal="false">
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
          <el-input v-model="taskForm.cron_expr" placeholder="6 字段 Quartz 示例：0/1 * * * * ? 每秒；0 * * * * ? 每分钟" />
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
          <el-form-item label="安全协议" required>
            <el-select v-model="taskForm.kafkaSecurityProtocol" placeholder="选择协议" style="width: 100%">
              <el-option label="PLAINTEXT" value="PLAINTEXT" />
              <el-option label="SASL_PLAINTEXT" value="SASL_PLAINTEXT" />
              <el-option label="SASL_SSL" value="SASL_SSL" />
              <el-option label="SSL" value="SSL" />
            </el-select>
          </el-form-item>
          <template v-if="taskForm.kafkaSecurityProtocol && taskForm.kafkaSecurityProtocol.startsWith('SASL')">
            <el-form-item label="SASL 用户名">
              <el-input v-model="taskForm.kafkaUsername" placeholder="SASL 认证用户名" />
            </el-form-item>
            <el-form-item label="SASL 密码">
              <el-input v-model="taskForm.kafkaPassword" type="password" show-password placeholder="SASL 认证密码" />
            </el-form-item>
            <el-form-item label="SASL 机制">
              <el-select v-model="taskForm.kafkaSaslMechanism" placeholder="默认 PLAIN" style="width: 100%">
                <el-option label="PLAIN" value="PLAIN" />
                <el-option label="SCRAM-SHA-256" value="SCRAM-SHA-256" />
                <el-option label="SCRAM-SHA-512" value="SCRAM-SHA-512" />
              </el-select>
            </el-form-item>
          </template>
          <el-form-item v-if="taskForm.kafkaSecurityProtocol === 'SSL' || taskForm.kafkaSecurityProtocol === 'SASL_SSL'" label="SSL CA 证书">
            <el-select v-model="taskForm.kafkaSslCafileId" placeholder="选择已上传的证书" clearable style="width: 100%; max-width: 360px">
              <el-option v-for="c in kafkaCerts" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <div class="cert-hint">若已有证书不满足需求，可联系管理员添加</div>
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
          <div v-for="p in paramConfigList" :key="p.param" class="param-row">
            <span class="param-name">{{ p.param }}</span>
            <el-select v-model="p.type" placeholder="类型" style="width:160px">
              <el-option label="固定内容" value="fixed" />
              <el-option label="当前时间" value="current_time" />
              <el-option label="13位时间戳" value="timestamp_13" />
              <el-option label="10位时间戳" value="timestamp_10" />
              <el-option label="轮询" value="round_robin" />
              <el-option label="批次号" value="batch" />
            </el-select>
            <el-input
              v-model="p.value"
              :placeholder="paramPlaceholder(p.type)"
              :disabled="paramValueDisabled(p.type)"
              style="margin-left:8px;flex:1"
            />
            <span class="param-hint">{{ paramHint(p.type) }}</span>
          </div>
          <div class="param-doc">
            固定内容：填什么渲染什么。当前时间：默认 %Y-%m-%d %H:%M:%S，可自定义 strftime 格式。轮询：不填为本批内序号 1～每批条数；填逗号分隔值则按条轮询。批次号：任务第 N 次执行的整数。
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="taskDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitTask">确定</el-button>
      </template>
    </el-dialog>

    <!-- Kafka 证书上传弹窗 -->
    <el-dialog v-model="certUploadVisible" title="上传 Kafka 证书" width="440px" :close-on-click-modal="false">
      <el-form :model="certUploadForm" label-width="90px">
        <el-form-item label="证书名称" required>
          <el-input v-model="certUploadForm.name" placeholder="用于列表展示与选择，如：生产环境 CA" />
        </el-form-item>
        <el-form-item label="证书文件" required>
          <el-upload
            :auto-upload="false"
            :limit="1"
            :on-change="(f) => { certUploadForm.file = f?.raw }"
            accept=".pem,.crt,.cer"
          >
            <el-button type="primary">选择 .pem / .crt / .cer 文件</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="certUploadVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCertUpload">确定</el-button>
      </template>
    </el-dialog>

    <!-- 执行记录弹窗 -->
    <el-dialog v-model="executionsDialogVisible" title="执行记录" width="900px" :close-on-click-modal="false" @open="currentTaskId && loadExecutions()">
      <div class="toolbar-row executions-toolbar">
        <el-button @click="loadExecutions" :disabled="!currentTaskId">刷新</el-button>
        <el-button type="danger" @click="clearExecutions" :disabled="!currentTaskId">清空</el-button>
      </div>
      <el-table :data="executions" border max-height="400">
        <el-table-column prop="batch_no" label="批次" width="80" />
        <el-table-column prop="executed_at" label="执行时间" width="180" />
        <el-table-column prop="success" label="成功" width="70">
          <template #default="{ row }">{{ row.success ? '是' : '否' }}</template>
        </el-table-column>
        <el-table-column prop="records_count" label="条数" width="80" />
        <el-table-column prop="result_message" label="结果" min-width="200" show-overflow-tooltip />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const router = useRouter()
const route = useRoute()
const activeTab = ref('agents')
const currentUser = ref(null)
const agents = ref([])
const tasks = ref([])
const kafkaCerts = ref([])
const certUploadVisible = ref(false)
const certUploadForm = ref({ name: '', file: null })
const agentDialogVisible = ref(false)
const editingAgent = ref(null)
const agentForm = ref({ name: '', url: '', token: '', kafkaConfigStr: '' })
const checkDialogVisible = ref(false)
const checkForm = ref({ url: '', token: '' })
const checkResult = ref(null)
const taskDialogVisible = ref(false)
const editingTask = ref(null)
const taskForm = ref({
  name: '', task_type: 'kafka', cron_expr: '0/1 * * * * ?', batch_size: 1, agent_id: null,
  template_content: '',
  kafkaBootstrap: '', kafkaTopic: '', kafkaSecurityProtocol: 'PLAINTEXT',
  kafkaUsername: '', kafkaPassword: '', kafkaSaslMechanism: 'PLAIN',
  kafkaSslCafileId: null,
  chHost: 'localhost', chPort: 9000, chUser: 'default', chPassword: ''
})
const templateParams = ref([])
const paramConfigList = ref([])
const executionsDialogVisible = ref(false)
const executions = ref([])
const currentTaskId = ref(null)
let agentsPollTimer = null

const DEFAULT_CURRENT_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

function getToken() {
  try {
    return localStorage.getItem('token')
  } catch {
    return null
  }
}

function loadCurrentUser() {
  api.get('/auth/me').then(r => { if (r.success) currentUser.value = r.data }).catch(() => { currentUser.value = null })
}

const loadAgents = () => api.get('/agents').then(r => { if (r.success) agents.value = r.data })
const loadTasks = () => api.get('/data-tasks').then(r => { if (r.success) tasks.value = r.data })
const loadKafkaCerts = () => api.get('/kafka-certs').then(r => { if (r.success) kafkaCerts.value = r.data })

onMounted(() => {
  if (!getToken() || !getToken().trim()) {
    router.replace({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  loadCurrentUser()
})

onUnmounted(() => {
  if (agentsPollTimer) clearInterval(agentsPollTimer)
})

watch(activeTab, (t) => {
  if (t === 'agents') {
    loadAgents()
    if (agentsPollTimer) clearInterval(agentsPollTimer)
    agentsPollTimer = setInterval(loadAgents, 30000)
  } else {
    if (agentsPollTimer) {
      clearInterval(agentsPollTimer)
      agentsPollTimer = null
    }
    if (t === 'tasks') loadTasks()
    if (t === 'kafka-certs') loadKafkaCerts()
  }
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

function showCertUpload() {
  certUploadForm.value = { name: '', file: null }
  certUploadVisible.value = true
}

function submitCertUpload() {
  const name = (certUploadForm.value.name || '').trim()
  const file = certUploadForm.value.file
  if (!name) { ElMessage.warning('请填写证书名称'); return }
  if (!file) { ElMessage.warning('请选择证书文件'); return }
  const formData = new FormData()
  formData.append('name', name)
  formData.append('file', file)
  api.post('/kafka-certs', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
    .then(r => {
      if (r.success) { ElMessage.success('上传成功'); certUploadVisible.value = false; loadKafkaCerts() }
      else ElMessage.error(r.error || '失败')
    })
    .catch(e => ElMessage.error(e.response?.data?.error || e.message))
}

function deleteKafkaCert(row) {
  ElMessageBox.confirm('确定删除该证书？删除后使用该证书的任务将无法正常执行。', '提示', { type: 'warning' }).then(() => {
    api.delete(`/kafka-certs/${row.id}`).then(r => {
      if (r.success) { ElMessage.success('已删除'); loadKafkaCerts() }
      else ElMessage.error(r.error)
    }).catch(e => ElMessage.error(e.response?.data?.error || e.message))
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
      kafkaBootstrap: k.bootstrap_servers || '', kafkaTopic: k.topic || '',
      kafkaSecurityProtocol: k.security_protocol || 'PLAINTEXT',
      kafkaUsername: k.username || '', kafkaPassword: k.password || '', kafkaSaslMechanism: k.sasl_mechanism || 'PLAIN',
      kafkaSslCafileId: k.ssl_cafile_id ?? null,
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
      name: '', task_type: 'kafka', cron_expr: '0/1 * * * * ?', batch_size: 1, agent_id: null, template_content: '',
      kafkaBootstrap: '', kafkaTopic: '', kafkaSecurityProtocol: 'PLAINTEXT',
      kafkaUsername: '', kafkaPassword: '', kafkaSaslMechanism: 'PLAIN',
      kafkaSslCafileId: null,
      chHost: 'localhost', chPort: 9000, chUser: 'default', chPassword: ''
    }
    templateParams.value = []
    paramConfigList.value = []
  }
  loadKafkaCerts()
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

function onParamTypeChange(p, newType) {
  if (newType === 'current_time' && (p.value === '' || p.value == null)) {
    p.value = DEFAULT_CURRENT_TIME_FORMAT
  }
}

function paramPlaceholder(type) {
  const t = type || 'fixed'
  if (t === 'fixed') return '填写什么即渲染什么'
  if (t === 'current_time') return '默认 ' + DEFAULT_CURRENT_TIME_FORMAT + '，可改'
  if (t === 'round_robin') return '可选：逗号分隔多值轮询；不填则为 1～本批条数'
  if (t === 'timestamp_13' || t === 'timestamp_10' || t === 'batch') return '无需填值'
  return '值'
}

function paramValueDisabled(type) {
  return type === 'timestamp_13' || type === 'timestamp_10' || type === 'batch'
}

function paramHint(type) {
  const t = type || 'fixed'
  if (t === 'timestamp_13') return '（13 位毫秒）'
  if (t === 'timestamp_10') return '（10 位秒）'
  if (t === 'batch') return '（第 N 次执行）'
  if (t === 'round_robin') return '（本批内序号或轮询值）'
  return ''
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
      security_protocol: taskForm.value.kafkaSecurityProtocol || 'PLAINTEXT',
      username: taskForm.value.kafkaUsername?.trim() || undefined,
      password: taskForm.value.kafkaPassword?.trim() || undefined,
      sasl_mechanism: taskForm.value.kafkaSaslMechanism || 'PLAIN',
      ssl_cafile_id: taskForm.value.kafkaSslCafileId ?? undefined
    }
  } else {
    connector_config.clickhouse = {
      host: taskForm.value.chHost?.trim() || 'localhost',
      port: taskForm.value.chPort ?? 9000,
      user: taskForm.value.chUser?.trim() || 'default',
      password: (taskForm.value.chPassword != null && String(taskForm.value.chPassword).trim() !== '') ? String(taskForm.value.chPassword).trim() : ''
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
  executionsDialogVisible.value = true
  loadExecutions()
}

function loadExecutions() {
  if (!currentTaskId.value) return
  api.get(`/data-tasks/${currentTaskId.value}/executions`).then(r => {
    if (r.success) executions.value = r.data
  }).catch(() => { executions.value = [] })
}

function clearExecutions() {
  if (!currentTaskId.value) return
  ElMessageBox.confirm('确定清空该任务的全部历史执行记录吗？此操作不可恢复，请谨慎操作。清空后可减轻数据库压力。', '清空执行记录', {
    type: 'warning',
    confirmButtonText: '确定清空',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    api.delete(`/data-tasks/${currentTaskId.value}/executions`)
      .then(r => {
        if (r.success) {
          ElMessage.success('已清空')
          loadExecutions()
        } else {
          ElMessage.error(r.error || '清空失败')
        }
      })
      .catch(e => ElMessage.error(e.response?.data?.error || e.message || '清空失败'))
  }).catch(() => {})
}
</script>

<style scoped>
.data-construction-page {
  max-width: 1600px;
  margin: 0 auto;
}

.status-hint {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
}

.param-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.param-row .param-name {
  width: 100px;
  flex-shrink: 0;
}
.param-row .param-hint {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
  flex-shrink: 0;
}
.param-doc {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}

.cert-hint {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}

.toolbar-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: nowrap;
  white-space: nowrap;
}
.executions-toolbar {
  margin-bottom: 12px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.status-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.status-cell .stop-reason {
  font-size: 12px;
  color: #f56c6c;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 1920 下表格单行展开，操作列不换行 */
.single-line-table .op-cell {
  white-space: nowrap;
}
.single-line-table :deep(.el-table__cell) {
  white-space: nowrap;
}
.single-line-table :deep(.el-table__cell .el-text) {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
