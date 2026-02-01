"""
数据库连接和初始化
"""
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, DEFAULT_ADMIN_IPS, DEPLOYMENT_IPS

_pool = None


def get_connection():
    """获取数据库连接"""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset='utf8mb4',
        cursorclass=DictCursor
    )


@contextmanager
def get_db():
    """数据库连接上下文管理器"""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """初始化数据库表"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = f.read()
            for stmt in schema.split(';'):
                stmt = stmt.strip()
                if stmt and not stmt.startswith('--'):
                    cursor.execute(stmt)
        conn.commit()
    finally:
        conn.close()


def is_admin_ip(ip, conn=None):
    """检查IP是否为管理员（部署机器所在 IP 或数据库 admin_ips 表中的 IP 均可管理所有 Agent/任务）"""
    if not ip:
        return False
    ip = str(ip).strip()
    if ip in DEFAULT_ADMIN_IPS or ip in DEPLOYMENT_IPS:
        return True
    try:
        close_conn = conn is None
        if conn is None:
            conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1 FROM admin_ips WHERE ip = %s', (ip,))
                return cursor.fetchone() is not None
        finally:
            if close_conn:
                conn.close()
    except Exception:
        return False
