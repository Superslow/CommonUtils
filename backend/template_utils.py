"""
模板+参数渲染
支持 {param} 语法，参数类型：fixed, current_time, timestamp_13, timestamp_10, round_robin, batch
"""
import re
import json
import time
from datetime import datetime


def extract_params(template_str):
    """从模板中提取可变参数 {param}"""
    return list(set(re.findall(r'\{(\w+)\}', template_str)))


def render_template(template_str, param_config, batch_no=1, round_robin_values=None):
    """
    渲染模板
    param_config: [{param: 'xxx', type: 'fixed'|'current_time'|'timestamp_13'|'timestamp_10'|'round_robin'|'batch', value: '...'}]
    round_robin_values: {param: [v1, v2, ...]} 轮询值列表
    """
    result = template_str
    round_robin_values = round_robin_values or {}
    
    for cfg in param_config or []:
        param = cfg.get('param')
        if not param:
            continue
        ptype = cfg.get('type', 'fixed')
        value = cfg.get('value', '')
        
        if ptype == 'fixed':
            repl = str(value)
        elif ptype == 'current_time':
            repl = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elif ptype == 'timestamp_13':
            repl = str(int(time.time() * 1000))
        elif ptype == 'timestamp_10':
            repl = str(int(time.time()))
        elif ptype == 'round_robin':
            vals = round_robin_values.get(param, value.split(',') if isinstance(value, str) else [])
            if vals:
                idx = (batch_no - 1) % len(vals)
                repl = str(vals[idx].strip() if isinstance(vals[idx], str) else vals[idx])
            else:
                repl = str(value)
        elif ptype == 'batch':
            repl = str(batch_no)
        else:
            repl = str(value)
        
        result = result.replace(f'{{{param}}}', repl)
    
    return result


def render_kafka_messages(template_json, param_config, batch_size, batch_no):
    """渲染Kafka消息（JSON模板），每批生成batch_size条"""
    messages = []
    for i in range(batch_size):
        rendered = render_template(template_json, param_config, batch_no + i)
        try:
            data = json.loads(rendered)
            messages.append(data if isinstance(data, dict) else {'data': data})
        except json.JSONDecodeError:
            messages.append({'raw': rendered})
    return messages


def render_clickhouse_sqls(template_sqls, param_config, batch_size, batch_no):
    """渲染ClickHouse SQL（模板列表），每批生成batch_size组SQL"""
    sqls = template_sqls if isinstance(template_sqls, list) else [str(template_sqls)]
    result = []
    for i in range(batch_size):
        for sql in sqls:
            rendered = render_template(sql, param_config, batch_no + i)
            result.append(rendered)
    return result
