"""
通用工具类Web服务
提供时间戳转换、JSON格式化校验、编码转换、文件MD5值计算、网段和IP归属关系判断、Cron表达式解析、数据构造任务等功能
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import time
import traceback
import hashlib
import base64
import ipaddress
import os
import threading
from datetime import datetime, timedelta
from functools import wraps
from croniter import croniter
import codecs
import jwt
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, is_admin_ip
from agent_client import check_agent, execute_on_agent
from template_utils import extract_params, render_kafka_messages, render_clickhouse_sqls

try:
    from config import JWT_SECRET, JWT_EXPIRE_DAYS
except ImportError:
    JWT_SECRET = 'common-utils-jwt-secret'
    JWT_EXPIRE_DAYS = 7

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 任务调度状态
_task_scheduler = None
_task_stop_flags = {}
_agent_status_thread = None
_scheduled_run_at = {}  # task_id -> next_run.timestamp()，避免同一计划时间重复调度
_scheduled_run_lock = threading.Lock()


def get_client_ip():
    """获取客户端真实 IP（用于审计等）。"""
    try:
        from config import CLIENT_IP_HEADER
        if CLIENT_IP_HEADER:
            raw = request.headers.get(CLIENT_IP_HEADER) or ''
            if raw:
                return raw.split(',')[0].strip() or request.remote_addr or '127.0.0.1'
    except Exception:
        pass
    raw = request.headers.get('X-Forwarded-For') or request.headers.get('X-Real-IP') or request.remote_addr or ''
    return raw.split(',')[0].strip() or '127.0.0.1'


def get_current_user():
    """从 Authorization: Bearer <token> 解析出当前用户，无效或缺失返回 None"""
    auth = request.headers.get('Authorization')
    if not auth or not auth.startswith('Bearer '):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        uid = payload.get('user_id')
        if not uid:
            return None
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT id, username, is_admin FROM users WHERE id = %s', (uid,))
                row = cur.fetchone()
        if not row:
            return None
        return {'id': row['id'], 'username': row['username'], 'is_admin': bool(row.get('is_admin'))}
    except (jwt.InvalidTokenError, jwt.ExpiredSignatureError):
        return None


def require_login(f):
    """数据构造相关接口必须登录，未登录返回 401"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': '未登录或登录已过期', 'code': 'UNAUTHORIZED'}), 401
        return f(*args, **kwargs)
    return wrapped


def can_modify_agent(agent, current_user):
    """是否允许修改/删除该 Agent：仅创建者或管理员"""
    if not current_user:
        return False
    if current_user.get('is_admin'):
        return True
    cid = agent.get('creator_user_id')
    return cid is not None and cid == current_user['id']


def can_modify_task(task, current_user):
    """是否允许修改/删除该任务：仅创建者或管理员"""
    if not current_user:
        return False
    if current_user.get('is_admin'):
        return True
    cid = task.get('creator_user_id')
    return cid is not None and cid == current_user['id']


def _make_token(user_id):
    return jwt.encode(
        {'user_id': user_id, 'exp': datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS)},
        JWT_SECRET, algorithm='HS256'
    )


# ---------- 认证 ----------
@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    """用户注册（用户名+密码）"""
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or len(username) < 2:
        return jsonify({'error': '用户名至少 2 个字符'}), 400
    if not password or len(password) < 6:
        return jsonify({'error': '密码至少 6 位'}), 400
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT id FROM users WHERE username = %s', (username,))
                if cur.fetchone():
                    return jsonify({'error': '用户名已存在'}), 400
                pw_hash = generate_password_hash(password, method='pbkdf2:sha256')
                cur.execute('INSERT INTO users (username, password_hash, is_admin) VALUES (%s, %s, 0)', (username, pw_hash))
                user_id = cur.lastrowid
        token = _make_token(user_id)
        return jsonify({
            'success': True,
            'data': {'token': token, 'user': {'id': user_id, 'username': username, 'is_admin': False}}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """用户登录（用户名+密码）"""
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({'error': '请输入用户名和密码'}), 400
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT id, username, password_hash, is_admin FROM users WHERE username = %s', (username,))
                row = cur.fetchone()
        if not row or not check_password_hash(row['password_hash'], password):
            return jsonify({'error': '用户名或密码错误'}), 401
        token = _make_token(row['id'])
        return jsonify({
            'success': True,
            'data': {
                'token': token,
                'user': {'id': row['id'], 'username': row['username'], 'is_admin': bool(row.get('is_admin'))}
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    """获取当前登录用户信息"""
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录', 'code': 'UNAUTHORIZED'}), 401
    return jsonify({'success': True, 'data': user})


@app.route('/api/auth/me', methods=['PUT'])
@require_login
def update_profile():
    """当前用户修改自己的用户名和/或密码。请求体：password（当前密码，必填）、username（可选）、new_password（可选，至少6位）。"""
    user = get_current_user()
    data = request.get_json() or {}
    password = (data.get('password') or '').strip()
    username = (data.get('username') or '').strip()
    new_password = data.get('new_password') or ''
    if not password:
        return jsonify({'error': '请填写当前密码以验证身份'}), 400
    if not username and not new_password:
        return jsonify({'error': '请填写新用户名和/或新密码'}), 400
    if username and len(username) < 2:
        return jsonify({'error': '用户名至少 2 个字符'}), 400
    if new_password and len(new_password) < 6:
        return jsonify({'error': '新密码至少 6 位'}), 400
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT id, username, password_hash FROM users WHERE id = %s', (user['id'],))
                row = cur.fetchone()
            if not row or not check_password_hash(row['password_hash'], password):
                return jsonify({'error': '当前密码错误'}), 400
            updates = []
            params = []
            if username and username != row['username']:
                with conn.cursor() as cur:
                    cur.execute('SELECT id FROM users WHERE username = %s AND id != %s', (username, user['id']))
                    if cur.fetchone():
                        return jsonify({'error': '用户名已被占用'}), 400
                updates.append('username = %s')
                params.append(username)
            if new_password:
                pw_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
                updates.append('password_hash = %s')
                params.append(pw_hash)
            if updates:
                params.append(user['id'])
                with conn.cursor() as cur:
                    cur.execute('UPDATE users SET ' + ', '.join(updates) + ' WHERE id = %s', params)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/users', methods=['GET'])
@require_login
def list_users():
    """用户列表（仅管理员）"""
    user = get_current_user()
    if not user.get('is_admin'):
        return jsonify({'error': '无权限'}), 403
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT id, username, is_admin, created_at FROM users ORDER BY id')
                rows = cur.fetchall()
        users = []
        for r in rows:
            u = dict(r)
            u['created_at'] = u['created_at'].isoformat() if u.get('created_at') else None
            users.append(u)
        return jsonify({'success': True, 'data': users})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/<int:uid>', methods=['PUT'])
@require_login
def update_user(uid):
    """管理员修改用户（目前仅支持设置/取消管理员）"""
    user = get_current_user()
    if not user.get('is_admin'):
        return jsonify({'error': '无权限'}), 403
    data = request.get_json() or {}
    is_admin = data.get('is_admin')
    if is_admin is None:
        return jsonify({'error': '缺少 is_admin 参数'}), 400
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT id FROM users WHERE id = %s', (uid,))
                if not cur.fetchone():
                    return jsonify({'error': '用户不存在'}), 404
                cur.execute('UPDATE users SET is_admin = %s WHERE id = %s', (1 if is_admin else 0, uid))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------- 站点配置：菜单、公告（管理员可改） ----------
DEFAULT_MENU_ITEMS = [
    {'label': '首页', 'path': '/', 'sort_order': 0, 'visible': True},
    {'label': '时间戳转换', 'path': '/timestamp', 'sort_order': 1, 'visible': True},
    {'label': 'JSON校验', 'path': '/json', 'sort_order': 2, 'visible': True},
    {'label': '编码转换', 'path': '/encode', 'sort_order': 3, 'visible': True},
    {'label': 'MD5计算', 'path': '/md5', 'sort_order': 4, 'visible': True},
    {'label': 'IP网段', 'path': '/ip', 'sort_order': 5, 'visible': True},
    {'label': 'Cron解析', 'path': '/cron', 'sort_order': 6, 'visible': True},
    {'label': '日期格式', 'path': '/date-format', 'sort_order': 7, 'visible': True},
    {'label': '数据构造', 'path': '/data-construction', 'sort_order': 8, 'visible': True},
]


def _get_site_config(key, default=None):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT config_value FROM site_config WHERE config_key = %s', (key,))
                row = cur.fetchone()
        if row and row.get('config_value'):
            return json.loads(row['config_value'])
    except Exception:
        pass
    return default


def _set_site_config(key, value):
    val_str = json.dumps(value, ensure_ascii=False)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO site_config (config_key, config_value, updated_at) VALUES (%s, %s, NOW()) '
                'ON DUPLICATE KEY UPDATE config_value = VALUES(config_value), updated_at = NOW()',
                (key, val_str)
            )
        conn.commit()


@app.route('/api/site/menu', methods=['GET'])
def get_site_menu():
    """获取菜单配置（顺序、是否可见），不需登录。与默认菜单合并，确保首页等默认项始终存在且可编辑/移动。"""
    stored = _get_site_config('menu_items') or []
    by_path = {it.get('path'): it for it in stored if isinstance(it, dict) and it.get('path')}
    result = []
    for i, d in enumerate(DEFAULT_MENU_ITEMS):
        path = d.get('path')
        s = by_path.get(path)
        if s is not None:
            result.append({
                'label': s.get('label') or d.get('label'),
                'path': path,
                'sort_order': s.get('sort_order', i),
                'visible': s.get('visible', True)
            })
        else:
            result.append({
                'label': d.get('label'),
                'path': path,
                'sort_order': d.get('sort_order', i),
                'visible': d.get('visible', True)
            })
    for path, s in by_path.items():
        if not any(r['path'] == path for r in result):
            result.append({
                'label': s.get('label', path),
                'path': path,
                'sort_order': s.get('sort_order', 999),
                'visible': s.get('visible', True)
            })
    result.sort(key=lambda x: (x.get('sort_order', 999), x.get('path', '')))
    return jsonify({'success': True, 'data': result})


@app.route('/api/site/menu', methods=['PUT'])
@require_login
def update_site_menu():
    """管理员更新菜单（顺序、是否可见）"""
    user = get_current_user()
    if not user.get('is_admin'):
        return jsonify({'error': '无权限'}), 403
    data = request.get_json()
    items = data.get('items') if isinstance(data, dict) else data
    if not isinstance(items, list):
        return jsonify({'error': '缺少 items 数组'}), 400
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            continue
        it['sort_order'] = it.get('sort_order', i)
        it['visible'] = it.get('visible', True)
    _set_site_config('menu_items', items)
    return jsonify({'success': True})


@app.route('/api/site/announcement', methods=['GET'])
def get_site_announcement():
    """获取当前公告（不需登录）；无新公告时旧公告一直显示"""
    obj = _get_site_config('announcement')
    if not obj or not obj.get('content'):
        return jsonify({'success': True, 'data': None})
    return jsonify({'success': True, 'data': {'content': obj.get('content'), 'updated_at': obj.get('updated_at')}})


@app.route('/api/site/announcement', methods=['POST'])
@require_login
def update_site_announcement():
    """管理员发布公告（一条；不发布新公告则旧公告继续显示）"""
    user = get_current_user()
    if not user.get('is_admin'):
        return jsonify({'error': '无权限'}), 403
    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    obj = {'content': content, 'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    _set_site_config('announcement', obj)
    return jsonify({'success': True, 'data': obj})


@app.route('/api/timestamp/convert', methods=['POST'])
def timestamp_convert():
    """时间戳转换"""
    try:
        data = request.get_json()
        timestamp = data.get('timestamp')
        
        if timestamp is None:
            return jsonify({'error': '缺少timestamp参数'}), 400
        
        # 判断是秒级还是毫秒级时间戳
        if len(str(timestamp)) > 10:
            timestamp = timestamp / 1000
        
        dt = datetime.fromtimestamp(timestamp)
        
        result = {
            'timestamp': int(timestamp),
            'timestamp_ms': int(timestamp * 1000),
            'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'),
            'date': dt.strftime('%Y-%m-%d'),
            'time': dt.strftime('%H:%M:%S'),
            'iso': dt.isoformat(),
            'weekday': dt.strftime('%A'),
            'weekday_cn': ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'][dt.weekday()],
        }
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/date-format/preview', methods=['POST'])
def date_format_preview():
    """按 strftime 格式渲染当前时间，用于校验「当前时间」参数格式是否预期（普通工具，不需登录）"""
    try:
        data = request.get_json() or {}
        fmt = (data.get('format') or '').strip() or '%Y-%m-%d %H:%M:%S'
        formatted = datetime.now().strftime(fmt)
        return jsonify({'success': True, 'data': {'format': fmt, 'formatted': formatted}})
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'格式无效: {e}'}), 400


@app.route('/api/timestamp/current', methods=['GET'])
def current_timestamp():
    """获取当前时间戳"""
    now = time.time()
    dt = datetime.now()
    return jsonify({
        'success': True,
        'data': {
            'timestamp': int(now),
            'timestamp_ms': int(now * 1000),
            'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'),
            'iso': dt.isoformat()
        }
    })


@app.route('/api/json/validate', methods=['POST'])
def json_validate():
    """JSON格式化校验"""
    try:
        data = request.get_json()
        json_str = data.get('json')
        
        if json_str is None:
            return jsonify({'error': '缺少json参数'}), 400
        
        # 尝试解析JSON
        try:
            parsed = json.loads(json_str)
            formatted = json.dumps(parsed, ensure_ascii=False, indent=2)
            
            return jsonify({
                'success': True,
                'data': {
                    'valid': True,
                    'formatted': formatted,
                    'type': type(parsed).__name__,
                    'size': len(json_str)
                }
            })
        except json.JSONDecodeError as e:
            return jsonify({
                'success': True,
                'data': {
                    'valid': False,
                    'error': str(e),
                    'error_line': getattr(e, 'lineno', None),
                    'error_col': getattr(e, 'colno', None)
                }
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/encode/convert', methods=['POST'])
def encode_convert():
    """编码转换"""
    try:
        data = request.get_json()
        text = data.get('text')
        from_encoding = data.get('from_encoding', 'utf-8')
        to_encoding = data.get('to_encoding', 'utf-8')
        operation = data.get('operation', 'convert')
        
        if text is None:
            return jsonify({'error': '缺少text参数'}), 400
        
        result = {}
        
        if operation == 'convert':
            try:
                decoded = text.encode(from_encoding) if isinstance(text, str) else text
                if from_encoding.lower() != 'utf-8':
                    decoded = codecs.decode(decoded, from_encoding)
                encoded = codecs.encode(decoded, to_encoding)
                result = {
                    'original': text,
                    'from_encoding': from_encoding,
                    'to_encoding': to_encoding,
                    'converted': encoded.decode('latin1') if to_encoding.lower() != 'utf-8' else encoded.decode('utf-8'),
                    'hex': encoded.hex()
                }
            except Exception as e:
                return jsonify({'error': f'编码转换失败: {str(e)}'}), 400
        
        elif operation == 'base64_encode':
            encoded = base64.b64encode(text.encode('utf-8')).decode('utf-8')
            result = {
                'original': text,
                'encoded': encoded
            }
        
        elif operation == 'base64_decode':
            try:
                decoded = base64.b64decode(text).decode('utf-8')
                result = {
                    'original': text,
                    'decoded': decoded
                }
            except Exception as e:
                return jsonify({'error': f'Base64解码失败: {str(e)}'}), 400
        
        elif operation == 'url_encode':
            import urllib.parse
            encoded = urllib.parse.quote(text, safe='')
            result = {
                'original': text,
                'encoded': encoded
            }
        
        elif operation == 'url_decode':
            import urllib.parse
            try:
                decoded = urllib.parse.unquote(text)
                result = {
                    'original': text,
                    'decoded': decoded
                }
            except Exception as e:
                return jsonify({'error': f'URL解码失败: {str(e)}'}), 400
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/file/md5', methods=['POST'])
def file_md5():
    """文件MD5值计算"""
    try:
        if 'file' not in request.files:
            data = request.get_json()
            if data and 'content' in data:
                content = data['content']
                if isinstance(content, str):
                    content = content.encode('utf-8')
                md5_hash = hashlib.md5(content).hexdigest()
                return jsonify({
                    'success': True,
                    'data': {
                        'md5': md5_hash,
                        'size': len(content)
                    }
                })
            return jsonify({'error': '缺少file参数或content参数'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '未选择文件'}), 400
        
        md5_hash = hashlib.md5()
        while True:
            chunk = file.read(8192)
            if not chunk:
                break
            md5_hash.update(chunk)
        
        file.seek(0)
        file_size = len(file.read())
        
        return jsonify({
            'success': True,
            'data': {
                'filename': file.filename,
                'md5': md5_hash.hexdigest(),
                'size': file_size
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ip/current', methods=['GET'])
def ip_current():
    """返回当前请求的客户端 IP（后端识别，用于权限判断的同一来源）"""
    return jsonify({'ip': get_client_ip() or ''})


@app.route('/api/ip/check', methods=['POST'])
def ip_check():
    """网段和IP归属关系判断"""
    try:
        data = request.get_json()
        ip = data.get('ip')
        network = data.get('network')
        
        if ip is None:
            return jsonify({'error': '缺少ip参数'}), 400
        
        result = {
            'ip': ip,
            'valid': False,
            'is_private': False,
            'is_public': False,
            'is_multicast': False,
            'is_reserved': False,
            'version': None,
            'in_network': None
        }
        
        try:
            ip_obj = ipaddress.ip_address(ip)
            result['valid'] = True
            result['version'] = ip_obj.version
            result['is_private'] = ip_obj.is_private
            result['is_public'] = ip_obj.is_global
            result['is_multicast'] = ip_obj.is_multicast
            result['is_reserved'] = ip_obj.is_reserved
            
            if network:
                try:
                    network_obj = ipaddress.ip_network(network, strict=False)
                    result['in_network'] = ip_obj in network_obj
                    result['network'] = str(network_obj)
                    result['network_address'] = str(network_obj.network_address)
                    result['broadcast_address'] = str(network_obj.broadcast_address)
                    result['netmask'] = str(network_obj.netmask)
                    result['hostmask'] = str(network_obj.hostmask)
                    result['num_addresses'] = network_obj.num_addresses
                except ValueError as e:
                    result['network_error'] = str(e)
        except ValueError as e:
            result['error'] = str(e)
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _normalize_cron_to_croniter(cron_expr):
    """
    将 Cron 表达式转为 croniter 可用的格式。
    - 5 字段：分 时 日 月 周，直接返回。
    - 6 字段（Quartz）：秒 分 时 日 月 周，转为 croniter 的 6 字段：分 时 日 月 周 秒，? 转为 *。
    """
    parts = cron_expr.strip().split()
    if len(parts) == 5:
        return cron_expr.strip()
    if len(parts) == 6:
        # Quartz: sec min hour day month dow -> croniter: min hour day month dow sec（croniter 秒在最后）
        sec, minute, hour, day, month, dow = parts
        def q(s):
            return '*' if s == '?' else s
        return ' '.join([q(minute), q(hour), q(day), q(month), q(dow), q(sec)])
    return None


@app.route('/api/cron/parse', methods=['POST'])
def cron_parse():
    """Cron表达式解析（支持 5 字段标准格式与 6 字段 Quartz 格式，如 0 * * * * ?）"""
    try:
        data = request.get_json()
        cron_expr = data.get('cron')
        count = data.get('count', 10)
        
        if cron_expr is None:
            return jsonify({'error': '缺少cron参数'}), 400
        
        try:
            normalized = _normalize_cron_to_croniter(cron_expr)
            if normalized is None:
                raise ValueError('Cron 表达式须为 5 字段（分 时 日 月 周）或 6 字段 Quartz（秒 分 时 日 月 周）')
            
            base_time = datetime.now()
            cron = croniter(normalized, base_time)
            
            parts = cron_expr.strip().split()
            field_names = ['minute', 'hour', 'day', 'month', 'weekday'] if len(parts) == 5 else ['second', 'minute', 'hour', 'day', 'month', 'weekday']
            fields = dict(zip(field_names, parts))
            
            next_times = []
            for i in range(count):
                next_time = cron.get_next(datetime)
                next_times.append({
                    'time': next_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'timestamp': int(next_time.timestamp()),
                    'weekday': next_time.strftime('%A'),
                    'weekday_cn': ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'][next_time.weekday()]
                })
            
            result = {
                'cron': cron_expr,
                'valid': True,
                'fields': fields,
                'next_times': next_times,
                'description': get_cron_description(cron_expr)
            }
            
            return jsonify({'success': True, 'data': result})
        except Exception as e:
            return jsonify({
                'success': True,
                'data': {
                    'cron': cron_expr,
                    'valid': False,
                    'error': str(e)
                }
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def get_cron_description(cron_expr):
    """获取Cron表达式的描述（支持 5 或 6 字段）"""
    parts = cron_expr.strip().split()
    if len(parts) not in (5, 6):
        return '无效的Cron表达式'
    
    # 6 字段 Quartz：秒 分 时 日 月 周
    if len(parts) == 6:
        sec, minute, hour, day, month, dow = parts
        desc_sec = f'第{sec}秒' if sec != '*' and sec != '?' else '每秒'
        minute = '*' if minute == '?' else minute
        hour = '*' if hour == '?' else hour
        day = '*' if day == '?' else day
        month = '*' if month == '?' else month
        dow = '*' if dow == '?' else dow
    else:
        minute, hour, day, month, dow = parts
        desc_sec = ''
    
    descriptions = []
    if desc_sec:
        descriptions.append(desc_sec)
    
    if minute == '*':
        descriptions.append('每分钟')
    elif '/' in minute:
        interval = minute.split('/')[1]
        descriptions.append(f'每{interval}分钟')
    else:
        descriptions.append(f'在{minute}分')
    
    if hour == '*':
        descriptions.append('每小时')
    elif '/' in hour:
        interval = hour.split('/')[1]
        descriptions.append(f'每{interval}小时')
    else:
        descriptions.append(f'在{hour}时')
    
    if day == '*':
        descriptions.append('每天')
    elif '/' in day:
        interval = day.split('/')[1]
        descriptions.append(f'每{interval}天')
    else:
        descriptions.append(f'在{day}日')
    
    if month == '*':
        descriptions.append('每月')
    elif '/' in month:
        interval = month.split('/')[1]
        descriptions.append(f'每{interval}月')
    else:
        descriptions.append(f'在{month}月')
    
    weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
    if dow == '*':
        descriptions.append('每周')
    elif dow.isdigit():
        day_num = int(dow)
        if 0 <= day_num <= 6:
            descriptions.append(f'在{weekdays[day_num]}')
    else:
        descriptions.append(f'在{dow}')
    
    return ' '.join(descriptions)


# ---------- Agent 管理（需登录） ----------
def _ensure_agent_status_refresh_started():
    """确保 Agent 状态刷新线程已启动（首次请求时启动，兼容 gunicorn）"""
    global _agent_status_thread
    if _agent_status_thread is None or not _agent_status_thread.is_alive():
        start_agent_status_refresh()


@app.route('/api/agents', methods=['GET'])
@require_login
def list_agents():
    """Agent 列表：普通用户仅自己的，管理员全部；状态由后台定时刷新"""
    _ensure_agent_status_refresh_started()
    user = get_current_user()
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                if user.get('is_admin'):
                    cur.execute('''
                        SELECT a.id, a.name, a.url, a.creator_ip, a.creator_user_id, a.status, a.last_check_at, a.kafka_config, a.created_at,
                               u.username AS creator_username
                        FROM agents a
                        LEFT JOIN users u ON a.creator_user_id = u.id
                        ORDER BY a.id
                    ''')
                else:
                    cur.execute('''
                        SELECT id, name, url, creator_ip, creator_user_id, status, last_check_at, kafka_config, created_at
                        FROM agents WHERE creator_user_id = %s ORDER BY id
                    ''', (user['id'],))
                rows = cur.fetchall()
        agents = []
        for r in rows:
            item = dict(r)
            item['is_owner'] = can_modify_agent(item, user)
            item['creator_username'] = item.get('creator_username')  # 仅管理员列表有
            item['last_check_at'] = item['last_check_at'].isoformat() if item.get('last_check_at') else None
            if item.get('kafka_config') and isinstance(item['kafka_config'], str):
                try:
                    item['kafka_config'] = json.loads(item['kafka_config'])
                except Exception:
                    pass
            agents.append(item)
        return jsonify({'success': True, 'data': agents})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/agents', methods=['POST'])
@require_login
def create_agent():
    """新增 Agent"""
    user = get_current_user()
    client_ip = get_client_ip()
    data = request.get_json()
    name = data.get('name')
    url = data.get('url')
    token = data.get('token')
    kafka_config = data.get('kafka_config')
    if not name or not url or not token:
        return jsonify({'error': '缺少name/url/token'}), 400
    ok, _ = check_agent(url, token)
    if not ok:
        return jsonify({'error': 'Agent不可用或Token错误'}), 400
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO agents (name, url, token, creator_user_id, creator_ip, status, kafka_config) VALUES (%s,%s,%s,%s,%s,%s,%s)',
                    (name, url.rstrip('/'), token, user['id'], client_ip, 'online', json.dumps(kafka_config) if kafka_config else None)
                )
                agent_id = cur.lastrowid
        return jsonify({'success': True, 'data': {'id': agent_id}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/agents/<int:aid>', methods=['PUT'])
@require_login
def update_agent(aid):
    """更新 Agent（仅管理员或创建者）"""
    user = get_current_user()
    data = request.get_json() or {}
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM agents WHERE id = %s', (aid,))
                agent = cur.fetchone()
            if not agent:
                return jsonify({'error': 'Agent不存在'}), 404
            if not can_modify_agent(agent, user):
                return jsonify({'error': '无权限修改'}), 403
            name = data.get('name') or agent['name']
            url = (data.get('url') or agent['url']).strip().rstrip('/')
            token = data.get('token') or agent.get('token') or ''
            kafka_config = data.get('kafka_config')
            if data.get('url') or (data.get('token') and data.get('token').strip()):
                ok, _ = check_agent(url, token)
                if not ok:
                    return jsonify({'error': 'Agent不可用或Token错误'}), 400
            kafka_val = None
            if kafka_config is not None:
                kafka_val = json.dumps(kafka_config) if isinstance(kafka_config, dict) else str(kafka_config)
            else:
                raw = agent.get('kafka_config')
                if isinstance(raw, str):
                    kafka_val = raw
                elif raw is not None:
                    kafka_val = json.dumps(raw)
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE agents SET name=%s, url=%s, token=%s, kafka_config=%s, last_check_at=NOW() WHERE id=%s',
                    (name, url, token, kafka_val, aid)
                )
            conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/agents/<int:aid>', methods=['DELETE'])
@require_login
def delete_agent(aid):
    """删除 Agent（仅管理员或创建者）"""
    user = get_current_user()
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM agents WHERE id = %s', (aid,))
                agent = cur.fetchone()
            if not agent:
                return jsonify({'error': 'Agent不存在'}), 404
            if not can_modify_agent(agent, user):
                return jsonify({'error': '无权限删除'}), 403
            with conn.cursor() as cur:
                cur.execute('DELETE FROM agents WHERE id = %s', (aid,))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/agents/check', methods=['POST'])
@require_login
def agent_check():
    """校验 Agent 是否可用（需登录）"""
    data = request.get_json()
    url = data.get('url')
    token = data.get('token')
    if not url or not token:
        return jsonify({'error': '缺少url或token'}), 400
    ok, detail = check_agent(url, token)
    return jsonify({'success': True, 'data': {'available': ok, 'detail': detail}})


# ---------- 模板参数解析（数据构造用，需登录） ----------
@app.route('/api/template/params', methods=['POST'])
@require_login
def template_params():
    """从模板中识别可变参数 {param}"""
    data = request.get_json()
    template = data.get('template', '')
    params = extract_params(template)
    return jsonify({'success': True, 'data': params})


# ---------- 数据构造任务（需登录） ----------
@app.route('/api/data-tasks', methods=['GET'])
@require_login
def list_data_tasks():
    """任务列表：普通用户仅自己的，管理员全部并显示创建者"""
    user = get_current_user()
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                if user.get('is_admin'):
                    cur.execute('''
                        SELECT t.*, a.name as agent_name, u.username as creator_username
                        FROM data_tasks t
                        LEFT JOIN agents a ON t.agent_id = a.id
                        LEFT JOIN users u ON t.creator_user_id = u.id
                        ORDER BY t.id
                    ''')
                else:
                    cur.execute('''
                        SELECT t.*, a.name as agent_name
                        FROM data_tasks t
                        LEFT JOIN agents a ON t.agent_id = a.id
                        WHERE t.creator_user_id = %s
                        ORDER BY t.id
                    ''', (user['id'],))
                rows = cur.fetchall()
        tasks = []
        for r in rows:
            item = dict(r)
            item['is_owner'] = can_modify_task(item, user)
            item['creator_username'] = item.get('creator_username')
            if item.get('param_config'):
                item['param_config'] = json.loads(item['param_config']) if isinstance(item['param_config'], str) else item['param_config']
            if item.get('connector_config'):
                item['connector_config'] = json.loads(item['connector_config']) if isinstance(item['connector_config'], str) else item['connector_config']
            tasks.append(item)
        return jsonify({'success': True, 'data': tasks})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/data-tasks', methods=['POST'])
@require_login
def create_data_task():
    """创建数据构造任务"""
    user = get_current_user()
    client_ip = get_client_ip()
    data = request.get_json()
    name = data.get('name')
    task_type = data.get('task_type')
    cron_expr = data.get('cron_expr')
    batch_size = data.get('batch_size', 1)
    agent_id = data.get('agent_id')
    template_content = data.get('template_content')
    param_config = data.get('param_config')
    connector_config = data.get('connector_config')
    if not all([name, task_type, cron_expr, agent_id, template_content]):
        return jsonify({'error': '缺少必填项'}), 400
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT id, creator_user_id FROM agents WHERE id = %s', (agent_id,))
                agent_row = cur.fetchone()
                if not agent_row:
                    return jsonify({'error': 'Agent不存在'}), 400
                if not user.get('is_admin') and agent_row.get('creator_user_id') != user['id']:
                    return jsonify({'error': '只能使用自己创建的 Agent'}), 403
                cur.execute('''
                    INSERT INTO data_tasks (name, task_type, cron_expr, batch_size, agent_id, template_content, param_config, connector_config, creator_user_id, creator_ip)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ''', (name, task_type, cron_expr, batch_size, agent_id, template_content,
                      json.dumps(param_config) if param_config else None,
                      json.dumps(connector_config) if connector_config else None,
                      user['id'], client_ip))
                task_id = cur.lastrowid
            conn.commit()
        return jsonify({'success': True, 'data': {'id': task_id}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/data-tasks/<int:tid>', methods=['PUT'])
@require_login
def update_data_task(tid):
    """更新任务（仅管理员或创建者）"""
    user = get_current_user()
    data = request.get_json()
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM data_tasks WHERE id = %s', (tid,))
                task = cur.fetchone()
            if not task:
                return jsonify({'error': '任务不存在'}), 404
            if not can_modify_task(task, user):
                return jsonify({'error': '无权限修改'}), 403
            name = data.get('name', task['name'])
            cron_expr = data.get('cron_expr', task['cron_expr'])
            batch_size = data.get('batch_size', task['batch_size'])
            agent_id = data.get('agent_id', task['agent_id'])
            template_content = data.get('template_content', task['template_content'])
            param_config = data.get('param_config', task.get('param_config'))
            connector_config = data.get('connector_config', task.get('connector_config'))
            if connector_config and isinstance(connector_config, dict):
                existing_cc = task.get('connector_config')
                if isinstance(existing_cc, str) and existing_cc:
                    try:
                        existing_cc = json.loads(existing_cc) or {}
                    except Exception:
                        existing_cc = {}
                elif not isinstance(existing_cc, dict):
                    existing_cc = {}
                existing_ch = (existing_cc or {}).get('clickhouse') or {}
                new_ch = connector_config.get('clickhouse') or {}
                new_password = new_ch.get('password')
                if new_ch and (new_password is None or (isinstance(new_password, str) and new_password.strip() == '')):
                    old_password = existing_ch.get('password')
                    if old_password is not None or (isinstance(old_password, str) and old_password.strip() != ''):
                        if 'clickhouse' not in connector_config:
                            connector_config['clickhouse'] = {}
                        connector_config['clickhouse']['password'] = old_password if old_password is not None else ''
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE data_tasks SET name=%s, cron_expr=%s, batch_size=%s, agent_id=%s,
                    template_content=%s, param_config=%s, connector_config=%s WHERE id=%s
                ''', (name, cron_expr, batch_size, agent_id, template_content,
                      json.dumps(param_config) if param_config else param_config,
                      json.dumps(connector_config) if connector_config else connector_config,
                      tid))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/data-tasks/<int:tid>', methods=['DELETE'])
@require_login
def delete_data_task(tid):
    """删除任务（仅管理员或创建者）"""
    user = get_current_user()
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM data_tasks WHERE id = %s', (tid,))
                task = cur.fetchone()
            if not task:
                return jsonify({'error': '任务不存在'}), 404
            if not can_modify_task(task, user):
                return jsonify({'error': '无权限删除'}), 403
            _task_stop_flags[tid] = True
            with conn.cursor() as cur:
                cur.execute('UPDATE data_tasks SET status=%s WHERE id=%s', ('stopped', tid))
                cur.execute('DELETE FROM data_tasks WHERE id = %s', (tid,))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/data-tasks/<int:tid>/start', methods=['POST'])
@require_login
def start_data_task(tid):
    """启动任务"""
    user = get_current_user()
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM data_tasks WHERE id = %s', (tid,))
                task = cur.fetchone()
            if not task:
                return jsonify({'error': '任务不存在'}), 404
            if not can_modify_task(task, user):
                return jsonify({'error': '无权限操作'}), 403
            with conn.cursor() as cur:
                cur.execute("UPDATE data_tasks SET status=%s, stop_reason = NULL WHERE id=%s", ('running', tid))
            conn.commit()
        _task_stop_flags[tid] = False
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/data-tasks/<int:tid>/stop', methods=['POST'])
@require_login
def stop_data_task(tid):
    """停止任务"""
    user = get_current_user()
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM data_tasks WHERE id = %s', (tid,))
                task = cur.fetchone()
            if not task:
                return jsonify({'error': '任务不存在'}), 404
            if not can_modify_task(task, user):
                return jsonify({'error': '无权限操作'}), 403
            _task_stop_flags[tid] = True
            with conn.cursor() as cur:
                cur.execute('UPDATE data_tasks SET status=%s WHERE id=%s', ('stopped', tid))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/data-tasks/<int:tid>/executions', methods=['GET'])
@require_login
def list_task_executions(tid):
    """任务执行记录"""
    user = get_current_user()
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT creator_user_id FROM data_tasks WHERE id = %s', (tid,))
                row = cur.fetchone()
            if not row:
                return jsonify({'error': '任务不存在'}), 404
            cid = row.get('creator_user_id')
            if not user.get('is_admin') and (cid is None or cid != user['id']):
                return jsonify({'error': '无权限'}), 403
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM task_executions WHERE task_id = %s ORDER BY id DESC LIMIT 100', (tid,))
                rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get('executed_at'):
                d['executed_at'] = d['executed_at'].isoformat()
            result.append(d)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/data-tasks/<int:tid>/executions', methods=['DELETE'])
@require_login
def clear_task_executions(tid):
    """清空该任务的历史执行记录（仅任务创建者或管理员）"""
    user = get_current_user()
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT creator_user_id FROM data_tasks WHERE id = %s', (tid,))
                row = cur.fetchone()
            if not row:
                return jsonify({'error': '任务不存在'}), 404
            cid = row.get('creator_user_id')
            if not user.get('is_admin') and (cid is None or cid != user['id']):
                return jsonify({'error': '无权限'}), 403
            with conn.cursor() as cur:
                cur.execute('DELETE FROM task_executions WHERE task_id = %s', (tid,))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def run_task_once(task_id, scheduled_time=None):
    """执行一次任务并记录结果。scheduled_time 为 cron 计划执行时间，用于渲染模板中的当前时间/时间戳及记录 executed_at。"""
    batch_no = 1
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM data_tasks WHERE id = %s AND status = %s', (task_id, 'running'))
                task = cur.fetchone()
            if not task or _task_stop_flags.get(task_id):
                return
            with conn.cursor() as cur:
                cur.execute('SELECT url, token FROM agents WHERE id = %s', (task['agent_id'],))
                agent = cur.fetchone()
        if not agent:
            return
        task_type = task['task_type']
        template_content = task['template_content']
        param_config = task.get('param_config')
        if isinstance(param_config, str):
            param_config = json.loads(param_config) if param_config else []
        raw_cc = task.get('connector_config')
        connector_config = {}
        if raw_cc:
            if isinstance(raw_cc, bytes):
                raw_cc = raw_cc.decode('utf-8', errors='replace')
            if isinstance(raw_cc, str):
                try:
                    connector_config = json.loads(raw_cc) or {}
                except Exception:
                    connector_config = {}
            elif isinstance(raw_cc, dict):
                connector_config = raw_cc
        batch_size = task.get('batch_size') or 1
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT COALESCE(MAX(batch_no),0) + 1 AS nb FROM task_executions WHERE task_id = %s', (task_id,))
                batch_no = cur.fetchone()['nb'] or 1
        if task_type == 'kafka':
            messages = render_kafka_messages(template_content, param_config, batch_size, batch_no, reference_time=scheduled_time)
            conn_cfg = connector_config.get('kafka') or {}
            ssl_cafile = conn_cfg.get('ssl_cafile')
            ssl_cafile_id = conn_cfg.get('ssl_cafile_id')
            if ssl_cafile_id is not None:
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute('SELECT content FROM kafka_certs WHERE id = %s', (ssl_cafile_id,))
                        row = cur.fetchone()
                if row:
                    ssl_cafile = row['content']
            task_data = {
                'bootstrap_servers': conn_cfg.get('bootstrap_servers', 'localhost:9092'),
                'topic': conn_cfg.get('topic', ''),
                'messages': messages,
                'config': {
                    'security_protocol': conn_cfg.get('security_protocol', 'PLAINTEXT'),
                    'username': conn_cfg.get('username'),
                    'password': conn_cfg.get('password'),
                    'sasl_mechanism': conn_cfg.get('sasl_mechanism', 'PLAIN'),
                    'ssl_cafile': ssl_cafile,
                }
            }
        else:
            sqls = render_clickhouse_sqls(
                json.loads(template_content) if isinstance(template_content, str) and template_content.startswith('[') else template_content,
                param_config, batch_size, batch_no, reference_time=scheduled_time)
            conn_cfg = connector_config.get('clickhouse') or {}
            ch_user = conn_cfg.get('user')
            ch_password = conn_cfg.get('password')
            ch_user = (ch_user if ch_user is not None else '') or 'default'
            ch_password = ch_password if ch_password is not None else ''
            if not isinstance(ch_user, str):
                ch_user = str(ch_user)
            if not isinstance(ch_password, str):
                ch_password = str(ch_password)
            task_data = {
                'host': conn_cfg.get('host', 'localhost'),
                'port': conn_cfg.get('port', 9000),
                'sqls': sqls,
                'config': {
                    'user': ch_user.strip() or 'default',
                    'password': ch_password
                }
            }
        result = execute_on_agent(agent['url'], agent['token'], task_type, task_data, batch_no)
        executed_at_val = scheduled_time if scheduled_time is not None else datetime.now()
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO task_executions (task_id, batch_no, success, result_message, records_count, executed_at) VALUES (%s,%s,%s,%s,%s,%s)',
                    (task_id, batch_no, 1, json.dumps(result), batch_size, executed_at_val))
            conn.commit()
    except Exception as e:
        err_msg = traceback.format_exc()
        executed_at_val = scheduled_time if scheduled_time is not None else datetime.now()
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'INSERT INTO task_executions (task_id, batch_no, success, result_message, executed_at) VALUES (%s,%s,%s,%s,%s)',
                        (task_id, batch_no, 0, err_msg, executed_at_val))
                    cur.execute(
                        'SELECT success FROM task_executions WHERE task_id = %s ORDER BY id DESC LIMIT 3',
                        (task_id,)
                    )
                    rows = cur.fetchall()
                    if len(rows) >= 3 and all(r.get('success') == 0 for r in rows):
                        cur.execute(
                            "UPDATE data_tasks SET status = 'stopped', stop_reason = %s WHERE id = %s",
                            ('连续失败超过3次，已自动停止', task_id)
                        )
        except Exception:
            pass


def _run_task_at_scheduled_time(task_id, scheduled_time):
    """在计划时间到达时执行任务，实现毫秒级准时"""
    delay = (scheduled_time - datetime.now()).total_seconds()
    if delay > 0:
        time.sleep(delay)
    try:
        run_task_once(task_id, scheduled_time=scheduled_time)
    finally:
        with _scheduled_run_lock:
            if _scheduled_run_at.get(task_id) == scheduled_time.timestamp():
                _scheduled_run_at.pop(task_id, None)


def scheduler_loop():
    """调度循环：按Cron执行运行中的任务；临近计划时间时起线程 sleep 到点再执行，实现毫秒级准时"""
    from croniter import croniter
    while True:
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT id, cron_expr FROM data_tasks WHERE status = %s', ('running',))
                    tasks = cur.fetchall()
            now = datetime.now()
            for t in tasks:
                if _task_stop_flags.get(t['id']):
                    continue
                try:
                    normalized = _normalize_cron_to_croniter(t['cron_expr'])
                    if not normalized:
                        continue
                    cron = croniter(normalized, now)
                    next_run = cron.get_next(datetime)
                    secs = (next_run - now).total_seconds()
                    if secs <= 0 or secs > 65:
                        continue
                    with _scheduled_run_lock:
                        key = next_run.timestamp()
                        if _scheduled_run_at.get(t['id']) == key:
                            continue
                        _scheduled_run_at[t['id']] = key
                    threading.Thread(
                        target=_run_task_at_scheduled_time,
                        args=(t['id'], next_run),
                        daemon=True
                    ).start()
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(1)


def start_scheduler():
    global _task_scheduler
    if _task_scheduler is None or not _task_scheduler.is_alive():
        _task_scheduler = threading.Thread(target=scheduler_loop, daemon=True)
        _task_scheduler.start()


def refresh_all_agents_status_loop():
    """后台线程：每分钟刷新所有 Agent 的在线状态"""
    while True:
        try:
            time.sleep(60)
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT id, url, token FROM agents')
                    rows = cur.fetchall()
            for r in rows:
                try:
                    ok, _ = check_agent(r['url'], r['token'])
                    status = 'online' if ok else 'offline'
                except Exception:
                    status = 'offline'
                try:
                    with get_db() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                'UPDATE agents SET status = %s, last_check_at = NOW() WHERE id = %s',
                                (status, r['id'])
                            )
                except Exception:
                    pass
        except Exception:
            pass


def start_agent_status_refresh():
    """启动 Agent 状态定时刷新线程"""
    global _agent_status_thread
    if _agent_status_thread is None or not _agent_status_thread.is_alive():
        _agent_status_thread = threading.Thread(target=refresh_all_agents_status_loop, daemon=True)
        _agent_status_thread.start()


# ---------- Kafka 证书管理 ----------
@app.route('/api/kafka-certs', methods=['GET'])
@require_login
def list_kafka_certs():
    """Kafka 证书列表（仅 id/name/created_at，不含内容）"""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT id, name, created_at FROM kafka_certs ORDER BY id')
                rows = cur.fetchall()
        items = [{'id': r['id'], 'name': r['name'], 'created_at': r['created_at'].isoformat() if r.get('created_at') else None} for r in rows]
        return jsonify({'success': True, 'data': items})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/kafka-certs', methods=['POST'])
@require_login
def create_kafka_cert():
    """上传 Kafka 证书（仅管理员）"""
    user = get_current_user()
    if not user.get('is_admin'):
        return jsonify({'error': '仅管理员可上传证书'}), 403
    if 'file' not in request.files:
        return jsonify({'error': '未选择文件'}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    name = (request.form.get('name') or '').strip() or os.path.splitext(os.path.basename(f.filename))[0]
    if not name:
        return jsonify({'error': '证书名称不能为空'}), 400
    try:
        content = f.read().decode('utf-8', errors='replace')
    except Exception as e:
        return jsonify({'error': f'读取文件失败: {e}'}), 400
    if not content.strip():
        return jsonify({'error': '证书内容为空'}), 400
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('INSERT INTO kafka_certs (name, content) VALUES (%s, %s)', (name, content))
                cert_id = cur.lastrowid
            conn.commit()
        return jsonify({'success': True, 'data': {'id': cert_id, 'name': name}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/kafka-certs/<int:cid>', methods=['DELETE'])
@require_login
def delete_kafka_cert(cid):
    """删除 Kafka 证书（仅管理员）"""
    user = get_current_user()
    if not user.get('is_admin'):
        return jsonify({'error': '仅管理员可删除证书'}), 403
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM kafka_certs WHERE id = %s', (cid,))
                if cur.rowcount == 0:
                    return jsonify({'error': '证书不存在'}), 404
            conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------- 证书上传（Kafka，兼容旧用法） ----------
@app.route('/api/upload/cert', methods=['POST'])
@require_login
def upload_cert():
    """上传 Kafka 证书（数据构造用，需登录）"""
    if 'file' not in request.files:
        return jsonify({'error': '未选择文件'}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    safe_name = os.path.basename(f.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
    f.save(path)
    return jsonify({'success': True, 'data': {'path': path, 'name': safe_name}})


@app.route('/api/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok', 'message': '服务运行正常'})


if __name__ == '__main__':
    init_db()
    start_scheduler()
    start_agent_status_refresh()
    from config import HOST, PORT, DEBUG
    app.run(debug=DEBUG, host=HOST, port=PORT)