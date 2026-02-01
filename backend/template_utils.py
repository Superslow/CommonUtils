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


def render_template(template_str, param_config, batch_no=1, round_robin_values=None, message_index_in_batch=0):
    """
    渲染模板
    param_config: [{param, type, value}]
    type: fixed=原样；current_time=当前时间(可填格式)；timestamp_13/10；round_robin=本批内序号或逗号分隔轮询；batch=执行批次号
    message_index_in_batch: 当前条在本批内的序号 0..batch_size-1，用于 round_robin 无值时渲染为 1..batch_size
    """
    result = template_str
    round_robin_values = round_robin_values or {}

    for cfg in param_config or []:
        param = cfg.get('param')
        if not param:
            continue
        ptype = cfg.get('type', 'fixed')
        value = cfg.get('value', '') or ''

        if ptype == 'fixed':
            repl = str(value)
        elif ptype == 'current_time':
            fmt = (value or '').strip() or '%Y-%m-%d %H:%M:%S'
            repl = datetime.now().strftime(fmt)
        elif ptype == 'timestamp_13':
            repl = str(int(time.time() * 1000))
        elif ptype == 'timestamp_10':
            repl = str(int(time.time()))
        elif ptype == 'round_robin':
            vals = round_robin_values.get(param)
            if vals is None and isinstance(value, str) and value.strip():
                vals = [v.strip() for v in value.split(',') if v.strip()]
            if vals:
                idx = (batch_no - 1 + message_index_in_batch) % len(vals)
                repl = str(vals[idx] if isinstance(vals[idx], str) else vals[idx])
            else:
                repl = str(message_index_in_batch + 1)
        elif ptype == 'batch':
            repl = str(batch_no)
        else:
            repl = str(value)

        result = result.replace(f'{{{param}}}', repl)

    return result


def render_kafka_messages(template_json, param_config, batch_size, batch_no):
    """渲染Kafka消息（JSON模板），每批生成batch_size条；round_robin 无值时为本批内序号 1..batch_size"""
    messages = []
    for i in range(batch_size):
        rendered = render_template(template_json, param_config, batch_no, message_index_in_batch=i)
        try:
            data = json.loads(rendered)
            messages.append(data if isinstance(data, dict) else {'data': data})
        except json.JSONDecodeError:
            messages.append({'raw': rendered})
    return messages


def render_clickhouse_sqls(template_sqls, param_config, batch_size, batch_no):
    """渲染ClickHouse SQL（模板列表），每批生成batch_size组SQL；round_robin 无值时为本批内序号 1..batch_size"""
    sqls = template_sqls if isinstance(template_sqls, list) else [str(template_sqls)]
    result = []
    for i in range(batch_size):
        for sql in sqls:
            rendered = render_template(sql, param_config, batch_no, message_index_in_batch=i)
            result.append(rendered)
    return result
