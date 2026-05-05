-- 修复 buy_price 列：设置为允许 NULL / 默认值
ALTER TABLE t_portfolio MODIFY COLUMN buy_price DECIMAL(10,2) DEFAULT 0 COMMENT '买入价';
