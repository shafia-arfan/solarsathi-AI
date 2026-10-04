
import os
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from config import DEMO_SCENARIOS, DEFAULT_GEMINI_MODEL
from tools.validation import validate_telemetry_dict
from tools.batch_tools import process_batch_telemetry
from agents.supervisor import SupervisorAgent
from utils.gemini_client import get_gemini_api_key, generate_natural_explanation
from utils.report_generator import generate_markdown_report

# Page Configuration
st.set_page_config(
    page_title="SolarSathi AI — Microgrid Manager & Health Doctor",
    page_icon="🌞",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .kpi-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 16px;
        border-left: 5px solid #ff9800;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE & INITIALIZATION -----------------
if "supervisor" not in st.session_state:
    st.session_state.supervisor = SupervisorAgent()

if "gemini_explanation" not in st.session_state:
    st.session_state.gemini_explanation = None

if "last_scenario" not in st.session_state:
    st.session_state.last_scenario = "Sunny Day"

# ----------------- SIDEBAR: CONFIG & INPUTS -----------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/solar-panel.png", width=64)
    st.title("SolarSathi Controls")
    
    # Engine Connectivity Status
    api_key_set = bool(get_gemini_api_key())
    if api_key_set:
        st.success("🟢 AI Engine: Gemini Connected")
    else:
        st.warning("🟡 AI Engine: Python Fallback Mode")
        st.caption("Add `GEMINI_API_KEY` to secrets for dynamic LLM reasoning.")

    st.subheader("⚡ Demo Scenarios")
    selected_scenario = st.selectbox(
        "Load Preconfigured State:",
        options=list(DEMO_SCENARIOS.keys()),
        index=0
    )
    
    if selected_scenario != st.session_state.last_scenario:
        st.session_state.last_scenario = selected_scenario
        st.session_state.gemini_explanation = None

    default_vals = DEMO_SCENARIOS[selected_scenario]

    st.markdown("---")
    st.subheader("📊 Live Telemetry Inputs")
    
    pv_input = st.number_input("Solar PV Generation (kW)", min_value=0.0, max_value=50.0, value=float(default_vals["pv_generation_kw"]), step=0.2)
    load_input = st.number_input("Load Demand (kW)", min_value=0.1, max_value=50.0, value=float(default_vals["load_demand_kw"]), step=0.2)
    soc_input = st.slider("Battery SOC (%)", min_value=0.0, max_value=100.0, value=float(default_vals["battery_soc"]), step=1.0)
    batt_cap_input = st.number_input("Battery Capacity (kWh)", min_value=1.0, max_value=100.0, value=float(default_vals["battery_capacity_kwh"]), step=1.0)
    
    with st.expander("🔋 Battery Diagnostic Telemetry", expanded=False):
        age_input = st.number_input("Battery Age (Years)", min_value=0.0, max_value=15.0, value=float(default_vals["battery_age_years"]), step=0.5)
        temp_input = st.number_input("Temperature (°C)", min_value=-10.0, max_value=80.0, value=float(default_vals["battery_temp_c"]), step=1.0)
        ir_input = st.number_input("Internal Resistance (mΩ)", min_value=1.0, max_value=200.0, value=float(default_vals["battery_internal_res_mohm"]), step=1.0)
        rated_ah = st.number_input("Rated Capacity (Ah)", min_value=10.0, max_value=1000.0, value=float(default_vals["rated_capacity_ah"]), step=10.0)
        actual_ah = st.number_input("Actual Capacity (Ah)", min_value=5.0, max_value=1000.0, value=float(default_vals["actual_capacity_ah"]), step=10.0)

    with st.expander("🌐 Grid & EV Telemetry", expanded=False):
        grid_avail = st.toggle("Grid Available", value=bool(default_vals["grid_available"]))
        load_shed = st.toggle("Load-Shedding Active", value=bool(default_vals["load_shedding"]))
        ev_demand = st.number_input("EV Charging Demand (kW)", min_value=0.0, max_value=22.0, value=float(default_vals["ev_demand_kw"]), step=0.5)
        tx_load = st.slider("Transformer Loading (%)", min_value=0.0, max_value=150.0, value=float(default_vals["transformer_loading_pct"]), step=5.0)

telemetry_data = {
    "pv_generation_kw": pv_input,
    "load_demand_kw": load_input,
    "battery_soc": soc_input,
    "battery_capacity_kwh": batt_cap_input,
    "battery_age_years": age_input,
    "battery_temp_c": temp_input,
    "battery_internal_res_mohm": ir_input,
    "rated_capacity_ah": rated_ah,
    "actual_capacity_ah": actual_ah,
    "grid_available": grid_avail,
    "load_shedding": load_shed,
    "ev_demand_kw": ev_demand,
    "transformer_loading_pct": tx_load,
}

# ----------------- EXECUTE DETERMINISTIC MULTI-AGENT WORKFLOW -----------------
validated_telemetry, error_msg = validate_telemetry_dict(telemetry_data)
if error_msg:
    st.error(f"Input Validation Error: {error_msg}")
    st.stop()

results = st.session_state.supervisor.coordinate(validated_telemetry)
solar_res = results["solar"]
battery_res = results["battery"]
grid_res = results["grid"]
plan_res = results["plan"]
was_replanned = results["replanned"]

# ----------------- MAIN UI TABS (MERGED SYSTEM) -----------------
st.title("🌞 SolarSathi AI")
st.markdown("##### *Agentic Solar + Battery Manager & Health Doctor*")

tab_live, tab_batch = st.tabs([
    "⚡ Real-Time Microgrid Dispatch",
    "📈 Batch Simulation & 24h Time-Series"
])

# ----------------- TAB 1: REAL-TIME LIVE DISPATCH -----------------
with tab_live:
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("☀️ Solar PV", f"{validated_telemetry.pv_generation_kw:.1f} kW", delta=solar_res.status)
    kpi2.metric("🏠 Demand", f"{validated_telemetry.load_demand_kw:.1f} kW")
    kpi3.metric("🔋 Battery SOC", f"{validated_telemetry.battery_soc:.0f}%", delta=f"{plan_res.battery_action}")
    kpi4.metric("⚡ Grid State", "Online" if validated_telemetry.grid_available and not validated_telemetry.load_shedding else "Outage")
    soh_color = "normal" if battery_res.status == "Healthy" else "inverse"
    kpi5.metric("❤️ Battery SOH", f"{battery_res.health_score:.0f}/100", delta=battery_res.status, delta_color=soh_color)

    if was_replanned:
        st.warning("⚠️ **Safety Guardrail Interception:** Supervisor re-routed power flows to prevent overload or thermal damage.")

    st.markdown("---")

    col_left, col_right = st.columns([3, 2])
    with col_left:
        st.subheader("⚡ Real-time Power Dispatch")
        flows = plan_res.power_flows
        flow_df = pd.DataFrame({
            "Flow Path": ["Solar ➔ Load", "Solar ➔ Battery", "Battery ➔ Load", "Grid ➔ Load", "Solar ➔ Grid"],
            "Power (kW)": [flows["solar_to_load"], flows["solar_to_battery"], flows["battery_to_load"], flows["grid_to_load"], flows["solar_to_grid"]]
        })
        fig = go.Figure(data=[
            go.Bar(
                x=flow_df["Flow Path"],
                y=flow_df["Power (kW)"],
                marker_color=["#4CAF50", "#2196F3", "#FF9800", "#9C27B0", "#00BCD4"],
                text=flow_df["Power (kW)"],
                textposition='auto',
            )
        ])
        fig.update_layout(height=320, margin=dict(l=20, r=20, t=20, b=20), yaxis_title="Dispatched Power (kW)")
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("🔋 Battery Health Doctor")
        gauge_fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = battery_res.health_score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': f"Status: {battery_res.status}"},
            gauge = {
                'axis': {'range': [0, 100]},
                'bar': {'color': "#2E7D32" if battery_res.status == "Healthy" else ("#F57C00" if battery_res.status == "Warning" else "#D32F2F")},
                'steps': [
                    {'range': [0, 50], 'color': "#FFCDD2"},
                    {'range': [50, 75], 'color': "#FFE0B2"},
                    {'range': [75, 100], 'color': "#C8E6C9"}
                ],
            }
        ))
        gauge_fig.update_layout(height=260, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(gauge_fig, use_container_width=True)
        st.caption(f"**Operating Rule:** {battery_res.recommended_operating_behavior}")

    st.subheader("📋 Coordinated Agent Dispatch Decisions")
    c1, c2, c3, c4 = st.columns(4)
    c1.info(f"**Solar Agent**\n\n{plan_res.solar_action}")
    c2.info(f"**Battery Agent**\n\n{plan_res.battery_action}")
    c3.info(f"**Grid Agent**\n\n{plan_res.grid_action}")
    c4.info(f"**EV Fleet Agent**\n\n{plan_res.ev_action}")

    st.markdown("---")
    st.subheader("🤖 SolarSathi Reasoning & Consultation")
    call_col, help_col = st.columns([2, 3])
    with call_col:
        st.write("Request full engineering justification from Gemini:")
        ask_ai_btn = st.button("🤖 Ask SolarSathi AI", use_container_width=True, type="primary")

    with help_col:
        user_query_input = st.text_input("Custom question (optional):", placeholder="e.g., Why did you delay EV charging?")

    if ask_ai_btn or st.session_state.gemini_explanation:
        if ask_ai_btn:
            with st.spinner("Multi-Agent Supervisor querying Gemini Reasoning Engine..."):
                explanation = generate_natural_explanation(
                    telemetry_dict=telemetry_data,
                    plan_dict=plan_res.model_dump(),
                    battery_dict=battery_res.model_dump(),
                    user_query=user_query_input if user_query_input else None
                )
                st.session_state.gemini_explanation = explanation

        st.markdown("#### 💡 AI Engineering Explanation")
        st.write(st.session_state.gemini_explanation)

    st.markdown("---")
    subtab1, subtab2 = st.tabs(["🚨 System Alerts & Diagnostics", "📄 Audit Report"])
    with subtab1:
        if plan_res.warning_alerts:
            for alert in plan_res.warning_alerts:
                st.error(f"⚠️ {alert}")
        else:
            st.success("✅ All network buses, transformers, and battery cells operating safely within nominal boundaries.")
        st.write("**Root-Cause Findings:**")
        for cause in battery_res.possible_causes:
            st.write(f"- {cause}")

    with subtab2:
        st.write("Download an engineering dossier for utility or technician records.")
        report_md = generate_markdown_report(telemetry_data, plan_res.model_dump(), battery_res.model_dump())
        st.download_button(
            label="📥 Download Energy Management Report (.md)",
            data=report_md,
            file_name=f"SolarSathi_Audit_{selected_scenario.replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True
        )
        with st.expander("Preview Audit Report", expanded=False):
            st.markdown(report_md)

# ----------------- TAB 2: BATCH CSV & 24H TIME-SERIES SIMULATOR -----------------
with tab_batch:
    st.subheader("📈 24-Hour Microgrid Time-Series Simulation")
    st.write("Run multi-agent dispatch and safety guardrails across full 24-hour load and solar curves from CSV telemetry.")

    batch_col1, batch_col2 = st.columns([2, 1])
    with batch_col1:
        uploaded_csv = st.file_uploader("Upload custom CSV file (or run default Pakistan 24h sample):", type=["csv"])
    with batch_col2:
        st.write("")
        st.write("")
        run_batch_btn = st.button("🚀 Run Multi-Agent Batch Engine", type="primary", use_container_width=True)

    default_csv_path = "Data/sample_energy_data.csv"
    target_csv = uploaded_csv if uploaded_csv is not None else (default_csv_path if os.path.exists(default_csv_path) else None)

    if target_csv is None:
        st.info("ℹ️ No CSV selected and `Data/sample_energy_data.csv` was not found. Please upload a CSV to simulate.")
    else:
        if run_batch_btn or "batch_results" in st.session_state:
            if run_batch_btn:
                with st.spinner("Processing time-series records through Solar, Battery, Grid, and Safety Agents..."):
                    st.session_state.batch_results = process_batch_telemetry(target_csv, st.session_state.supervisor)

            b_df = st.session_state.batch_results

            # Batch Summary Statistics
            sb1, sb2, sb3, sb4 = st.columns(4)
            sb1.metric("Total Records Processed", len(b_df))
            sb2.metric("Safety Guardrail Interventions", int(b_df["Safety_Replanned"].sum()))
            sb3.metric("Peak Dispatched Solar", f"{b_df['Flow_Solar_to_Load_kW'].max():.1f} kW")
            sb4.metric("Avg Battery Health Score", f"{b_df['Battery_SOH_Score'].mean():.1f}/100")

            # Time-Series Visualization
            x_axis = "hour" if "hour" in b_df.columns else b_df.index

            st.markdown("#### ⚡ 24-Hour Autonomous Power Dispatch Profile")
            sim_fig = go.Figure()
            sim_fig.add_trace(go.Scatter(x=b_df[x_axis] if "hour" in b_df.columns else b_df.index, y=b_df["pv_generation_kw"], mode="lines", name="Solar PV Generation (kW)", line=dict(color="#4CAF50", width=2)))
            sim_fig.add_trace(go.Scatter(x=b_df[x_axis] if "hour" in b_df.columns else b_df.index, y=b_df["load_demand_kw"], mode="lines", name="Load Demand (kW)", line=dict(color="#F44336", width=2)))
            sim_fig.add_trace(go.Scatter(x=b_df[x_axis] if "hour" in b_df.columns else b_df.index, y=b_df["Flow_Battery_to_Load_kW"], mode="lines", name="Battery Discharge (kW)", line=dict(color="#FF9800", width=2, dash="dot")))
            sim_fig.add_trace(go.Scatter(x=b_df[x_axis] if "hour" in b_df.columns else b_df.index, y=b_df["Flow_Solar_to_Battery_kW"], mode="lines", name="Battery Solar Charge (kW)", line=dict(color="#2196F3", width=2, dash="dash")))

            sim_fig.update_layout(
                xaxis_title="Time / Hour",
                yaxis_title="Power (kW)",
                height=380,
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(sim_fig, use_container_width=True)

            # Battery SOC & Health Profile
            st.markdown("#### 🔋 Battery SOC & Health Trajectory")
            batt_fig = go.Figure()
            batt_fig.add_trace(go.Scatter(x=b_df[x_axis] if "hour" in b_df.columns else b_df.index, y=b_df["battery_soc"], mode="lines+markers", name="Battery SOC (%)", line=dict(color="#00BCD4", width=2)))
            batt_fig.add_trace(go.Scatter(x=b_df[x_axis] if "hour" in b_df.columns else b_df.index, y=b_df["Battery_SOH_Score"], mode="lines", name="Battery SOH Score (/100)", line=dict(color="#8BC34A", width=2, dash="dash")))
            batt_fig.update_layout(
                xaxis_title="Time / Hour",
                yaxis_title="Percentage (%)",
                height=300,
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(batt_fig, use_container_width=True)

            # Interactive Telemetry and AI Decision Table
            st.markdown("#### 📋 Processed Telemetry with Agent Decisions")
            st.dataframe(b_df, use_container_width=True)

            # Download Enriched Decision CSV
            csv_export = b_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Full Processed AI Decisions Dataset (.csv)",
                data=csv_export,
                file_name="solarsathi_simulated_dispatch_results.csv",
                mime="text/csv",
                use_container_width=True
            )
