# StockEagle 🦅

**StockEagle** — 开源量化智能选股选基系统

> 用数据和策略替代情绪，用信号和规则替代直觉。

---

## ⚡ 开发进度

| 阶段 | 内容 | 状态 |
|------|------|------|
| P0 | 项目骨架 · 数据源 · 数据库 | ✅ 完成 |
| P1 | 策略层（多因子/技术/组合/基金筛选） | ✅ 完成 |
| P2 | 智能+追踪（评分/龙虎榜/板块/资金/热搜） | ✅ 完成 |
| P3 | Web UI（Streamlit）+ 风控 | 🔜 进行中 |
| P4 | 持仓管理 + 止损止盈 + 飞书推送 | 📋 待开始 |

---

## 🎯 功能概览

### 已上线（P0 + P1 + P2）

| 模块 | 功能 | 核心类 |
|------|------|--------|
| **数据源** | AKShare / westock-data / BaoStock / Ashare / efinance，全免费 | `AKShareSource` / `DataService` |
| **多因子策略** | 基本面+技术面+资金面+舆情，加权评分 + 回测 | `MultiFactorStrategy` |
| **技术策略** | MACD / 布林带 / 均线，独立回测 | `MACDStrategy` / `BollingerBandStrategy` / `MAStrategy` |
| **策略组合** | 多策略投票（多数/全票/任意），降低单一策略风险 | `CombinedStrategy` |
| **基金筛选器** | 按收益率/名称关键字/排序多维筛选公募基金 | `FundScreener` |
| **AI 综合评分** | 基本面30% + 技术面30% + 资金面25% + 舆情15% | `StockScorer` |
| **龙虎榜解读** | 游资席位识别 · 散户行为分析 · 异动汇总 | `DragonTigerAnalyzer` |
| **板块异动监控** | 行业/概念板块轮动 · 资金流向排名 | `SectorMonitor` |
| **资金异动监控** | 主力净流入 · 北向资金（沪深港通）| `MoneyMonitor` |
| **热搜监控** | 东方财富 + 百度 + 腾讯，三源聚合 | `HotSearchMonitor` |

### 规划中（P3 + P4）

- 🖥️ Streamlit 8页 Web UI（大盘总览/个股详情/策略信号/基金筛选/板块异动/资金流向/热搜/AI评分）
- 🛡️ 仓位管理 · 动态更新 · 止损止盈规则引擎
- 📲 飞书推送通知（信号/异动/每日复盘）
- 📊 每日自动复盘报告

---

## 🛠️ 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.14 |
| 数据库 | MySQL 8.x（`db_stockeagle`，11张表） |
| Web | Streamlit（前端）+ FastAPI（API） |
| 数据源 | AKShare（主）/ westock-data（备）/ BaoStock（历史）/ Ashare / efinance |
| 推送 | 飞书 Webhook |
| 技术指标 | `ta >= 0.11`（pandas-ta 不支持 Python 3.14） |

---

## 📂 项目结构

```
stock-eagle/
├── app/
│   ├── api/                # FastAPI 路由（strategy / tracker）
│   ├── data/               # 数据源封装（akshare_source / data_service）
│   ├── intelligence/       # 智能模块（scorer / dragon_tiger）
│   ├── models/             # 数据模型（SQLAlchemy ORM）
│   ├── notify/             # 推送通知（飞书）
│   ├── scheduler/          # 定时任务调度
│   ├── strategy/           # 策略层（technical / multi_factor / combine / fund_screener）
│   ├── tracker/            # 追踪模块（sector_monitor / money_monitor / hot_search）
│   ├── config.py           # 全局配置
│   ├── database.py         # 数据库连接
│   └── main.py             # FastAPI 入口
├── web/                    # Streamlit 前端（P3 开发中）
├── scripts/                # 工具脚本（初始化/导入数据）
├── tests/                  # 测试文件
│   ├── test_technical.py
│   ├── test_strategy.py
│   ├── test_combined.py
│   └── test_fund_screener.py
├── docs/                   # 设计文档
├── requirements.txt
├── LICENSE
└── README.md
```

---

## 🚀 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/stock-eagle.git
cd stock-eagle

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置数据库（MySQL 8.x）
# 修改 app/config.py 中的数据库连接信息
# 默认：mysql://root:123456@127.0.0.1:3306/db_stockeagle

# 4. 初始化数据库（11张表）
python scripts/init_db.py

# 5. 运行测试，验证功能
python tests/test_technical.py
python tests/test_strategy.py
python tests/test_combined.py
python tests/test_fund_screener.py

# 6. 启动 API 服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 7. 启动 Web UI（P3 完成后）
streamlit run web/app.py
```

---

## 📖 使用示例

### 单策略回测

```python
from app.strategy.technical import MACDStrategy
from datetime import date, timedelta

macd = MACDStrategy()
end = date.today()
start = end - timedelta(days=365)
result = macd.backtest("sh600519", start, end)
print(f"总收益率: {result['total_return']:.2f}%")
print(f"最大回撤: {result['max_drawdown']:.2f}%")
```

### 多策略组合（投票机制）

```python
from app.strategy.combine import CombinedStrategy
from app.strategy.technical import MACDStrategy, BollingerBandStrategy, MAStrategy

strategies = [MACDStrategy(), BollingerBandStrategy(), MAStrategy()]
combined = CombinedStrategy(strategies, voting_rule="majority")
result = combined.backtest("sz000063", start, end)
```

### AI 综合评分

```python
from app.intelligence.scorer import StockScorer

scorer = StockScorer()
result = scorer.score("sh600519")
print(result["total_score"], result["recommendation"])
```

### 龙虎榜解读

```python
from app.intelligence.dragon_tiger import DragonTigerAnalyzer

analyzer = DragonTigerAnalyzer()
summary = analyzer.get_lhb_summary("2026-05-04")
```

---

## 📊 数据库表结构

| 表名 | 说明 |
|------|------|
| `t_stock_basic` | 股票基础信息 |
| `t_stock_daily` | 日线行情 |
| `t_stock_realtime` | 实时行情 |
| `t_stock_money_flow` | 个股资金流向 |
| `t_fund_basic` | 基金基础信息 |
| `t_fund_nav` | 基金净值历史 |
| `t_sector_daily` | 板块日线数据 |
| `t_dragon_tiger` | 龙虎榜数据 |
| `t_daily_review` | 每日复盘记录 |
| `t_portfolio` | 持仓记录 |
| `t_strategy_signal` | 策略信号记录 |

---

## 📋 免责声明

⚠️ **本系统仅供学习研究使用，不构成任何投资建议。投资有风险，入市需谨慎。**

---

## 📄 License

MIT
