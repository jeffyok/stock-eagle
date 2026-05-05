-- =====================================================
-- 策略信号表字段补充
-- 执行时间: 2026-05-05
-- 说明: scan_strategy_signals 任务需要 name 字段
-- =====================================================

-- 添加股票名称字段
ALTER TABLE t_strategy_signal 
ADD COLUMN IF NOT EXISTS name VARCHAR(50) COMMENT '股票名称' AFTER code;

-- 验证
DESCRIBE t_strategy_signal;
