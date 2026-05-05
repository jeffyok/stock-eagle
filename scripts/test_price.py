"""调试 enrich_realtime"""
import sys
sys.path.insert(0, 'e:/pycharm_workspace/stock-eagle')

from app.portfolio.service import get_positions, enrich_with_realtime

positions = get_positions()
print(f"持仓数: {len(positions)}")
for p in positions:
    print(f"  id={p.id} code={p.code} name={p.name} cost={p.cost}")

enrich_with_realtime(positions)

for p in positions:
    cp = p.current_price()
    print(f"  {p.code} {p.name} - current_price={cp}")
