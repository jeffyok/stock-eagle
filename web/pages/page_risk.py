"""
🛡️ 风控规则配置页面（P4）
可配置的规则列表 + 实时风控检查
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from web.utils import apply_style

apply_style()


def _service_ok():
    try:
        from app.risk import get_rules, update_rule, check_portfolio
        from app.portfolio.service import get_positions, enrich_with_realtime
        return True
    except Exception:
        return False


if not _service_ok():
    st.error("后端模块未就绪，请在 app/risk/ 目录下完成模块开发")
    st.stop()


from app.risk import get_rules, update_rule, check_portfolio
from app.portfolio.service import get_positions, enrich_with_realtime


st.title("🛡️ 风控管理")

# ── 规则配置区 ──────────────────────────────────────────────────────
st.subheader("风控规则配置")

try:
    rules = get_rules()
except Exception as e:
    st.error(f"规则读取失败：{e}")
    st.stop()

# 按类型分组展示
st.markdown("**数值型规则**（阈值）")
num_cols = ["规则名称", "当前值", "单位", "启用", "操作"]
num_rows = []
for key, meta in rules.items():
    if meta["type"] == "number":
        num_rows.append({
            "rule_key": key,
            "规则名称": meta["name"],
            "当前值": meta["value"],
            "单位": "%" if "pct" in key else "",
            "启用": meta["enabled"],
        })

if num_rows:
    edited = st.data_editor(
        num_rows,
        column_config={
            "rule_key": None,
            "规则名称": st.column_config.TextColumn("规则名称", disabled=True),
            "当前值": st.column_config.NumberColumn("当前值", min_value=0, max_value=100),
            "单位": st.column_config.TextColumn("单位", disabled=True),
            "启用": st.column_config.CheckboxColumn("启用"),
        },
        width='stretch',
        hide_index=True,
        key="risk_rules_editor",
    )
    if st.button("💾 保存修改", type="primary"):
        for row in edited:
            update_rule(row["rule_key"], str(row["当前值"]), row["启用"])
        st.success("规则保存成功！")
        st.rerun()
else:
    st.info("暂无数值型规则")

st.markdown("**开关型规则**（报警开关）")
sw_cols = ["规则名称", "状态", "说明", "启用"]
sw_rows = []
for key, meta in rules.items():
    if meta["type"] == "switch":
        sw_rows.append({
            "rule_key": key,
            "规则名称": meta["name"],
            "状态": "开启" if meta["enabled"] else "关闭",
            "说明": meta.get("description", ""),
            "启用": meta["enabled"],
        })

if sw_rows:
    sw_edited = st.data_editor(
        sw_rows,
        column_config={
            "rule_key": None,
            "规则名称": st.column_config.TextColumn("规则名称", disabled=True),
            "状态": st.column_config.TextColumn("状态", disabled=True),
            "说明": st.column_config.TextColumn("说明", disabled=True),
            "启用": st.column_config.CheckboxColumn("启用"),
        },
        width='stretch',
        hide_index=True,
        key="risk_switch_editor",
    )
    if st.button("💾 保存开关设置"):
        for row in sw_edited:
            update_rule(row["rule_key"], "1" if row["启用"] else "0", row["启用"])
        st.success("开关设置保存成功！")
        st.rerun()

st.markdown("---")

# ── 实时风控检查 ───────────────────────────────────────────────────
st.subheader("实时风控检查")

if st.button("🔍 立即检查", type="primary", width='stretch'):
    with st.spinner("正在检查持仓…"):
        try:
            positions = get_positions()
            positions = enrich_with_realtime(positions)
            alerts = check_portfolio(positions)
            if not alerts:
                st.success("✅ 暂无预警，一切正常！")
            else:
                st.error(f"⚠️ 发现 {len(alerts)} 条预警，请关注！")
                for a in alerts:
                    if a.level == "red":
                        st.error(f"🔴 [{a.rule}] {a.name}({a.code}) — {a.current_val}（阈值：{a.threshold}）")
                    elif a.level == "yellow":
                        st.warning(f"🟡 [{a.rule}] {a.name}({a.code}) — {a.current_val}（阈值：{a.threshold}）")
                    else:
                        st.success(f"🟢 [{a.rule}] {a.name}({a.code}) — {a.current_val}（阈值：{a.threshold}）")
        except Exception as e:
            st.error(f"检查失败：{e}")
else:
    st.info("点击「立即检查」对当前持仓进行风控扫描")
