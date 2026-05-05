"""
📋 持仓管理页面（P4）
CRUD + 实时行情 + 盈亏计算
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from datetime import date
from decimal import Decimal
from web.utils import apply_style, style_pct_series

apply_style()


# ── 后端可用检测 ─────────────────────────────────────────────────
def _service():
    try:
        from app.portfolio.service import (
            get_positions, enrich_with_realtime,
            add_position, delete_position, update_position,
        )
        return True
    except Exception:
        return False


if not _service():
    st.error("后端模块未就绪，请在 app/portfolio/ 目录下完成模块开发")
    st.stop()


from app.portfolio.service import (
    get_positions, enrich_with_realtime,
    add_position, delete_position, update_position, get_position,
)
from app.portfolio import Portfolio


st.title("📋 持仓管理")

# ── 顶部操作栏 ─────────────────────────────────────────────────────
c_add, c_refresh, _ = st.columns([1, 1, 4])
with c_add:
    if st.button("➕ 新增持仓", use_container_width=True):
        st.session_state["show_add"] = True
with c_refresh:
    if st.button("🔄 刷新行情", use_container_width=True):
        st.session_state["refresh"] = True

if "show_add" not in st.session_state:
    st.session_state["show_add"] = False

# ── 新增持仓表单 ────────────────────────────────────────────────────
if st.session_state.get("show_add"):
    with st.form("add_form", clear_on_submit=True):
        st.subheader("新增持仓")
        code = st.text_input("股票代码（如 sh600519）", value="sh600519")
        name = st.text_input("股票名称", value="贵州茅台")
        cost = st.number_input("持仓成本（元/股）", min_value=0.01, value=1680.0, step=1.0)
        quantity = st.number_input("持仓数量（股）", min_value=1, value=100, step=100)
        buy_date = st.date_input("买入日期", value=date.today())
        stop_loss = st.number_input("止损价（元，留空不设置）", min_value=0.0, value=0.0, step=1.0)
        take_profit = st.number_input("止盈价（元，留空不设置）", min_value=0.0, value=0.0, step=1.0)
        note = st.text_input("备注", value="")
        submitted = st.form_submit_button("确认添加")
        if submitted:
            sl = None if stop_loss == 0.0 else stop_loss
            tp = None if take_profit == 0.0 else take_profit
            new_id = add_position(
                code=code, name=name, cost=cost, quantity=int(quantity),
                buy_date=str(buy_date), stop_loss=sl, take_profit=tp, note=note or None,
            )
            if new_id:
                st.success(f"添加成功！ID: {new_id}")
                st.session_state["show_add"] = False
                st.rerun()
            else:
                st.error("添加失败，请检查输入")

# ── 加载持仓 + 实时行情 ────────────────────────────────────────────
with st.spinner("加载持仓数据…"):
    positions = get_positions()
    positions = enrich_with_realtime(positions)


if not positions:
    st.info("暂无持仓记录，点击「新增持仓」开始添加。")
    st.stop()

# ── 账户总览 ──────────────────────────────────────────────────────
total_cost = sum(p.cost * p.quantity for p in positions)
total_mv = sum(p.market_value() or 0 for p in positions)
total_pl = total_mv - total_cost
total_pl_pct = (total_pl / total_cost * 100) if total_cost > 0 else 0

oc1, oc2, oc3, oc4 = st.columns(4)
oc1.metric("账户总市值", f"¥{total_mv:,.2f}")
oc2.metric("持仓总成本", f"¥{total_cost:,.2f}")
oc3.metric("浮动盈亏", f"¥{total_pl:+,.2f}",
            delta=f"{total_pl_pct:+.2f}%" if total_cost > 0 else None)
oc4.metric("持仓数量", f"{len(positions)} 只")

st.markdown("---")

# ── 持仓明细（表格 + 行内单选）────────────────────────────────
st.subheader("持仓明细")

radio_key = "portfolio_radio"

# 初始化默认选中第一行
if radio_key not in st.session_state:
    st.session_state[radio_key] = 0

# radio 选项：每一行显示一个持仓（代码 + 名称）
radio_options = list(range(len(positions)))
radio_labels = [f"{p.code}  {p.name}" for p in positions]

# 用 st.radio 实现单选，放在表格上方
sel_idx = st.radio(
    "选择持仓（点击单选）：",
    options=radio_options,
    format_func=lambda i: radio_labels[i],
    index=st.session_state[radio_key],
    horizontal=True,
    key=radio_key,
)

selected_pos = positions[sel_idx]

# 表格数据（不含单选列，高亮选中行）
rows = []
for i, p in enumerate(positions):
    mv = p.market_value()
    pl = p.profit_loss()
    pl_pct = p.profit_loss_pct()
    rows.append({
        "代码": p.code,
        "名称": p.name,
        "成本（元）": f"{p.cost:.2f}",
        "现价（元）": f"{p.current_price():.2f}" if p.current_price() else "N/A",
        "数量（股）": f"{p.quantity:,}",
        "市值（元）": f"{mv:,.2f}" if mv else "N/A",
        "盈亏（元）": f"{pl:+,.2f}" if pl is not None else "N/A",
        "盈亏（%）": f"{pl_pct:+.2f}%" if pl_pct is not None else "N/A",
        "止损价": f"{p.stop_loss:.2f}" if p.stop_loss else "-",
        "止盈价": f"{p.take_profit:.2f}" if p.take_profit else "-",
    })

df_display = pd.DataFrame(rows)

# 高亮选中行
def _highlight_row(row):
    idx = row.name  # DataFrame 行索引
    if idx == sel_idx:
        return ["background-color: #c8e6c9"] * len(row)
    return [""] * len(row)

styled = df_display.style.apply(_highlight_row, axis=1)
st.dataframe(styled, use_container_width=True, hide_index=True)

st.caption(f"📌 已选：{selected_pos.name}（{selected_pos.code}）")

# ── 操作按钮（放持仓明细下面）──────────────────────────────────────
ec1, ec2, ec3 = st.columns(3)

with ec1:
    del_key = f"confirm_del_{selected_pos.id}"
    if st.button("🗑️ 删除持仓", use_container_width=True, key="btn_del"):
        st.session_state[del_key] = True

    # 确认提示
    if st.session_state.get(del_key):
        st.warning(f"⚠️ 确认删除「{selected_pos.name}（{selected_pos.code}）」？此操作不可撤销！")
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("✅ 确认删除", key="btn_del_confirm", use_container_width=True):
                if delete_position(selected_pos.id):
                    st.success(f"已删除 {selected_pos.name}（{selected_pos.code}）")
                    del st.session_state[del_key]
                    st.rerun()
                else:
                    st.error("删除失败")
        with cc2:
            if st.button("❌ 取消", key="btn_del_cancel", use_container_width=True):
                del st.session_state[del_key]
                st.rerun()

with ec2:
    if st.button("✏️ 编辑持仓", use_container_width=True):
        st.session_state["edit_id"] = selected_pos.id
        st.rerun()

with ec3:
    if st.button("🔍 查看预警", type="primary", use_container_width=True):
        st.session_state["show_alerts"] = True
        st.session_state["alert_pos_idx"] = sel_idx

# ── 编辑表单 ────────────────────────────────────────────────────────
if st.session_state.get("edit_id"):
    p = get_position(st.session_state["edit_id"])
    if p:
        with st.form("edit_form"):
            st.subheader(f"✏️ 编辑持仓 — {p.name}（{p.code}）")
            new_cost = st.number_input("持仓成本（元/股）", min_value=0.01, value=float(p.cost), step=1.0)
            new_quantity = st.number_input("持仓数量（股）", min_value=1, value=p.quantity, step=100)
            new_sl = st.number_input("止损价（元，0=不设置）", min_value=0.0, value=float(p.stop_loss or 0), step=1.0)
            new_tp = st.number_input("止盈价（元，0=不设置）", min_value=0.0, value=float(p.take_profit or 0), step=1.0)
            new_note = st.text_input("备注", value=p.note or "")
            if st.form_submit_button("💾 保存修改"):
                update_position(
                    p.id,
                    cost=float(new_cost),
                    quantity=int(new_quantity),
                    stop_loss=None if new_sl == 0 else new_sl,
                    take_profit=None if new_tp == 0 else new_tp,
                    note=new_note or None,
                )
                st.success("✅ 修改成功！")
                del st.session_state["edit_id"]
                st.rerun()
        if st.button("❌ 取消编辑"):
            del st.session_state["edit_id"]
            st.rerun()
    else:
        st.error("未找到该持仓")
        del st.session_state["edit_id"]

# ── 预警面板 ────────────────────────────────────────────────────────
if st.session_state.get("show_alerts"):
    st.markdown("#### 🚨 风控预警")
    try:
        from app.risk import check_portfolio
        alert_idx = st.session_state.get("alert_pos_idx", 0)
        target_pos = [positions[alert_idx]]
        alerts = check_portfolio(target_pos)
        if not alerts:
            st.success("✅ 该持仓无风控预警")
        else:
            for a in alerts:
                if a.level == "red":
                    st.error(f"🔴 {a.name}（{a.code}）— {a.rule}：{a.current_val}")
                elif a.level == "yellow":
                    st.warning(f"🟡 {a.name}（{a.code}）— {a.rule}：{a.current_val}")
                else:
                    st.info(f"🟢 {a.name}（{a.code}）— {a.rule}：{a.current_val}")
    except Exception as e:
        st.error(f"风控引擎加载失败：{e}")
    if st.button("🔙 返回持仓列表"):
        del st.session_state["show_alerts"]
        st.rerun()
