"""
数据构造Agent - 负责执行Kafka消息发送和ClickHouse数据写入
启动时在控制台输出Token，Token基于本机生成，每台电脑固定
支持通过参数修改端口
"""
import json
import hashlib
import traceback
import platform
import socket
import tempfile
import os
from functools import wraps
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from kafka import KafkaProducer
from clickhouse_driver import Client

app = Flask(__name__)
CORS(app)


def generate_machine_token():
    """根据机器信息生成固定Token"""
    info = f"{platform.node()}-{socket.gethostname()}-{platform.machine()}"
    return hashlib.sha256(info.encode()).hexdigest()[:32]


AGENT_TOKEN = generate_machine_token()

# Kafka 证书缓存目录（下发任务时写入，按内容哈希去重，已有则校验后复用）
def _cert_cache_dir():
    base = os.environ.get('AGENT_CERT_CACHE_DIR')
    if base:
        return os.path.join(base, 'certs')
    if os.name == 'nt':
        base = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
    else:
        base = os.path.expanduser('~/.local/share')
    return os.path.join(base, 'commonutils_agent', 'certs')


def get_cached_cert_path(pem_content):
    """
    将 PEM 证书内容缓存到本地，按内容 SHA256 命名；已有则校验内容一致后复用路径，避免重复缓存。
    返回本地 .pem 文件路径。
    """
    if not pem_content or not isinstance(pem_content, str):
        return None
    pem_content = pem_content.strip()
    if '-----BEGIN' not in pem_content:
        return None
    content_bytes = pem_content.encode('utf-8')
    h = hashlib.sha256(content_bytes).hexdigest()
    cache_dir = _cert_cache_dir()
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, f'{h}.pem')
    if os.path.isfile(path):
        try:
            with open(path, 'rb') as f:
                existing = f.read()
            if hashlib.sha256(existing).hexdigest() == h:
                return path
        except Exception:
            pass
    try:
        with open(path, 'wb') as f:
            f.write(content_bytes)
    except Exception:
        return None
    return path


def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-Agent-Token') or (request.json.get('token') if request.is_json else None)
        if not token or token != AGENT_TOKEN:
            return jsonify({'success': False, 'error': 'Invalid or missing token'}), 401
        return f(*args, **kwargs)
    return decorated


@app.route('/api/agent/health', methods=['GET'])
@require_token
def health():
    return jsonify({'success': True, 'status': 'ok'})


@app.route('/api/agent/execute', methods=['POST'])
@require_token
def execute():
    try:
        data = request.get_json()
        task_type = data.get('task_type')
        task_data = data.get('task_data')
        batch_no = data.get('batch_no', 1)

        if not task_type or not task_data:
            return jsonify({'success': False, 'error': 'Missing task_type or task_data'}), 400

        if task_type == 'kafka':
            result = execute_kafka(task_data, batch_no)
        elif task_type == 'clickhouse':
            result = execute_clickhouse(task_data, batch_no)
        else:
            return jsonify({'success': False, 'error': f'Unknown task_type: {task_type}'}), 400

        return jsonify({
            'success': True,
            'result': result,
            'batch_no': batch_no,
            'executed_at': datetime.now().isoformat()
        })
    except Exception as e:
        tb = traceback.format_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': tb
        }), 500


def execute_kafka(task_data, batch_no):
    bootstrap_servers = task_data.get('bootstrap_servers', 'localhost:9092')
    topic = task_data.get('topic')
    messages = task_data.get('messages', [])
    config = task_data.get('config', {})

    if not topic or not messages:
        raise ValueError('Missing topic or messages')

    producer_config = {
        'bootstrap_servers': bootstrap_servers.split(','),
        'value_serializer': lambda v: json.dumps(v).encode('utf-8') if isinstance(v, dict) else str(v).encode('utf-8')
    }
    security_protocol = (config.get('security_protocol') or 'PLAINTEXT').upper()
    producer_config['security_protocol'] = security_protocol

    if security_protocol in ('SASL_PLAINTEXT', 'SASL_SSL') and config.get('username') and config.get('password'):
        producer_config['sasl_mechanism'] = config.get('sasl_mechanism') or 'PLAIN'
        producer_config['sasl_plain_username'] = config['username']
        producer_config['sasl_plain_password'] = config['password']

    ssl_cafile_path = None
    if security_protocol in ('SSL', 'SASL_SSL') and config.get('ssl_cafile'):
        ssl_cafile = config['ssl_cafile']
        if isinstance(ssl_cafile, str) and '-----BEGIN' in ssl_cafile:
            ssl_cafile_path = get_cached_cert_path(ssl_cafile)
            if ssl_cafile_path:
                producer_config['ssl_cafile'] = ssl_cafile_path
            else:
                fd, ssl_cafile_path = tempfile.mkstemp(suffix='.pem')
                try:
                    os.write(fd, ssl_cafile.encode('utf-8'))
                finally:
                    os.close(fd)
                producer_config['ssl_cafile'] = ssl_cafile_path
        else:
            producer_config['ssl_cafile'] = ssl_cafile
        producer_config['ssl_check_hostname'] = False

    try:
        producer = KafkaProducer(**producer_config)
    except Exception as e:
        raise RuntimeError(f'Kafka 连接失败: {e}') from e
    sent_count = 0
    try:
        for msg in messages:
            if isinstance(msg, dict):
                producer.send(topic, value=msg)
            else:
                producer.send(topic, value=msg.encode('utf-8') if isinstance(msg, str) else msg)
            sent_count += 1
        producer.flush()
    finally:
        producer.close()
        if ssl_cafile_path and os.path.isfile(ssl_cafile_path) and _cert_cache_dir() not in ssl_cafile_path:
            try:
                os.remove(ssl_cafile_path)
            except Exception:
                pass

    return {'sent_count': sent_count, 'topic': topic}


def execute_clickhouse(task_data, batch_no):
    host = task_data.get('host', 'localhost')
    port = task_data.get('port', 9000)
    sqls = task_data.get('sqls', [])
    config = task_data.get('config', {}) or {}

    if not sqls:
        raise ValueError('Missing sqls')

    user = config.get('user') or config.get('username')
    password = config.get('password') or config.get('passwd')
    if user is None:
        user = 'default'
    if password is None:
        password = ''
    user = str(user).strip() if user else 'default'
    user = user or 'default'
    password = str(password) if password is not None else ''
    database = (config.get('database') or '').strip() or 'default'
    try:
        client = Client(
            host=host,
            port=int(port) if port is not None else 9000,
            database=database,
            user=user,
            password=password
        )
        executed = 0
        for sql in sqls:
            client.execute(sql)
            executed += 1
        return {'executed_sqls': executed, 'host': host}
    except Exception as e:
        err_msg = str(e)
        if 'password' in err_msg.lower() and ('incorrect' in err_msg.lower() or 'no user' in err_msg.lower()):
            hint = ' (收到密码长度: %d，若为 0 表示未传到 Agent)' % len(password)
            raise RuntimeError(err_msg + hint) from e
        raise


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=5001, help='Agent port')
    parser.add_argument('-H', '--host', default='0.0.0.0', help='Bind host')
    args = parser.parse_args()

    print('=' * 60)
    print('Agent Token (use when registering):')
    print(AGENT_TOKEN)
    print('=' * 60)

    app.run(host=args.host, port=args.port, debug=False)
