# CommonUtils - 通用工具类集合

一个基于 Python Flask 后端和 Vue 3 前端的通用工具类 Web 应用，提供多种实用工具功能，支持用户登录与管理员配置。

## 功能特性

### 普通工具（无需登录）
- ⏰ **时间戳转换** - 时间戳与日期时间相互转换，支持秒级和毫秒级
- 📄 **JSON格式化校验** - JSON格式验证和美化
- 🔄 **编码转换** - 文本编码转换、Base64编解码、URL编解码
- 🔐 **文件MD5计算** - 计算文件或文本内容的MD5哈希值
- 🌐 **IP网段判断** - IP地址归属判断和网段关系检查
- ⏱️ **Cron表达式解析** - 解析Cron表达式并查看未来执行时间（支持 5 字段与 6 字段 Quartz）
- 📅 **日期格式预览** - 按 strftime 格式渲染当前时间，用于校验「当前时间」类参数格式

### 数据构造（需登录）
- 📊 **数据构造** - 定时构造 Kafka 消息 / ClickHouse 数据，模板+参数渲染，由 Agent 节点执行
  - Agent 管理：新增/编辑/删除 Agent，状态自动刷新
  - 任务管理：Kafka/ClickHouse 任务，Cron 调度，参数类型：固定内容、当前时间、时间戳、轮询、批次号等

### 用户与权限
- **注册/登录** - 用户名+密码，JWT 鉴权；数据构造相关接口需登录
- **普通用户** - 仅能查看和使用自己创建的 Agent 与任务
- **管理员** - 可查看全部 Agent/任务及创建者、用户管理、菜单管理、发布公告

### 管理员专属
- **用户管理** - 右上角用户下拉 → 用户管理：查看所有用户，设置/取消管理员
- **菜单管理** - 右上角 → 菜单管理：调整顶栏菜单顺序与是否可见
- **发布公告** - 右上角 → 发布公告：在页面顶部显示一条公告，无新公告时旧公告持续显示
- **修改密码** - 右上角用户下拉 → 修改密码（所有登录用户可用）

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

### 1. 数据库初始化（MySQL）

使用数据构造功能前，需要先准备好 MySQL。

1. **创建数据库**：
```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS common_utils DEFAULT CHARACTER SET utf8mb4;"
```

2. **配置连接**（任选其一）：
   - **环境变量**：
     ```bash
     export MYSQL_HOST=localhost
     export MYSQL_PORT=3306
     export MYSQL_USER=root
     export MYSQL_PASSWORD=your_password
     export MYSQL_DATABASE=common_utils
     ```
   - **.env 文件**（推荐，尤其 Windows）：在 `backend` 目录下新建 `.env`（可复制 `.env.example`），写入上述变量。启动时会用 `python-dotenv` 自动加载。
   - **config_local.py**：在 `backend` 目录下新建 `config_local.py`（可复制 `config_local.example.py`），例如 `MYSQL_PASSWORD = '你的密码'`，会覆盖环境变量。详见 `backend/README.md`。
   - **直接改配置**：编辑 `backend/config.py`，修改 `MYSQL_HOST`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE` 等。

3. **表结构**：后端首次启动时会自动执行 `backend/database/schema.sql` 建表（在 `python app.py` 里会调用 `init_db()`），无需手动导入。若已存在表则跳过。

### 2. 后端启动

1. 进入后端目录并安装依赖：
```bash
cd backend
pip install -r requirements.txt
```

2. （可选）配置监听地址与端口、**客户端 IP 来源**（多机访问时必看）：
   - **环境变量**：
     ```bash
     export FLASK_HOST=0.0.0.0
     export FLASK_PORT=5000
     export FLASK_DEBUG=true
     # 若前端通过反向代理（如 nginx）访问后端，必须设置真实客户端 IP 头，否则所有人会被当成同一 IP，权限错误
     export CLIENT_IP_HEADER=X-Forwarded-For
     ```
   - 在 nginx 中需设置：`proxy_set_header X-Forwarded-For $remote_addr;`
   - 或在 `backend/config.py` 中修改 `HOST`、`PORT`、`CLIENT_IP_HEADER`。

3. 启动服务：
```bash
python app.py
```

启动后：
- 服务地址：`http://<本机IP>:5000`（默认 `0.0.0.0:5000`，支持非 localhost 访问）
- 会自动执行数据库初始化（若未建表）
- 会启动内置的任务调度（用于数据构造的定时执行）

### 3. Agent 启动（仅在使用「数据构造」时需要）

Agent 是实际执行 Kafka 发送 / ClickHouse 写入的节点，可部署在与主程序相同或不同的机器上。

1. 进入 Agent 目录并安装依赖：
```bash
cd agent
pip install -r requirements.txt
```

2. 启动（默认端口 5001）：
```bash
python agent.py
```

3. **修改端口**：
```bash
python agent.py -p 5002
# 或指定 host
python agent.py --port 5002 --host 0.0.0.0
```

4. 启动后**在控制台**会输出一行 Token，例如：
```
============================================================
Agent Token (use when registering):
a1b2c3d4e5f6...
============================================================
```
- 该 Token 按本机信息生成，**每台电脑固定**，重启不变。
- 在主程序「数据构造」→「Agent 管理」→「新增 Agent」时，需填写 **Agent 的 URL** 和此 **Token**。

### 4. 前端启动

1. 进入前端目录并安装依赖：
```bash
cd frontend
npm install
```

2. 开发环境默认会把 `/api` 代理到后端，默认后端地址为 `http://localhost:5000`。若后端地址或端口不同，需修改 `frontend/vite.config.js` 中的 `server.proxy['/api'].target`，例如：
```javascript
proxy: {
  '/api': {
    target: 'http://192.168.1.100:5000',  // 改成实际后端地址
    changeOrigin: true
  }
}
```

3. 启动开发服务器（默认 `0.0.0.0:3000`，支持非 localhost 访问）：
```bash
npm run dev
```

4. 浏览器访问：`http://<本机IP>:3000`（本机可为 `http://localhost:3000`）。

### 5. 地址与端口汇总

| 模块   | 默认地址            | 配置方式 |
|--------|---------------------|----------|
| 后端   | `http://0.0.0.0:5000` | 环境变量 `FLASK_HOST`、`FLASK_PORT` 或 `backend/config.py` |
| 前端   | `http://0.0.0.0:3000` | `frontend/vite.config.js` 的 `server.port`、`server.host` |
| 前端请求后端 | `/api` → `http://localhost:5000` | `frontend/vite.config.js` 的 `server.proxy['/api'].target` |
| Agent  | `http://0.0.0.0:5001` | 启动参数 `-p/--port`、`-H/--host` |

### 6. 部署与多机访问说明

- **反向代理（如 nginx）**：若前端通过 nginx 访问后端，必须让后端拿到真实客户端 IP，否则所有人会被当成同一 IP，权限判断错误。在 nginx 中设置 `proxy_set_header X-Forwarded-For $remote_addr;`，并在后端配置 `CLIENT_IP_HEADER=X-Forwarded-For`（环境变量或 `backend/config.py`）。
- **管理员**：第一个注册用户需在数据库中手动设为管理员（`users.is_admin = 1`），或使用预留管理员账号（若在配置中设置了 `ADMIN_USERNAME`/`ADMIN_PASSWORD`，可用该账号登录后拥有管理员权限）。部署机器 IP 也可在配置中设为管理员 IP（`ADMIN_IPS`）作为兜底。

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
- `GET /api/ip/current` - 获取当前请求的客户端 IP（用于前端展示「当前访问IP」）

### Cron解析
- `POST /api/cron/parse` - 解析Cron表达式

### 日期格式预览
- `POST /api/date-format/preview` - 按 strftime 格式渲染当前时间（用于数据构造中「当前时间」参数格式校验）

### 认证（数据构造等需登录接口使用）
- `POST /api/auth/register` - 注册（用户名、密码）
- `POST /api/auth/login` - 登录（返回 JWT）
- `GET /api/auth/me` - 获取当前用户信息（需 Authorization 头）
- `POST /api/auth/change-password` - 修改密码（需登录）

### 站点配置（管理员）
- `GET /api/site/menu` - 获取顶栏菜单项（顺序、可见性）
- `PUT /api/site/menu` - 更新菜单（管理员）
- `GET /api/site/announcement` - 获取当前公告
- `POST /api/site/announcement` - 发布/清空公告（管理员）

### 数据构造（需登录）
- Agent：`GET/POST/PUT/DELETE /api/agents/*` - Agent 的增删改查与状态
- 任务：`GET/POST/PUT/DELETE /api/data-tasks/*`、`POST /api/data-tasks/:id/run-once` - 任务的增删改查与单次执行

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