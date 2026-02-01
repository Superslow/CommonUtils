# CommonUtils - 通用工具类集合

一个基于 Python Flask 后端和 Vue 3 前端的通用工具类 Web 应用，提供多种实用工具功能。

## 功能特性

- ⏰ **时间戳转换** - 时间戳与日期时间相互转换，支持秒级和毫秒级
- 📄 **JSON格式化校验** - JSON格式验证和美化
- 🔄 **编码转换** - 文本编码转换、Base64编解码、URL编解码
- 🔐 **文件MD5计算** - 计算文件或文本内容的MD5哈希值
- 🌐 **IP网段判断** - IP地址归属判断和网段关系检查
- ⏱️ **Cron表达式解析** - 解析Cron表达式并查看未来执行时间
- 📊 **数据构造** - 定时构造 Kafka 消息 / ClickHouse 数据，模板+参数渲染，由 Agent 节点执行

## 技术栈

### 后端
- Python 3.8+
- Flask - Web框架
- Flask-CORS - 跨域支持
- MySQL - 任务与 Agent 持久化
- croniter - Cron表达式解析
- PyMySQL / requests

### Agent（独立进程）
- Python 3.8+
- Flask、kafka-python、clickhouse-driver
- 启动时输出固定 Token（按本机生成），支持 `-p` 修改端口

### 前端
- Vue 3 - 前端框架
- Element Plus - UI组件库
- Vue Router - 路由管理
- Axios - HTTP客户端
- Vite - 构建工具

## 项目结构

```
CommonUtils/
├── backend/              # Python 后端
│   ├── app.py           # Flask 主应用（含任务调度）
│   ├── config.py        # 配置（MySQL、Flask、管理员 IP）
│   ├── agent_client.py  # Agent 客户端（含连接缓存）
│   ├── template_utils.py # 模板参数渲染
│   ├── database/       # MySQL 表结构与连接
│   └── requirements.txt
├── agent/               # 数据构造 Agent（独立部署）
│   ├── agent.py        # 执行 Kafka / ClickHouse
│   └── requirements.txt
├── frontend/            # Vue 前端
│   ├── src/views/      # 含数据构造、Agent 管理、各工具页
│   └── vite.config.js  # host: 0.0.0.0 支持非 localhost 访问
└── README.md
```

## 快速开始

### 后端启动

1. 进入后端目录：
```bash
cd backend
```

2. 安装Python依赖：
```bash
pip install -r requirements.txt
```

3. 启动Flask服务：
```bash
python app.py
```

后端服务将在 `http://0.0.0.0:5000` 启动（支持非 localhost 访问）。需先创建 MySQL 数据库 `common_utils` 并配置 `backend/config.py` 或环境变量（MYSQL_*）。

### 前端启动

1. 进入前端目录：
```bash
cd frontend
```

2. 安装Node.js依赖：
```bash
npm install
```

3. 启动开发服务器：
```bash
npm run dev
```

前端应用将在 `http://localhost:3000` 启动

## API接口

### 时间戳转换
- `POST /api/timestamp/convert` - 转换时间戳
- `GET /api/timestamp/current` - 获取当前时间戳

### JSON校验
- `POST /api/json/validate` - 校验和格式化JSON

### 编码转换
- `POST /api/encode/convert` - 编码转换（支持多种操作）

### MD5计算
- `POST /api/file/md5` - 计算文件或文本的MD5值

### IP检查
- `POST /api/ip/check` - 检查IP地址和网段关系

### Cron解析
- `POST /api/cron/parse` - 解析Cron表达式

### 健康检查
- `GET /api/health` - 服务健康检查

## 使用示例

### 时间戳转换
输入时间戳（秒或毫秒），自动转换为多种日期时间格式。

### JSON格式化
输入JSON字符串，自动验证格式并美化输出。

### 编码转换
支持UTF-8、GBK、GB2312等编码之间的转换，以及Base64和URL编解码。

### MD5计算
支持文件上传或文本输入，计算MD5哈希值。

### IP网段判断
输入IP地址和可选网段（CIDR格式），判断IP归属和网段关系。

### Cron表达式解析
输入Cron表达式，查看未来执行时间和表达式说明。

## 开发说明

### 后端开发
- 使用Flask开发RESTful API
- 支持CORS跨域请求
- 统一的JSON响应格式

### 前端开发
- 使用Vue 3 Composition API
- Element Plus组件库
- 响应式设计，支持移动端

## 许可证

MIT License