"""
测试策略组合（CombinedStrategy）
对比单个策略 vs 组合策略的回测结果
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from datetime import date, timedelta
from app.strategy.technical import MACDStrategy, BollingerBandStrategy, MAStrategy
from app.strategy.combine import CombinedStrategy

# 测试参数
CODE = "sz000063"   # 中兴通讯
END_DATE = date.today()
START_DATE = date(END_DATE.year - 1, END_DATE.month, END_DATE.day)

print(f"测试股票：{CODE}")
print(f"时间范围：{START_DATE} ~ {END_DATE}")
print("=" * 60)

# ──────────────────────────────────────────────────────────────────────────
# 1. 单个策略回测
# ──────────────────────────────────────────────────────────────────────────
macd_st = MACDStrategy()
boll_st = BollingerBandStrategy()
ma_st   = MAStrategy()

strategies = [macd_st, boll_st, ma_st]
names     = ["MACD", "布林带", "均线"]

print("\n【单个策略回测】")
print("-" * 60)
for st, name in zip(strategies, names):
    result = st.backtest(CODE, START_DATE, END_DATE)
    print(f"\n{name}策略：")
    print(f"  总收益率  : {result['total_return']:.2f}%")
    print(f"  年化收益  : {result['annual_return']:.2f}%")
    print(f"  最大回撤  : {result['max_drawdown']:.2f}%")
    print(f"  夏普比率  : {result['sharpe']:.2f}")
    print(f"  胜率      : {result['win_rate']:.2f}%")
    print(f"  交易次数  : {len([t for t in result['trades'] if t['action']=='buy'])} 次买入")

# ──────────────────────────────────────────────────────────────────────────
# 2. 组合策略回测（不同投票规则）
# ──────────────────────────────────────────────────────────────────────────
print("\n\n【组合策略回测】")
print("-" * 60)

rules = ["majority", "unanimous", "any"]
rule_names = ["多数投票", "全票通过", "任意一个"]

for rule, rule_name in zip(rules, rule_names):
    combined = CombinedStrategy(
        strategies=strategies,
        voting_rule=rule,
    )
    result = combined.backtest(CODE, START_DATE, END_DATE)
    print(f"\n组合策略（{rule_name}）：")
    print(f"  总收益率  : {result['total_return']:.2f}%")
    print(f"  年化收益  : {result['annual_return']:.2f}%")
    print(f"  最大回撤  : {result['max_drawdown']:.2f}%")
    print(f"  夏普比率  : {result['sharpe']:.2f}")
    print(f"  胜率      : {result['win_rate']:.2f}%")
    print(f"  交易次数  : {len([t for t in result['trades'] if t['action']=='buy'])} 次买入")

# ──────────────────────────────────────────────────────────────────────────
# 3. generate_signals 测试
# ──────────────────────────────────────────────────────────────────────────
print("\n\n【信号生成测试】")
print("-" * 60)
combined = CombinedStrategy(strategies, "majority")
signals = combined.generate_signals(CODE, START_DATE, END_DATE)
print(f"多数投票规则下，共生成 {len(signals)} 个信号：")
for sig in signals[:5]:
    print(f"  {sig['date']} {sig['direction']:4s} @ {sig['price']:.2f}  原因：{sig['reason'][:50]}")
if len(signals) > 5:
    print(f"  ...（共 {len(signals)} 个信号，仅显示前5个）")

print("\n" + "=" * 60)
print("测试完成！")
