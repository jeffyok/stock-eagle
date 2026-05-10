"""
📰 每日复盘页面（P4）
展示历史复盘报告 + 手动触发复盘生成
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from datetime import date, datetime
from web.utils import apply_style

apply_style()
st.title("📰 每日复盘")


# ── 后端可用性检测 ─────────────────────────────────────────────
def _service_ok():
    try:
        from app.models.review import DailyReview
        from app.data.akshare_source import AKShareSource
        from app.notify import push_daily_review
        return True
    except Exception:
        return False


if not _service_ok():
    st.error("后端模块未就绪，请在 app/models/ 和 app/notify/ 完成模块开发")
    st.stop()


from app.models.review import DailyReview
from app.database import SessionLocal
from app.notify import push_daily_review
from app.config import settings

# ── 手动触发复盘生成 ──────────────────────────────────────────
st.subheader("生成今日复盘")
c1, c2 = st.columns([1, 3])
with c1:
    if st.button("🔄 立即生成今日复盘", type="primary", use_container_width=True):
        with st.spinner("正在生成复盘报告…"):
            try:
                from app.scheduler.jobs import daily_review_task
                daily_review_task(push=False)
                st.success("✅ 今日复盘已生成！可点击下方按钮推送到飞书。")
                st.rerun()
            except Exception as e:
                st.error(f"生成失败：{e}")
with c2:
    st.caption("触发后自动推送飞书（需配置 FEISHU_WEBHOOK_URL）")

st.markdown("---")

# ── 历史复盘列表 ───────────────────────────────────────────────
st.subheader("历史复盘")

db = SessionLocal()
try:
    reviews = db.query(DailyReview).order_by(DailyReview.review_date.desc()).all()
finally:
    db.close()

if not reviews:
    st.info("暂无复盘记录，点击上方按钮生成今日复盘。")
    st.stop()

# 选择复盘日期
review_options = {r.review_date.strftime("%Y-%m-%d"): r for r in reviews}
selected_date = st.selectbox(
    "选择复盘日期：",
    options=list(review_options.keys()),
    index=0,
)

review = review_options[selected_date]
content = review.market_trend or "（无内容）"

# ── 展示复盘报告 ──────────────────────────────────────────────
st.markdown("### 📊 复盘报告内容")

# 用 st.markdown 渲染（内容是 Markdown 格式）
for line in content.split("\n"):
    if line.startswith("━━"):
        st.divider()
    elif line.startswith("📰") or line.startswith("📅"):
        st.markdown(f"**{line}**")
    else:
        st.markdown(line)

st.markdown("---")

# ── 推送按钮 ─────────────────────────────────────────────────
if settings.FEISHU_WEBHOOK_URL:
    if st.button("📲 推送此报告到飞书", use_container_width=True):
        with st.spinner("正在推送…"):
            ok = push_daily_review(content)
            if ok:
                st.success("✅ 推送成功！")
            else:
                st.error("❌ 推送失败，请检查 Webhook URL 配置")
else:
    st.warning("⚠️ 未配置 FEISHU_WEBHOOK_URL，无法推送。请在 .env 中配置。")
    if st.button("📲 推送此报告到飞书（演示）", disabled=True):
        pass
