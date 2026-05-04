"""
测试基金筛选器（FundScreener）
"""
from app.strategy.fund_screener import FundScreener

screener = FundScreener()

print("=" * 60)
print("基金筛选器测试")
print("=" * 60)

# ──────────────────────────────────────────────────────────────────
# 1. 股票型基金 TOP10（近1年收益 > 0）
# ──────────────────────────────────────────────────────────────────
print("\n【1】股票型基金 TOP10（近1年收益 > 0%）")
print("-" * 60)
results = screener.top_stock_funds(top_n=10, min_1y_return=0.0)
print(f"找到 {len(results)} 只基金：\n")
for r in results[:5]:
    print(
        f"  {r['code']:6s}  {r['name'][:14]:14s}  "
        f"近1年={r.get('return_1y', 0):6.2f}%  "
        f"近3年={r.get('return_3y', 0) or 0.0:6.2f}%  "
        f"净值={r.get('nav', 0):.4f}"
    )
if len(results) > 5:
    print(f"  ...（共 {len(results)} 只，仅显示前5只）")

# ──────────────────────────────────────────────────────────────────
# 2. 混合型基金 TOP10
# ──────────────────────────────────────────────────────────────────
print("\n\n【2】混合型基金 TOP10（近1年收益 > 0%）")
print("-" * 60)
results = screener.top_mixed_funds(top_n=10, min_1y_return=0.0)
print(f"找到 {len(results)} 只基金：\n")
for r in results[:5]:
    print(
        f"  {r['code']:6s}  {r['name'][:14]:14s}  "
        f"近1年={r.get('return_1y', 0):6.2f}%  "
        f"净值={r.get('nav', 0):.4f}"
    )
if len(results) > 5:
    print(f"  ...（共 {len(results)} 只，仅显示前5只）")

# ──────────────────────────────────────────────────────────────────
# 3. 自定义筛选：近3年收益 > 50% 的股票型基金
# ──────────────────────────────────────────────────────────────────
print("\n\n【3】自定义筛选：近3年收益 > 50%（基金名含'股票'）")
print("-" * 60)
results = screener.screen(
    name_keyword="股票",
    min_return={"return_3y": 50.0},
    sort_by="return_3y",
    ascending=False,
    top_n=10,
)
print(f"找到 {len(results)} 只基金：\n")
for r in results[:5]:
    r3y = r.get("return_3y") or 0.0
    rytd = r.get("return_ytd") or 0.0
    print(
        f"  {r['code']:6s}  {r['name'][:14]:14s}  "
        f"近3年={r3y:6.2f}%  "
        f"今年来={rytd:6.2f}%"
    )
if len(results) > 5:
    print(f"  ...（共 {len(results)} 只，仅显示前5只）")

# ──────────────────────────────────────────────────────────────────
# 4. 单只基金历史净值
# ──────────────────────────────────────────────────────────────────
print("\n\n【4】单只基金历史净值（最近1年）")
print("-" * 60)
# 取一只股票型基金做测试
test_code = None
test_name = ""
results = screener.top_stock_funds(top_n=1, min_1y_return=0.0)
if results:
    test_code = results[0]["code"]
    test_name = results[0]["name"]
    nav_history = screener.get_fund_nav_history(test_code, years=1)
    print(f"基金 {test_code}（{test_name}）最近1年净值（前5条）：")
    for rec in nav_history[:5]:
        print(f"  {rec['date']}  NAV={rec['nav']:.4f}  涨跌幅={rec['pct_chg']:.2f}%")
    if len(nav_history) > 5:
        print(f"  ...（共 {len(nav_history)} 条记录）")
else:
    print("无可用基金数据，跳过净值历史测试")

print("\n" + "=" * 60)
print("测试完成！")
