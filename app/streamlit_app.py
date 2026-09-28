"""Dashboard: where do German long-distance trains lose time?

uv run streamlit run app/streamlit_app.py
"""

from pathlib import Path

import altair as alt
import duckdb
import streamlit as st

MARTS = Path(__file__).resolve().parent.parent / "data" / "marts"
PHASE_LABELS = {"running": "Running between stations", "at_station": "Standing at stations"}
PHASE_COLORS = alt.Scale(domain=list(PHASE_LABELS.values()), range=["#2a78d6", "#eb6834"])


@st.cache_data
def load(mart: str):
    return duckdb.sql(f"SELECT * FROM '{MARTS / mart}.parquet'").df()


st.set_page_config(page_title="DB punctuality: where trains lose time", layout="wide")
st.title("Where do German long-distance trains lose time?")
st.caption(
    "ICE, IC and EC trains. Delay added = change in a train's delay between two points "
    "of its journey, from Deutsche Bahn's live timetable data."
)

phase = load("fct_delay_by_phase")
locations = load("fct_delay_locations")

col_month, col_types = st.columns([1, 2])
months = sorted(phase["service_month"].unique(), reverse=True)
month = col_month.selectbox("Month", months)
types = col_types.multiselect("Train types", ["ICE", "IC", "EC"], default=["ICE", "IC", "EC"])
if not types:
    st.info("Pick at least one train type.")
    st.stop()

sel = phase[(phase["service_month"] == month) & (phase["train_type"].isin(types))]
by_phase = sel.groupby("phase")[["scheduled_min", "minutes_net", "n_events"]].sum()
if (by_phase["minutes_net"] <= 0).any():
    st.warning("For this selection one phase recovers more delay than it adds; shares not shown.")
    st.stop()

station, running = by_phase.loc["at_station"], by_phase.loc["running"]
sched_share = station.scheduled_min / by_phase.scheduled_min.sum()
delay_share = station.minutes_net / by_phase.minutes_net.sum()
station_rate = station.minutes_net / (station.scheduled_min / 60)
running_rate = running.minutes_net / (running.scheduled_min / 60)

# --- headline -------------------------------------------------------------------------
t1, t2, t3 = st.columns(3)
t1.metric("Scheduled time spent at stations", f"{sched_share:.0%}")
t2.metric("Net delay added at stations", f"{delay_share:.0%}")
t3.metric(
    "Net delay per scheduled hour: at stations vs running",
    f"{station_rate:.1f} vs {running_rate:.1f} min",
)

# --- share of time vs share of delay --------------------------------------------------
st.subheader("Trains spend little time at stations, but pick up half their delay there")
share_rows = []
for p, label in PHASE_LABELS.items():
    share_rows.append(
        {
            "measure": "Scheduled time",
            "phase": label,
            "share": by_phase.loc[p, "scheduled_min"] / by_phase.scheduled_min.sum(),
        }
    )
    share_rows.append(
        {
            "measure": "Net delay added",
            "phase": label,
            "share": by_phase.loc[p, "minutes_net"] / by_phase.minutes_net.sum(),
        }
    )
shares = alt.Data(values=share_rows)
bars = (
    alt.Chart(shares)
    .mark_bar(cornerRadius=4)
    .encode(
        y=alt.Y(
            "measure:N",
            title=None,
            sort=["Scheduled time", "Net delay added"],
            scale=alt.Scale(paddingInner=0.35),
        ),
        x=alt.X("share:Q", stack="normalize", title=None, axis=alt.Axis(format="%")),
        color=alt.Color("phase:N", scale=PHASE_COLORS, legend=alt.Legend(orient="top", title=None)),
        order=alt.Order("phase:N", sort="descending"),
        tooltip=[
            alt.Tooltip("measure:N", title="Measure"),
            alt.Tooltip("phase:N", title="Phase"),
            alt.Tooltip("share:Q", title="Share", format=".1%"),
        ],
    )
)
labels = (
    alt.Chart(shares)
    .mark_text(color="white", fontWeight="bold", align="center")
    .encode(
        y=alt.Y("measure:N", sort=["Scheduled time", "Net delay added"]),
        x=alt.X("share:Q", stack="normalize", bandPosition=0.5),
        text=alt.Text("share:Q", format=".0%"),
        order=alt.Order("phase:N", sort="descending"),
        opacity=alt.condition("datum.share > 0.06", alt.value(1), alt.value(0)),
    )
)
st.altair_chart((bars + labels).properties(height=150), use_container_width=True)
st.caption(
    f"Per scheduled hour, standing at stations adds {station_rate:.0f} min of net delay; "
    f"running adds {running_rate:.1f} min. Running time has slack that absorbs delay; "
    "station stops mostly do not."
)

# --- day by day -----------------------------------------------------------------------
st.subheader("Share of net delay added at stations, day by day")
daily = sel[sel["service_date"].astype(str).str.startswith(month)]
daily = daily.pivot_table(
    index="service_date", columns="phase", values="minutes_net", aggfunc="sum"
)
daily = daily[daily.sum(axis=1) > 0]
daily["station_share"] = daily["at_station"] / daily.sum(axis=1)
daily = daily.reset_index()
daily["weekday"] = daily["service_date"].dt.day_name()
line = (
    alt.Chart(daily)
    .mark_line(strokeWidth=2, color="#eb6834", point=alt.OverlayMarkDef(size=64, color="#eb6834"))
    .encode(
        x=alt.X("service_date:T", title=None),
        y=alt.Y(
            "station_share:Q", title=None, axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])
        ),
        tooltip=[
            alt.Tooltip("service_date:T", title="Date"),
            alt.Tooltip("weekday:N", title="Day"),
            alt.Tooltip("station_share:Q", title="At stations", format=".0%"),
        ],
    )
)
half = (
    alt.Chart(alt.Data(values=[{"y": 0.5}]))
    .mark_rule(strokeDash=[4, 4], color="gray")
    .encode(y="y:Q")
)
st.altair_chart((half + line).properties(height=260), use_container_width=True)
st.caption("Dashed line = 50%. Weekends tend to sit higher.")

# --- where exactly --------------------------------------------------------------------
st.subheader("Where the most net delay is added")
kind = st.radio("Show", ["Stations", "Track segments"], horizontal=True)
loc_type = "station" if kind == "Stations" else "track"
top = (
    locations[(locations["service_month"] == month) & (locations["location_type"] == loc_type)]
    .nlargest(12, "minutes_net")
    .assign(net_per_pass=lambda d: d["minutes_net"] / d["n_train_passes"])
)
top_chart = (
    alt.Chart(top)
    .mark_bar(cornerRadiusEnd=4, height=16, color="#eb6834" if loc_type == "station" else "#2a78d6")
    .encode(
        y=alt.Y("location_name:N", sort="-x", title=None, axis=alt.Axis(labelLimit=320)),
        x=alt.X("minutes_net:Q", title="Net delay added (minutes, whole month)"),
        tooltip=[
            alt.Tooltip("location_name:N", title="Location"),
            alt.Tooltip("minutes_net:Q", title="Net minutes", format=","),
            alt.Tooltip("n_train_passes:Q", title="Train passes", format=","),
            alt.Tooltip("net_per_pass:Q", title="Net min per train", format=".1f"),
        ],
    )
)
st.altair_chart(top_chart.properties(height=380), use_container_width=True)
st.caption("All train types. Big hubs rank high partly because many trains pass through them.")

with st.expander("Table view"):
    st.dataframe(
        top[
            [
                "location_name",
                "n_train_passes",
                "minutes_gained",
                "minutes_recovered",
                "minutes_net",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )

# --- caveats and attribution ----------------------------------------------------------
st.divider()
st.markdown(
    "**Read with care.** Delay recorded while a train stands at a station is not only "
    "boarding: it also includes waiting for a free track or a connecting train. Times are "
    "DB's latest reported values when the data was fetched, not audited actuals. "
    "About 8% of stops are excluded (cancelled, diverted, or inconsistent times)."
)
st.caption(
    "Data: Deutsche Bahn, Timetables API, CC BY 4.0, collected by "
    "[piebro/deutsche-bahn-data](https://github.com/piebro/deutsche-bahn-data). "
    "Not affiliated with Deutsche Bahn."
)
