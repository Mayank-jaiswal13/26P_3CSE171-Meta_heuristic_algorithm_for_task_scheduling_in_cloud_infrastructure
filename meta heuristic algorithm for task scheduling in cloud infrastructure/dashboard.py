
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Cloud Scheduler",
    page_icon="☁️",
    layout="wide",
)

st.title("☁️ Cloud Task Scheduling Dashboard")
st.caption(
    "PT171 | Meta-Heuristic Algorithms for Task Scheduling"
)

csv_path = Path("results/validation_v1/runs.csv")

if not csv_path.exists():
    st.error(f"Results file not found: {csv_path}")
    st.info("Run your experiment first or check the CSV path.")
    st.stop()

df = pd.read_csv(csv_path)

required = {
    "algorithm",
    "makespan_seconds",
    "load_imbalance_seconds",
    "energy_proxy_joules",
    "fitness",
}

if not required.issubset(df.columns):
    st.error("The results CSV is missing required columns.")
    st.write("Available columns:", list(df.columns))
    st.stop()

algorithms = sorted(df["algorithm"].dropna().unique())

selected = st.multiselect(
    "Compare algorithms",
    algorithms,
    default=algorithms,
)

data = df[df["algorithm"].isin(selected)]

if data.empty:
    st.warning("Select at least one algorithm.")
    st.stop()

summary = (
    data.groupby("algorithm", as_index=False)
    .agg(
        Makespan=("makespan_seconds", "mean"),
        Load_Imbalance=("load_imbalance_seconds", "mean"),
        Energy_Proxy=("energy_proxy_joules", "mean"),
        Fitness=("fitness", "mean"),
    )
)

best = summary.loc[summary["Fitness"].idxmin()]

c1, c2, c3, c4 = st.columns(4)

c1.metric("Algorithms", len(summary))
c2.metric("Best algorithm", best["algorithm"])
c3.metric("Best mean makespan", f'{best["Makespan"]:.2f} s')
c4.metric("Best mean fitness", f'{best["Fitness"]:.4f}')

st.subheader("Performance comparison")

left, right = st.columns(2)

with left:
    fig = px.bar(
        summary,
        x="algorithm",
        y="Makespan",
        color="algorithm",
        title="Average Makespan (seconds)",
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    fig = px.bar(
        summary,
        x="algorithm",
        y="Load_Imbalance",
        color="algorithm",
        title="Average Load Imbalance (seconds)",
    )
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)

with left:
    fig = px.bar(
        summary,
        x="algorithm",
        y="Energy_Proxy",
        color="algorithm",
        title="Energy Proxy (joules)",
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    fig = px.bar(
        summary,
        x="algorithm",
        y="Fitness",
        color="algorithm",
        title="Average Fitness (lower is better)",
    )
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Experiment results")
st.dataframe(summary.round(4), use_container_width=True)

st.download_button(
    "Download comparison CSV",
    data=summary.to_csv(index=False),
    file_name="algorithm_comparison.csv",
    mime="text/csv",
)

st.caption(
    "Energy is a simulated proxy, not measured hardware consumption. "
    "Results depend on workload, seeds, and experiment settings."
)
