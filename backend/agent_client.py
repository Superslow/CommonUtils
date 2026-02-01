"""
Agent客户端 - 支持连接缓存，避免每次轮询重新建立连接
"""
import requests
import threading
from datetime import datetime
# Agent连接缓存: {url: {'session': session, 'last_check': datetime, 'status': 'ok'}}
_agent_cache = {}
_cache_lock = threading.Lock()


def _ensure_url(url):
    """确保URL包含协议"""
    if not url:
        return url
    url = url.strip().rstrip('/')
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    return url


def get_agent_session(url):
    """获取Agent的缓存session，避免每次轮询重新建立连接"""
    url = _ensure_url(url)
    base = url.rstrip('/')
    with _cache_lock:
        if base not in _agent_cache:
            session = requests.Session()
            session.headers.update({'Content-Type': 'application/json'})
            _agent_cache[base] = {
                'session': session,
                'last_check': None,
                'status': 'unknown'
            }
        return _agent_cache[base]['session'], base


def check_agent(url, token):
    """校验Agent是否可用"""
    session, base = get_agent_session(url)
    try:
        resp = session.get(
            base.rstrip('/') + '/api/agent/health',
            headers={'X-Agent-Token': token},
            timeout=5
        )
        ok = resp.status_code == 200
        with _cache_lock:
            if base in _agent_cache:
                _agent_cache[base]['last_check'] = datetime.now()
                _agent_cache[base]['status'] = 'ok' if ok else 'error'
        return ok, resp.json() if resp.text else {}
    except Exception as e:
        with _cache_lock:
            if base in _agent_cache:
                _agent_cache[base]['status'] = 'error'
        return False, {'error': str(e)}


def execute_on_agent(url, token, task_type, task_data, batch_no=1):
    """在Agent上执行任务"""
    session, base = get_agent_session(url)
    resp = session.post(
        base.rstrip('/') + '/api/agent/execute',
        headers={'X-Agent-Token': token},
        json={
            'task_type': task_type,
            'task_data': task_data,
            'batch_no': batch_no
        },
        timeout=60
    )
    if resp.status_code != 200:
        raise Exception(f'Agent error: {resp.status_code} {resp.text}')
    data = resp.json()
    if not data.get('success'):
        raise Exception(data.get('error', 'Unknown error'))
    return data.get('result', {})
