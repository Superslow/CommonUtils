# 后端服务

## 安装依赖

```bash
pip install -r requirements.txt
```

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