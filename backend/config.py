"""
应用配置
Windows 下系统环境变量常不生效，优先从 .env 或 config_local.py 读取。
"""
import os
import sys
import socket
from pathlib import Path

# 1) 优先加载 .env 到 os.environ（Windows 下最可靠：在 backend 目录建 .env 写 MYSQL_PASSWORD=xxx）
_CONFIG_DIR = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    _env_path = _CONFIG_DIR / '.env'
    load_dotenv(_env_path)
except ImportError:
    pass


def _env_str(key, default=''):
    """从环境变量读取字符串，兼容 Windows：去除首尾空格、\\r\\n 等换行符。"""
    val = os.environ.get(key)  # 与 getenv 等价，确保读到 dotenv 注入的值
    if val is None:
        return default
    if not isinstance(val, str):
        return str(val).strip()
    # 去除 Windows 换行符和首尾空格
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

# 2) 可选：config_local.py 覆盖（Windows 下环境变量仍不生效时，在 backend 下建 config_local.py 写 MYSQL_PASSWORD='xxx'）
_local_py = _CONFIG_DIR / 'config_local.py'
if _local_py.exists():
    try:
        import importlib.util
        _spec = importlib.util.spec_from_file_location('config_local', _local_py)
        if _spec and _spec.loader:
            _local = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_local)
            for _name in (
                'MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE',
                'HOST', 'PORT', 'DEBUG', 'ADMIN_USERNAME', 'ADMIN_PASSWORD', 'JWT_SECRET', 'JWT_EXPIRE_DAYS',
                'CLIENT_IP_HEADER',
            ):
                if hasattr(_local, _name):
                    _v = getattr(_local, _name)
                    if _name in ('MYSQL_PORT', 'PORT', 'JWT_EXPIRE_DAYS'):
                        globals()[_name] = int(_v) if _v is not None else globals()[_name]
                    elif _v is not None:
                        globals()[_name] = _v
    except Exception:
        pass
