"""
数据构造Agent - 负责执行Kafka消息发送和ClickHouse数据写入
启动时在控制台输出Token，Token基于本机生成，每台电脑固定
支持通过参数修改端口
"""
import json
import hashlib
import platform
import socket
from functools import wraps
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def generate_machine_token():
    """根据机器信息生成固定Token"""
    info = f"{platform.node()}-{socket.gethostname()}-{platform.machine()}"
    return hashlib.sha256(info.encode()).hexdigest()[:32]

AGENT_TOKEN = generate_machine_token()


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
        return jsonify({'success': False, 'error': str(e)}), 500


def execute_kafka(task_data, batch_no):
    from kafka import KafkaProducer
    
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
    
    if config.get('username') and config.get('password'):
        producer_config['security_protocol'] = config.get('security_protocol', 'SASL_PLAINTEXT')
        producer_config['sasl_mechanism'] = config.get('sasl_mechanism', 'PLAIN')
        producer_config['sasl_plain_username'] = config['username']
        producer_config['sasl_plain_password'] = config['password']
    
    if config.get('ssl_cafile'):
        producer_config['ssl_cafile'] = config['ssl_cafile']
    if config.get('ssl_certfile'):
        producer_config['ssl_certfile'] = config['ssl_certfile']
    if config.get('ssl_keyfile'):
        producer_config['ssl_keyfile'] = config['ssl_keyfile']
    
    producer = KafkaProducer(**producer_config)
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
    
    return {'sent_count': sent_count, 'topic': topic}


def execute_clickhouse(task_data, batch_no):
    from clickhouse_driver import Client
    
    host = task_data.get('host', 'localhost')
    port = task_data.get('port', 9000)
    sqls = task_data.get('sqls', [])
    config = task_data.get('config', {})
    
    if not sqls:
        raise ValueError('Missing sqls')
    
    client = Client(
        host=host,
        port=port,
        user=config.get('user', 'default'),
        password=config.get('password', '')
    )
    
    executed = 0
    for sql in sqls:
        client.execute(sql)
        executed += 1
    
    return {'executed_sqls': executed, 'host': host}


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
