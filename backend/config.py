"""
应用配置
"""
import os

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

# 管理员IP列表（可修改/删除所有资源，可通过数据库动态配置）
DEFAULT_ADMIN_IPS = ['127.0.0.1', '::1']
