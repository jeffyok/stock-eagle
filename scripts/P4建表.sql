-- P4 持仓管理 + 风控规则 建表 DDL
-- 执行方式：mysql -h 127.0.0.1 -u root -p123456 db_stockeagle < scripts/P4建表.sql

USE db_stockeagle;

-- ============================================================
-- t_portfolio：持仓表
-- ============================================================
CREATE TABLE IF NOT EXISTS t_portfolio (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    code         VARCHAR(10)   NOT NULL COMMENT '股票代码，如 sh600519',
    name         VARCHAR(20)   NOT NULL COMMENT '股票名称',
    cost         DECIMAL(12,2) NOT NULL COMMENT '持仓成本（元/股）',
    quantity     BIGINT         NOT NULL COMMENT '持仓数量（股）',
    buy_date     DATE           NOT NULL COMMENT '买入日期',
    stop_loss    DECIMAL(12,2)     NULL COMMENT '止损价（元）',
    take_profit  DECIMAL(12,2)     NULL COMMENT '止盈价（元）',
    note         VARCHAR(255)        NULL COMMENT '备注',
    deleted_at   DATETIME            NULL COMMENT '软删除时间',
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_code (code),
    INDEX idx_deleted (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='持仓管理表';

-- ============================================================
-- t_risk_rule：风控规则配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS t_risk_rule (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    rule_key     VARCHAR(30)   NOT NULL UNIQUE COMMENT '规则键',
    rule_name    VARCHAR(50)   NOT NULL COMMENT '规则名称',
    rule_value   VARCHAR(50)   NOT NULL COMMENT '规则值',
    rule_type    VARCHAR(10)   NOT NULL COMMENT '类型：number / switch',
    description  VARCHAR(255)     NULL COMMENT '规则说明',
    is_enabled   TINYINT(1)   DEFAULT 1 COMMENT '是否启用（0=否，1=是）',
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_key (rule_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='风控规则配置表';

-- ============================================================
-- t_risk_rule 初始数据
-- ============================================================
INSERT INTO t_risk_rule (rule_key, rule_name, rule_value, rule_type, description) VALUES
('single_loss_pct',     '单票亏损报警阈值',     '5',  'number', '单只股票亏损超过成本价 X% 时报警'),
('total_loss_pct',      '账户总亏损报警阈值',   '10', 'number', '账户总盈亏低于总成本 X% 时报警'),
('position_pct',        '单票仓位上限报警',     '30', 'number', '单只股票市值占账户总资产超过 X% 时报警'),
('drawdown_pct',       '账户最大回撤报警阈值', '15', 'number', '账户市值从最高点回撤超过 X% 时报警'),
('stop_loss_triggered', '止损价触发报警',        '1',  'switch', '持仓股票价格触及或跌破止损价时报警'),
('take_profit_triggered','止盈价触发报警',       '1',  'switch', '持仓股票价格触及或突破止盈价时报警')
ON DUPLICATE KEY UPDATE rule_value = VALUES(rule_value);

-- ============================================================
-- t_push_log：推送日志表（每日复盘推送记录）
-- ============================================================
CREATE TABLE IF NOT EXISTS t_push_log (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    push_type    VARCHAR(20)   NOT NULL COMMENT '推送类型：daily_review / alert',
    title        VARCHAR(100)  NOT NULL COMMENT '推送标题',
    content      TEXT              NULL COMMENT '推送内容',
    status       VARCHAR(10)   NOT NULL COMMENT 'success / failed',
    error_msg    VARCHAR(500)     NULL COMMENT '失败原因',
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='推送日志表';
