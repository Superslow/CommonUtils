-- CommonUtils 数据库表结构（兼容 MySQL 5.5.x，JSON 用 TEXT 存储）
-- 管理员IP列表（可修改/删除所有任务和Agent）
CREATE TABLE IF NOT EXISTS admin_ips (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip VARCHAR(45) NOT NULL UNIQUE,
    remark VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Agent节点表（MySQL 5.5 仅允许一个 TIMESTAMP 带 CURRENT_TIMESTAMP，故 updated_at 用 DATETIME+触发器）
CREATE TABLE IF NOT EXISTS agents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT 'Agent名称',
    url VARCHAR(500) NOT NULL COMMENT 'Agent服务地址',
    token VARCHAR(128) NOT NULL COMMENT '验证Token',
    creator_ip VARCHAR(45) NOT NULL COMMENT '创建者IP',
    status ENUM('online', 'offline', 'unknown') DEFAULT 'unknown',
    last_check_at TIMESTAMP NULL DEFAULT NULL,
    kafka_config TEXT DEFAULT NULL COMMENT 'Kafka连接配置(可选，任务级也可配置)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT NULL,
    INDEX idx_creator_ip (creator_ip)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

DROP TRIGGER IF EXISTS agents_before_update;
CREATE TRIGGER agents_before_update BEFORE UPDATE ON agents FOR EACH ROW SET NEW.updated_at = NOW();

-- 数据构造任务表（同上，updated_at 用 DATETIME+触发器）
CREATE TABLE IF NOT EXISTS data_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '任务名称',
    task_type ENUM('kafka', 'clickhouse') NOT NULL COMMENT '任务类型',
    status ENUM('running', 'stopped', 'paused') DEFAULT 'stopped',
    cron_expr VARCHAR(100) NOT NULL COMMENT 'Cron表达式',
    batch_size INT DEFAULT 1 COMMENT '每批数据条数',
    agent_id INT NOT NULL COMMENT '执行Agent',
    template_content TEXT NOT NULL COMMENT '模板内容(JSON或SQL)',
    param_config TEXT DEFAULT NULL COMMENT '参数配置[{param, type, value}]',
    connector_config TEXT DEFAULT NULL COMMENT '连接器配置(Kafka/ClickHouse)',
    creator_ip VARCHAR(45) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT NULL,
    INDEX idx_creator_ip (creator_ip),
    INDEX idx_status (status),
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

DROP TRIGGER IF EXISTS data_tasks_before_update;
CREATE TRIGGER data_tasks_before_update BEFORE UPDATE ON data_tasks FOR EACH ROW SET NEW.updated_at = NOW();

-- 任务执行记录表
CREATE TABLE IF NOT EXISTS task_executions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id INT NOT NULL,
    batch_no INT DEFAULT 1,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success TINYINT(1) DEFAULT 1,
    result_message TEXT,
    records_count INT DEFAULT 0,
    INDEX idx_task_id (task_id),
    INDEX idx_executed_at (executed_at),
    FOREIGN KEY (task_id) REFERENCES data_tasks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
