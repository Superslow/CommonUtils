"""
应用配置
"""
import os
import socket


def _env_str(key, default=''):
    """从环境变量读取字符串，兼容 Windows：去除首尾空格、\\r\\n 等换行符。"""
    val = os.getenv(key)
    if val is None:
        return default
    if not isinstance(val, str):
        return default
    # 去除 Windows 换行符和首尾空格，避免 .env 或 set 带入的 \\r\\n 导致密码错误
    return val.replace('\r', '').replace('\n', '').strip() or default


def _env_int(key, default=0):
    """从环境变量读取整数。"""
    s = _env_str(key, str(default))
    try:
        return int(s) if s else default
    except ValueError:
        return default


def get_deployment_ips():
    """获取当前部署机器所在 IP 列表，从本机访问或从部署机 IP 访问的用户视为管理员"""
    ips = ['127.0.0.1', '::1']
    try:
        hostname = socket.gethostname()
        for addr in socket.gethostbyname_ex(hostname)[2]:
            if addr and addr not in ips:
                ips.append(addr)
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            primary = s.getsockname()[0]
            if primary and primary not in ips:
                ips.append(primary)
        finally:
            s.close()
    except Exception:
        pass
    return ips


# MySQL配置（Windows 下环境变量可能带换行/空格，统一用 _env_str 规范化）
MYSQL_HOST = _env_str('MYSQL_HOST', 'localhost')
MYSQL_PORT = _env_int('MYSQL_PORT', 3306)
MYSQL_USER = _env_str('MYSQL_USER', 'root')
MYSQL_PASSWORD = _env_str('MYSQL_PASSWORD', '')
MYSQL_DATABASE = _env_str('MYSQL_DATABASE', 'common_utils')

# Flask配置
DEBUG = _env_str('FLASK_DEBUG', 'true').lower() == 'true'
HOST = _env_str('FLASK_HOST', '0.0.0.0')
PORT = _env_int('FLASK_PORT', 5000)

# 客户端 IP 来源（反向代理场景下必须设置，否则所有请求会被视为来自代理 IP，权限会错误）
# 例如 nginx: proxy_set_header X-Forwarded-For $remote_addr; 则设为 X-Forwarded-For
CLIENT_IP_HEADER = _env_str('CLIENT_IP_HEADER') or None

# 管理员IP：部署机器所在 IP（从本机或部署机 IP 访问可管理所有 Agent/任务）+ 数据库 admin_ips 表
DEFAULT_ADMIN_IPS = ['127.0.0.1', '::1']
DEPLOYMENT_IPS = get_deployment_ips()

# 用户登录：预留管理员账号（首次启动时创建，若已存在则跳过）
ADMIN_USERNAME = _env_str('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = _env_str('ADMIN_PASSWORD', 'admin123')

# JWT 密钥（生产环境务必设置环境变量）
JWT_SECRET = _env_str('JWT_SECRET', 'common-utils-jwt-secret-change-in-production')
JWT_EXPIRE_DAYS = _env_int('JWT_EXPIRE_DAYS', 7)
