import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.strategy.technical import MACDStrategy, BollingerBandStrategy, MAStrategy
from datetime import date, timedelta

end = date.today()
start = end - timedelta(days=365)
code = 'sz000063'

for name, s in [
    ('MACD', MACDStrategy()),
    ('布林带', BollingerBandStrategy()),
    ('均线', MAStrategy()),
]:
    r = s.backtest(code, start, end)
    print(f'{name}: 收益={r["total_return"]}% 年化={r["annual_return"]}% 最大回撤={r["max_drawdown"]}% 夏普={r["sharpe"]} 胜率={r["win_rate"]}% 交易数={len(r["trades"])}')
