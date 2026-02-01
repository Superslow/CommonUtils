"""
应用配置
"""
import os
import socket


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


# MySQL配置
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'common_utils')

# Flask配置
DEBUG = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
HOST = os.getenv('FLASK_HOST', '0.0.0.0')
PORT = int(os.getenv('FLASK_PORT', 5000))

# 管理员IP：部署机器所在 IP（从本机或部署机 IP 访问可管理所有 Agent/任务）+ 数据库 admin_ips 表
DEFAULT_ADMIN_IPS = ['127.0.0.1', '::1']
DEPLOYMENT_IPS = get_deployment_ips()
