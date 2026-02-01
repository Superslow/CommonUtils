"""
数据库连接和初始化
"""
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE,
    DEFAULT_ADMIN_IPS, DEPLOYMENT_IPS,
    ADMIN_USERNAME, ADMIN_PASSWORD,
)
from werkzeug.security import generate_password_hash, check_password_hash

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
                    try:
                        cursor.execute(stmt)
                    except pymysql.err.OperationalError as e:
                        if e.args[0] != 1050:  # table already exists
                            raise
        conn.commit()
        migrate_db(conn)
        ensure_admin_user(conn)
    finally:
        conn.close()


def migrate_db(conn=None):
    """为已有表添加 creator_user_id 等列（若不存在）"""
    close_conn = conn is None
    if conn is None:
        conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS n FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'agents' AND COLUMN_NAME = 'creator_user_id'",
                (MYSQL_DATABASE,)
            )
            if cursor.fetchone()['n'] == 0:
                cursor.execute('ALTER TABLE agents ADD COLUMN creator_user_id INT NULL COMMENT "创建者用户ID" AFTER token')
                cursor.execute("ALTER TABLE agents MODIFY COLUMN creator_ip VARCHAR(45) NULL COMMENT '创建者IP（审计）'")
            cursor.execute(
                "SELECT COUNT(*) AS n FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'data_tasks' AND COLUMN_NAME = 'creator_user_id'",
                (MYSQL_DATABASE,)
            )
            if cursor.fetchone()['n'] == 0:
                cursor.execute('ALTER TABLE data_tasks ADD COLUMN creator_user_id INT NULL COMMENT "创建者用户ID" AFTER connector_config')
                cursor.execute("ALTER TABLE data_tasks MODIFY COLUMN creator_ip VARCHAR(45) NULL COMMENT '创建者IP（审计）'")
            cursor.execute(
                "SELECT COUNT(*) AS n FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'site_config'",
                (MYSQL_DATABASE,)
            )
            if cursor.fetchone()['n'] == 0:
                cursor.execute("""
                    CREATE TABLE site_config (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        config_key VARCHAR(64) NOT NULL UNIQUE,
                        config_value TEXT,
                        updated_at DATETIME NULL DEFAULT NULL,
                        INDEX idx_config_key (config_key)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8
                """)
        conn.commit()
    finally:
        if close_conn:
            conn.close()


def ensure_admin_user(conn=None):
    """确保预留管理员账号存在"""
    close_conn = conn is None
    if conn is None:
        conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT id, password_hash FROM users WHERE username = %s', (ADMIN_USERNAME,))
            row = cursor.fetchone()
            if row:
                return
            pw_hash = generate_password_hash(ADMIN_PASSWORD, method='pbkdf2:sha256')
            cursor.execute(
                'INSERT INTO users (username, password_hash, is_admin) VALUES (%s, %s, 1)',
                (ADMIN_USERNAME, pw_hash)
            )
        conn.commit()
    finally:
        if close_conn:
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
