# StockEagle 🦅

**StockEagle** — 开源量化智能选股选基系统

> 仓库地址: https://github.com/yourusername/stock-eagle

> 用数据和策略替代情绪，用信号和规则替代直觉。

## 功能模块

| 模块 | 说明 |
|------|------|
| 🎯 策略选股 | 多因子选股 + 技术策略 + 回测验证 |
| 🧠 智能推荐 | AI综合评分 + 龙虎榜解读 + 机构跟踪 |
| 🔥 风口追踪 | 板块异动 + 资金异动 + 热搜监控 |
| 💰 基金筛选 | 多维度筛选 + 净值跟踪 + ETF分析 |
| 📋 持仓管理 | 持仓监控 + 止盈止损 + 收益分析 |
| 📉 回测验证 | 历史回测 + 收益曲线 + 风险指标 |
| 📰 每日复盘 | 自动复盘 + 操作建议 |

## 技术栈

- **语言**: Python 3.14
- **数据库**: MySQL 8.x
- **Web**: Streamlit + FastAPI
- **数据源**: AKShare / westock-data / BaoStock / Ashare / efinance（全免费）

## 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/stock-eagle.git
cd stock-eagle

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置数据库
# 修改 .env 文件中的 MySQL 连接信息

# 4. 初始化数据库
python scripts/init_db.py

# 5. 导入历史数据
python scripts/import_data.py

# 6. 启动 Web UI
streamlit run web/app.py

# 7. 启动 API 服务（可选）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 项目结构

```
stock-eagle/
├── app/             # Python 包（后端服务 / FastAPI）
├── web/             # Streamlit 前端
├── scripts/         # 工具脚本
├── tests/           # 测试
└── requirements.txt # 依赖
```

## License

MIT

---

_⚠️ 免责声明：本系统仅供学习研究使用，不构成任何投资建议。投资有风险，入市需谨慎。_
