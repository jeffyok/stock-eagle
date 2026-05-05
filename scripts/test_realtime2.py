"""测试批量获取全市场行情效率"""
import akshare as ak
import pandas as pd
import time

t0 = time.time()
df = ak.stock_zh_a_spot_em()
t1 = time.time()
print(f"全市场拉取耗时: {t1-t0:.1f}s, 行数: {len(df)}")
print("列名:", df.columns.tolist())

# 按 code 过滤
codes = ["600519", "000001", "300750"]
t2 = time.time()
sub = df[df["代码"].isin(codes)][["代码", "名称", "最新价", "涨跌幅"]]
t3 = time.time()
print(f"\n过滤耗时: {t3-t2:.3f}s")
print(sub.to_string(index=False))
