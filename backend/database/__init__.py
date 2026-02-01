"""
数据库模块
"""
from .db import get_db, init_db, is_admin_ip

__all__ = ['get_db', 'init_db', 'is_admin_ip']
