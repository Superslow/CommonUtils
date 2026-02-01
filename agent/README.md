# 数据构造 Agent

负责实际执行 Kafka 消息发送和 ClickHouse 数据写入的节点。主程序将任务下发给 Agent，Agent 执行后返回结果。

## 启动

```bash
pip install -r requirements.txt
python agent.py
```

## 修改端口

```bash
python agent.py -p 5002
# 或
python agent.py --port 5002 --host 0.0.0.0
```

## Token

- 启动时在控制台输出 **Token**，关联 Agent 时在主程序里填写此 Token。
- Token 根据本机信息生成，**每台电脑固定**，重启不变。

## 关联方式

在主程序「数据构造」→「Agent 管理」→「新增 Agent」中填写：
- **URL**：本机 Agent 地址，如 `http://192.168.1.100:5001`
- **Token**：上述控制台输出的 Token

## 校验

主程序提供「校验 Agent」功能，输入 URL 和 Token 可检查 Agent 是否可用。
