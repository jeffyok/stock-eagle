"""
快速测试多因子策略
"""
import sys
sys.path.insert(0, r"e:\pycharm_workspace\stock-eagle")

from app.strategy.multi_factor import MultiFactorStrategy
from datetime import date, timedelta

strategy = MultiFactorStrategy()
end = date.today()
start = end - timedelta(days=365)

code = "sh600519"
print(f"=== 测试信号生成: {code} ===")
try:
    signals = strategy.generate_signals(code, start, end)
    print(f"信号数: {len(signals)}")
    for s in signals:
        print(s)
except Exception as e:
    print(f"信号生成失败: {e}")

print(f"\n=== 测试回测: {code} ===")
try:
    result = strategy.backtest(code, start, end, initial_cash=100000.0)
    print(f"总收益率: {result['total_return']:.2f}%")
    print(f"年化收益: {result['annual_return']:.2f}%")
    print(f"最大回撤: {result['max_drawdown']:.2f}%")
    print(f"夏普比率: {result['sharpe']:.2f}")
    print(f"胜率: {result['win_rate']:.2f}%")
    print(f"交易次数: {len(result['trades'])}")
except Exception as e:
    print(f"回测失败: {e}")
