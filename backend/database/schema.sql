-- CommonUtils 数据库表结构（兼容 MySQL 5.5.x，JSON 用 TEXT 存储）
-- 用户表（用户名+密码登录，预留管理员账号）
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE COMMENT '用户名',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    is_admin TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否管理员',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 管理员IP列表（可修改/删除所有任务和Agent，可选保留）
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
    creator_user_id INT NULL COMMENT '创建者用户ID',
    creator_ip VARCHAR(45) NULL COMMENT '创建者IP（审计）',
    status ENUM('online', 'offline', 'unknown') DEFAULT 'unknown',
    last_check_at TIMESTAMP NULL DEFAULT NULL,
    kafka_config TEXT DEFAULT NULL COMMENT 'Kafka连接配置(可选，任务级也可配置)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT NULL,
    INDEX idx_creator_user_id (creator_user_id),
    INDEX idx_creator_ip (creator_ip),
    FOREIGN KEY (creator_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

DROP TRIGGER IF EXISTS agents_before_update;
CREATE TRIGGER agents_before_update BEFORE UPDATE ON agents FOR EACH ROW SET NEW.updated_at = NOW();

-- 数据构造任务表（同上，updated_at 用 DATETIME+触发器）
CREATE TABLE IF NOT EXISTS data_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '任务名称',
    task_type ENUM('kafka', 'clickhouse') NOT NULL COMMENT '任务类型',
    status ENUM('running', 'stopped', 'paused') DEFAULT 'stopped',
    stop_reason VARCHAR(255) NULL DEFAULT NULL COMMENT '自动停止原因，如连续失败超过3次',
    cron_expr VARCHAR(100) NOT NULL COMMENT 'Cron表达式',
    batch_size INT DEFAULT 1 COMMENT '每批数据条数',
    agent_id INT NOT NULL COMMENT '执行Agent',
    template_content TEXT NOT NULL COMMENT '模板内容(JSON或SQL)',
    param_config TEXT DEFAULT NULL COMMENT '参数配置[{param, type, value}]',
    connector_config TEXT DEFAULT NULL COMMENT '连接器配置(Kafka/ClickHouse)',
    creator_user_id INT NULL COMMENT '创建者用户ID',
    creator_ip VARCHAR(45) NULL COMMENT '创建者IP（审计）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT NULL,
    INDEX idx_creator_user_id (creator_user_id),
    INDEX idx_creator_ip (creator_ip),
    INDEX idx_status (status),
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE RESTRICT,
    FOREIGN KEY (creator_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

DROP TRIGGER IF EXISTS data_tasks_before_update;
CREATE TRIGGER data_tasks_before_update BEFORE UPDATE ON data_tasks FOR EACH ROW SET NEW.updated_at = NOW();

-- 站点配置（菜单、公告等，key-value）
CREATE TABLE IF NOT EXISTS site_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(64) NOT NULL UNIQUE COMMENT '配置键',
    config_value TEXT COMMENT '配置值(JSON)',
    updated_at DATETIME NULL DEFAULT NULL,
    INDEX idx_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

DROP TRIGGER IF EXISTS site_config_before_update;
CREATE TRIGGER site_config_before_update BEFORE UPDATE ON site_config FOR EACH ROW SET NEW.updated_at = NOW();

-- Kafka 证书表（管理员上传，任务通过名称/ID 关联）
CREATE TABLE IF NOT EXISTS kafka_certs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '证书名称（展示与选择用）',
    content LONGTEXT NOT NULL COMMENT 'PEM 证书内容',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 调度抢占表（多进程下同一计划时间只允许一个进程执行，避免重复跑）
CREATE TABLE IF NOT EXISTS data_task_schedule_claims (
    task_id INT NOT NULL,
    schedule_key_ts BIGINT NOT NULL COMMENT '计划执行时间戳(秒)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (task_id, schedule_key_ts),
    FOREIGN KEY (task_id) REFERENCES data_tasks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

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
