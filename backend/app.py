"""
通用工具类Web服务
提供时间戳转换、JSON格式化校验、编码转换、文件MD5值计算、网段和IP归属关系判断、Cron表达式解析等功能
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import time
import hashlib
import base64
import ipaddress
from datetime import datetime
from croniter import croniter
import codecs

app = Flask(__name__)
CORS(app)  # 允许跨域请求


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


@app.route('/api/cron/parse', methods=['POST'])
def cron_parse():
    """Cron表达式解析"""
    try:
        data = request.get_json()
        cron_expr = data.get('cron')
        count = data.get('count', 10)
        
        if cron_expr is None:
            return jsonify({'error': '缺少cron参数'}), 400
        
        try:
            base_time = datetime.now()
            cron = croniter(cron_expr, base_time)
            
            parts = cron_expr.split()
            if len(parts) != 5:
                raise ValueError('Cron表达式必须包含5个字段（分 时 日 月 周）')
            
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
                'fields': {
                    'minute': parts[0],
                    'hour': parts[1],
                    'day': parts[2],
                    'month': parts[3],
                    'weekday': parts[4]
                },
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
    """获取Cron表达式的描述"""
    parts = cron_expr.split()
    if len(parts) != 5:
        return '无效的Cron表达式'
    
    descriptions = []
    
    if parts[0] == '*':
        descriptions.append('每分钟')
    elif '/' in parts[0]:
        interval = parts[0].split('/')[1]
        descriptions.append(f'每{interval}分钟')
    else:
        descriptions.append(f'在{parts[0]}分')
    
    if parts[1] == '*':
        descriptions.append('每小时')
    elif '/' in parts[1]:
        interval = parts[1].split('/')[1]
        descriptions.append(f'每{interval}小时')
    else:
        descriptions.append(f'在{parts[1]}时')
    
    if parts[2] == '*':
        descriptions.append('每天')
    elif '/' in parts[2]:
        interval = parts[2].split('/')[1]
        descriptions.append(f'每{interval}天')
    else:
        descriptions.append(f'在{parts[2]}日')
    
    if parts[3] == '*':
        descriptions.append('每月')
    elif '/' in parts[3]:
        interval = parts[3].split('/')[1]
        descriptions.append(f'每{interval}月')
    else:
        descriptions.append(f'在{parts[3]}月')
    
    weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
    if parts[4] == '*':
        descriptions.append('每周')
    elif parts[4].isdigit():
        day = int(parts[4])
        if 0 <= day <= 6:
            descriptions.append(f'在{weekdays[day]}')
    else:
        descriptions.append(f'在{parts[4]}')
    
    return ' '.join(descriptions)


@app.route('/api/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok', 'message': '服务运行正常'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)