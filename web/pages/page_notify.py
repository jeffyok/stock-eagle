"""
📢 推送管理页面（P4）
查看推送记录、测试推送、配置 Webhook、自动推送
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
        from app.notify import push_text, push_markdown, get_push_history, save_webhook_url
        from app.risk import check_portfolio
        from app.portfolio.service import get_positions, enrich_with_realtime
        from app.config import settings
        return True, ""
    except Exception as e:
        return False, str(e)


ok, err_msg = _service_ok()
if not ok:
    st.error(f"后端模块未就绪：{err_msg}")
    st.stop()


from app.notify import push_text, push_markdown, get_push_history, save_webhook_url, push_portfolio_alerts
from app.risk import check_portfolio
from app.portfolio.service import get_positions, enrich_with_realtime
from app.config import settings


st.title("📢 推送管理")

# ── 推送配置 ─────────────────────────────────────────────────────
st.subheader("推送配置")

# 读取已保存的 URL
saved_url = getattr(settings, "FEISHU_WEBHOOK_URL", "") or ""

webhook = st.text_input(
    "飞书 Webhook URL",
    value=saved_url,
    type="password",
    help="在飞书群设置 → 群机器人 → 添加机器人 中获取 Webhook URL",
)

c_save, c_status = st.columns([1, 3])
with c_save:
    if st.button("💾 保存 URL", use_container_width=True):
        if webhook:
            if save_webhook_url(webhook):
                st.success("URL 已保存到 .env，重启后生效！")
                st.info("如需立即生效，请在配置文件中手动设置后重启服务")
            else:
                st.error("保存失败，请检查文件权限")
        else:
            st.warning("URL 不能为空")

with c_status:
    if saved_url:
        st.success("✅ Webhook URL 已配置")
    else:
        st.warning("⚠️ 尚未配置 Webhook URL")

st.markdown("---")

# ── 自动推送设置 ─────────────────────────────────────────────────
st.subheader("⏰ 自动推送")
st.info("定时推送由系统自动化任务执行。当前 Webhook URL 保存后，每日 16:00（收盘后）自动推送持仓预警。")

c_now, c_alert = st.columns(2)

with c_now:
    if st.button("📤 立即推送持仓预警", type="primary", use_container_width=True):
        if not webhook:
            st.warning("请先配置并保存 Webhook URL")
        else:
            with st.spinner("正在检查持仓..."):
                positions = get_positions()
                positions = enrich_with_realtime(positions)
                ok = push_portfolio_alerts(positions, webhook_url=webhook)
                if ok:
                    st.success("✅ 推送成功！")
                else:
                    st.error("推送失败，请检查 URL 或网络")

with c_alert:
    test_text = st.text_input("测试文本", value="✅ StockEagle 推送测试成功！")
    if st.button("📤 推送测试文本", use_container_width=True):
        if not webhook:
            st.warning("请先配置并保存 Webhook URL")
        else:
            ok = push_text(test_text, webhook_url=webhook)
            st.success("推送成功！") if ok else st.error("推送失败，请检查 URL")

st.markdown("---")

# ── 推送记录 ─────────────────────────────────────────────────────
st.subheader("📋 推送记录")
try:
    history = get_push_history(limit=50)
    if not history:
        st.info("暂无推送记录")
    else:
        rows = []
        for row in history:
            rows.append({
                "ID": row[0],
                "类型": row[1],
                "标题": row[2][:30],
                "状态": "✅ 成功" if row[3] == "success" else "❌ 失败",
                "时间": str(row[5])[:19],
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
except Exception as e:
    st.error(f"读取推送记录失败：{e}")
