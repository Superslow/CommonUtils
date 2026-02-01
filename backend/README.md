# 后端服务

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置（含数据库密码）

**Windows 下系统环境变量常不生效**，建议用下面两种方式之一：

### 方式一：.env 文件（推荐）

在 `backend` 目录下新建 `.env` 文件（可复制 `.env.example` 后改名），内容示例：

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的数据库密码
MYSQL_DATABASE=common_utils
```

启动时会自动用 `python-dotenv` 加载，无需再设系统环境变量。

### 方式二：config_local.py

在 `backend` 目录下新建 `config_local.py`（可复制 `config_local.example.py` 后改名），内容示例：

```python
MYSQL_PASSWORD = '你的数据库密码'
# 其他可选：MYSQL_HOST, MYSQL_USER, MYSQL_DATABASE, ADMIN_USERNAME, ADMIN_PASSWORD, JWT_SECRET 等
```

会覆盖默认及环境变量中的同名配置。

### 验证是否生效

在 `backend` 目录执行：

```bash
python -c "from config import MYSQL_PASSWORD; print('MYSQL_PASSWORD 已加载' if MYSQL_PASSWORD else 'MYSQL_PASSWORD 为空')"
```

若输出「MYSQL_PASSWORD 已加载」，说明配置生效。

## 启动服务

```bash
python app.py
```

服务将在 `http://localhost:5000` 启动

## API文档

所有API接口都以 `/api` 为前缀，支持跨域请求（CORS）。

### 时间戳转换
- `POST /api/timestamp/convert` - 转换时间戳为日期时间
- `GET /api/timestamp/current` - 获取当前时间戳

### JSON校验
- `POST /api/json/validate` - 校验和格式化JSON字符串

### 编码转换
- `POST /api/encode/convert` - 编码转换（支持convert、base64_encode、base64_decode、url_encode、url_decode）

### MD5计算
- `POST /api/file/md5` - 计算文件或文本的MD5值（支持文件上传或JSON传递内容）

### IP检查
- `POST /api/ip/check` - 检查IP地址和网段关系

### Cron解析
- `POST /api/cron/parse` - 解析Cron表达式并返回未来执行时间

### 健康检查
- `GET /api/health` - 服务健康检查