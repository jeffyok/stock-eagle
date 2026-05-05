"""
执行数据库迁移：添加 name 字段到 t_strategy_signal 表
"""
import pymysql

conn = pymysql.connect(
    host='127.0.0.1',
    port=3306,
    user='root',
    password='123456',
    database='db_stockeagle'
)
cur = conn.cursor()

# 检查是否已有 name 字段
cur.execute('SHOW COLUMNS FROM t_strategy_signal LIKE "name"')
if not cur.fetchone():
    cur.execute('''
        ALTER TABLE t_strategy_signal
        ADD COLUMN name VARCHAR(50) COMMENT "股票名称" AFTER code
    ''')
    print('Added name column to t_strategy_signal')
else:
    print('name column already exists')

conn.commit()

# 验证表结构
cur.execute('DESCRIBE t_strategy_signal')
print('\nCurrent table structure:')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}')

cur.close()
conn.close()
print('\nMigration completed!')
