#!/usr/bin/env python3
import asyncio
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from database import AsyncTinyDB
from metrics import Metrics


def render_live_websocket_widget():
    """Renders an isolated real-time WebSocket client card that updates via DOM manipulation without Python reruns."""
    widget_html = """
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 16px; background: #ffffff; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <h4 style="margin: 0; color: #1e293b; font-size: 16px;">Live WebSocket Telemetry Feed</h4>
            <span id="ws-status" style="font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 12px; background: #fef3c7; color: #d97706;">Connecting...</span>
        </div>
        <div id="ws-live-content" style="font-family: monospace; font-size: 13px; color: #334155; background: #f8fafc; padding: 12px; border-radius: 6px; border: 1px solid #f1f5f9; height: 140px; overflow-y: auto;">
            Waiting for real-time payloads from server...
        </div>
    </div>

    <script>
        // Streamlit renders this HTML inside an iframe, whose own host may be empty.
        const appUrl = new URL(document.referrer || window.location.href);
        const wsUrl = `${appUrl.protocol === 'https:' ? 'wss:' : 'ws:'}//${appUrl.host}/ws/telemetry`;
        const ws = new WebSocket(wsUrl);

        const statusBadge = document.getElementById('ws-status');
        const contentBox = document.getElementById('ws-live-content');

        ws.onopen = function() {
            statusBadge.style.background = '#dcfce7';
            statusBadge.style.color = '#16a34a';
            statusBadge.innerText = 'Connected Live';
        };

        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            const timeStr = new Date().toLocaleTimeString();
            
            let metricsHtml = `<div style="margin-bottom: 6px; border-bottom: 1px dashed #e2e8f0; padding-bottom: 4px;">`;
            metricsHtml += `<strong style="color: #0284c7;">[${timeStr}] MAC: ${data.mac_address}</strong><br>`;
            
            for (const [key, value] of Object.entries(data.content)) {
                metricsHtml += `&nbsp;&nbsp;<code>${key}</code>: <b>${value}</b> `;
            }
            metricsHtml += `</div>`;
            
            // Prepend latest message to top of box
            contentBox.innerHTML = metricsHtml + contentBox.innerHTML;
        };

        ws.onclose = function() {
            statusBadge.style.background = '#fee2e2';
            statusBadge.style.color = '#dc2626';
            statusBadge.innerText = 'Disconnected';
        };
    </script>
    """
    st.iframe(widget_html, height=210)

st.set_page_config(
    page_title="COP-3604 Linux Infrastructure Observability Dashboard",
    layout="wide",
)

st.title("COP-3604 Linux Infrastructure Observability Dashboard")


async def load_mac_addresses(db: AsyncTinyDB) -> list[str]:
    """Safely extract unique MAC addresses from TinyDB tag values."""
    raw_tags = await db.get_mac_addresses()
    # TinyDB get_tag_values() returns a dict {'mac-address': [...]}
    if isinstance(raw_tags, dict):
        return raw_tags.get(db.mac_address_tag, [])
    if isinstance(raw_tags, list):
        return raw_tags
    return []


def points_to_dataframe(points: list) -> pd.DataFrame:
    """Convert TinyDB Point objects into a sorted Pandas DataFrame."""
    rows = []
    for pt in points:
        def value(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            try:
                return obj[key]
            except (KeyError, TypeError, AttributeError, IndexError):
                return getattr(obj, key, default)

        raw_time = value(pt, "time")
        if raw_time is None:
            raw_time = value(pt, "timestamp", value(pt, "_time"))
        if raw_time is None:
            continue
        datetime_value = pd.to_datetime(raw_time, errors="coerce")
        if pd.isna(datetime_value):
            continue

        tags = value(pt, "tags", {}) or {}
        fields = value(pt, "fields", {}) or {}
        if not isinstance(tags, dict):
            tags = {}
        if not isinstance(fields, dict):
            fields = {}

        row = {
            "timestamp": datetime_value.to_pydatetime().astimezone().strftime("%B %d, %Y %I:%M %p"),
            "shorttime": datetime_value.to_pydatetime().astimezone().strftime("%m-%d %I:%M %p"),
            "datetime": datetime_value,
        }
        row.update(fields)
        for metric in Metrics:
            metric_name = str(metric)
            metric_value = value(pt, metric_name)
            if metric_value is not None and metric_name not in row:
                row[metric_name] = metric_value
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values("datetime").reset_index(drop=True)
    for metric in Metrics:
        if str(metric) not in df.columns:
            df[str(metric)] = 0.0
    return df


render_live_websocket_widget()

# Re-instantiate TinyDB on each run to read fresh rows appended by dashboard.py
db = AsyncTinyDB()
mac_list = asyncio.run(load_mac_addresses(db))

# --- Sidebar Controls ---
st.sidebar.header("Server & Time Window")

if not mac_list:
    st.warning(
        "No server telemetry found in `database.csv` yet. "
        "Start `dashboard.py` and run `collectors.py` to populate metrics."
    )
    if st.button("Retry / Refresh"):
        st.rerun()
    st.stop()

selected_mac = st.sidebar.selectbox("Select Monitored Server (MAC)", mac_list)
hours_past = st.sidebar.slider("Historical Window (Hours)", min_value=1, max_value=72, value=12)

st.sidebar.markdown("---")
st.sidebar.header("Alert Thresholds")
cpu_threshold = st.sidebar.slider("CPU Usage Threshold (%)", 10, 100, 80)
mem_threshold = st.sidebar.slider("Memory Usage Threshold (%)", 10, 100, 80)
storage_threshold = st.sidebar.slider("Storage Usage Threshold (%)", 10, 100, 85)
load_threshold = st.sidebar.slider("System Load (1m) Threshold", 0.5, 16.0, 2.5, step=0.5)
time_threshold_minutes = st.sidebar.slider("Time Check Threshold (minutes)", 5, 60, 10, step=1)

# Query data from TinyDB
points = asyncio.run(db.query_data(selected_mac, hours_past=hours_past))
df = points_to_dataframe(points)

if df.empty:
    st.info(f"No data points recorded for `{selected_mac}` in the last {hours_past} hour(s).")
    st.stop()

latest = df.iloc[-1]

# Notification System (Threshold Alerts)
alerts = []
if latest[Metrics.CPU] >= cpu_threshold:
    alerts.append(f"**CPU Usage** is at `{latest[Metrics.CPU]:.1f}%` (Threshold: `{cpu_threshold}%`)")
if latest[Metrics.MEMORY] >= mem_threshold:
    alerts.append(f"**Memory Usage** is at `{latest[Metrics.MEMORY]:.1f}%` (Threshold: `{mem_threshold}%`)")
if latest[Metrics.STORAGE] >= storage_threshold:
    alerts.append(f"**Storage Usage** is at `{latest[Metrics.STORAGE]:.1f}%` (Threshold: `{storage_threshold}%`)")
if latest[Metrics.LOAD] >= load_threshold:
    alerts.append(f"**System Load** is at `{latest[Metrics.LOAD]:.2f}` (Threshold: `{load_threshold}`)")

if alerts:
    for alert_msg in alerts:
        st.error(f"**ALERT [{selected_mac}]**: {alert_msg}")
else:
    st.success(f"**Server `{selected_mac}` Healthy** — All metrics are below alert thresholds.")

# Key Performance Metrics
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    cpu_val: float = latest[Metrics.CPU]
    st.metric(
        "CPU Usage",
        f"{cpu_val:.1f}%",
        delta="OVER THRESHOLD" if cpu_val >= cpu_threshold else "Normal",
        delta_color="inverse" if cpu_val >= cpu_threshold else "normal",
    )
with col2:
    mem_val: float = latest[Metrics.MEMORY]
    st.metric(
        "Memory (RAM)",
        f"{mem_val:.1f}%",
        delta="OVER THRESHOLD" if mem_val >= mem_threshold else "Normal",
        delta_color="inverse" if mem_val >= mem_threshold else "normal",
    )
with col3:
    sto_val: float = latest[Metrics.STORAGE]
    st.metric(
        "Disk Storage",
        f"{sto_val:.1f}%",
        delta="OVER THRESHOLD" if sto_val >= storage_threshold else "Normal",
        delta_color="inverse" if sto_val >= storage_threshold else "normal",
    )
with col4:
    net_val = latest[Metrics.NETWORK]
    st.metric("Network I/O (Total)", f"{net_val:.2f} MB")
with col5:
    load_val: float = latest[Metrics.LOAD]
    st.metric(
        "System Load (1m)",
        f"{load_val:.2f}",
        delta="OVER THRESHOLD" if load_val >= load_threshold else "Normal",
        delta_color="inverse" if load_val >= load_threshold else "normal",
    )
with col6:
    time_val = latest["shorttime"]
    time_age_minutes = (
        pd.Timestamp.now(tz="UTC")
        - pd.to_datetime(latest["datetime"], utc=True)
    ).total_seconds() / 60
    st.metric(
        "Last Check",
        f"{time_val}",
        delta="OVER THRESHOLD" if time_age_minutes >= time_threshold_minutes else "Normal",
        delta_color="inverse" if time_age_minutes >= time_threshold_minutes else "normal",
    )

st.markdown("---")

# Real-Time & Historical Data Visualizations
tab_realtime, tab_historical, tab_raw = st.tabs([
    "Real-Time Telemetry (Last 25 Samples)",
    f"Historical Trends (Last {hours_past}h)",
    "Raw TinyDB Records",
])

with tab_realtime:
    recent_df = df.tail(25)
    c1, c2 = st.columns(2)

    with c1:
        fig_rt_util = go.Figure()
        fig_rt_util.add_trace(go.Scatter(
            x=recent_df["shorttime"], y=recent_df[Metrics.CPU],
            mode="lines+markers", name="CPU %"
        ))
        fig_rt_util.add_trace(go.Scatter(
            x=recent_df["shorttime"], y=recent_df[Metrics.MEMORY],
            mode="lines+markers", name="Memory %"
        ))
        fig_rt_util.add_hline(
            y=cpu_threshold, line_dash="dash", line_color="red",
            annotation_text=f"CPU Limit ({cpu_threshold}%)"
        )
        fig_rt_util.add_hline(
            y=mem_threshold, line_dash="dot", line_color="orange",
            annotation_text=f"RAM Limit ({mem_threshold}%)"
        )
        fig_rt_util.update_layout(
            title="Real-Time CPU & Memory Usage (%)",
            xaxis_title="time",
            yaxis=dict(title="Percent (%)", range=[0, 105]),
            height=370,
        )
        st.plotly_chart(fig_rt_util, width='stretch')

    with c2:
        fig_rt_load = go.Figure()
        fig_rt_load.add_trace(go.Scatter(
            x=recent_df["shorttime"], y=recent_df[Metrics.LOAD],
            mode="lines+markers", name="1m Load Avg"
        ))
        fig_rt_load.add_hline(
            y=load_threshold, line_dash="dash", line_color="red",
            annotation_text=f"Load Threshold ({load_threshold})"
        )
        fig_rt_load.update_layout(
            title="Real-Time System Load Average",
            xaxis_title="time",
            yaxis_title="Load",
            height=370,
        )
        st.plotly_chart(fig_rt_load, width='stretch')

with tab_historical:
    h1, h2 = st.columns(2)
    with h1:
        fig_hist_pct = px.line(
            df,
            x="shorttime",
            y=[Metrics.CPU, Metrics.MEMORY, Metrics.STORAGE],
            title=f"Historical CPU, Memory & Storage (%) — Last {hours_past}h",
            labels={"value": "Usage (%)", "time": "Time", "variable": "Metric"},
        )
        fig_hist_pct.update_layout(yaxis=dict(range=[0, 105]), height=370)
        st.plotly_chart(fig_hist_pct, width='stretch')

    with h2:
        fig_hist_net = px.area(
            df,
            x="shorttime",
            y=Metrics.NETWORK,
            title=f"Historical Cumulative Network Traffic (MB) — Last {hours_past}h",
            labels={Metrics.NETWORK: "Megabytes (MB)", "time": "Time"},
        )
        fig_hist_net.update_layout(height=370)
        st.plotly_chart(fig_hist_net, width='stretch')

with tab_raw:
    st.dataframe(df.iloc[::-1], width='stretch')
