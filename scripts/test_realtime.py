"""测试实时行情获取"""
import sys
sys.path.insert(0, 'e:/pycharm_workspace/stock-eagle')

from app.data.akshare_source import AKShareSource

src = AKShareSource()

# 测试 sh600519
print("=== 测试 sh600519 ===")
data = src.get_stock_realtime("sh600519")
print("返回结果:", data)

# 测试 sz000001
print("\n=== 测试 sz000001 ===")
data2 = src.get_stock_realtime("sz000001")
print("返回结果:", data2)

# 测试 portfolio service
print("\n=== 测试 enrich_with_realtime ===")
from app.portfolio.service import get_positions, enrich_with_realtime

positions = get_positions()
print(f"持仓数量: {len(positions)}")
for p in positions:
    print(f"  {p.code} {p.name} - cost={p.cost}, current_price={p.current_price()}")
