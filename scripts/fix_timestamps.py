"""修复 t_portfolio 时间戳列"""
import pymysql

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='123456', database='db_stockeagle')
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE t_portfolio ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
    print("created_at 列已添加")
except Exception as e:
    print(f"created_at: {e}")

try:
    cur.execute("ALTER TABLE t_portfolio ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
    print("updated_at 列已添加")
except Exception as e:
    print(f"updated_at: {e}")

conn.commit()

# 验证
cur.execute("SELECT id, created_at, updated_at FROM t_portfolio LIMIT 3")
rows = cur.fetchall()
print("\n现有数据时间戳：")
for r in rows:
    print(r)

conn.close()
