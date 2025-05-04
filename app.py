from flask import Flask, render_template
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.offline as pyo

app = Flask(__name__)

@app.route("/")
def index():
    # 1) Load all data
    df = pd.read_csv("Merged_Incident_Reports.csv")

    # 2) Coerce lat/lon → numeric
    df["Latitude"]  = pd.to_numeric(df["Latitude"],  errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

    # 3) Parse dates & restrict to last 12 months (all systems)
    df["Incident Date"] = pd.to_datetime(df["Incident Date"], format="%b-%Y", errors="coerce")
    max_dt = df["Incident Date"].max()
    start_dt = max_dt - pd.DateOffset(months=11)
    recent_all = df[(df["Incident Date"] >= start_dt) & (df["Incident Date"] <= max_dt)]

    # 4) Monthly bar (all systems)
    df_mon = (
        recent_all
        .groupby(recent_all["Incident Date"].dt.strftime("%B %Y"))
        .size().reset_index(name="Crashes")
    )
    df_mon["dt"] = pd.to_datetime(df_mon["Incident Date"], format="%B %Y", errors="coerce")
    df_mon = df_mon.sort_values("dt")
    fig_month = px.bar(
        df_mon,
        x="Incident Date",
        y="Crashes",
        title="Crashes by Month (All Systems)",
        text="Crashes"
    )
    fig_month.update_traces(textposition="outside")

    # 5) State choropleth (all systems)
    df_state = df.groupby(df["State"].str.strip()).size().reset_index(name="Crashes")
    fig_state = px.choropleth(
        df_state,
        locations="State",
        locationmode="USA-states",
        color="Crashes",
        scope="usa",
        color_continuous_scale="Blues",
        title="Crashes by State (All Systems)"
    )

    # 6) Combo bar + 3-month rolling avg (all systems)
    df_mon["RollingAvg"] = df_mon["Crashes"].rolling(window=3, min_periods=1).mean()
    fig_combo = go.Figure()
    fig_combo.add_trace(go.Bar(
        x=df_mon["Incident Date"],
        y=df_mon["Crashes"],
        name="Monthly Crashes"
    ))
    fig_combo.add_trace(go.Scatter(
        x=df_mon["Incident Date"],
        y=df_mon["RollingAvg"],
        mode="lines+markers",
        name="3-Month Rolling Avg"
    ))
    fig_combo.update_layout(
        title="Monthly Crashes + 3-Month Rolling Average (All Systems)",
        xaxis_title="Month",
        yaxis_title="Count"
    )

    # 7) Calendar heatmap (all systems)
    df_mon["Year"]  = df_mon["dt"].dt.year
    df_mon["Month"] = df_mon["dt"].dt.strftime("%b")
    pivot = (
        df_mon
        .pivot(index="Year", columns="Month", values="Crashes")
        .fillna(0)
        .reindex(columns=["Jan","Feb","Mar","Apr","May","Jun",
                          "Jul","Aug","Sep","Oct","Nov","Dec"],
                 fill_value=0)
    )
    fig_calendar = px.imshow(
        pivot,
        labels=dict(x="Month", y="Year", color="Crashes"),
        title="Monthly Crash Heatmap (All Systems)"
    )

    # 8) Pie chart of Reporting Entity (all systems)
    df_ent = (
        df["Reporting Entity"]
        .value_counts()
        .reset_index(name="Crashes")
        .rename(columns={"index":"Reporting Entity"})
    )
    fig_pie = px.pie(
        df_ent,
        names="Reporting Entity",
        values="Crashes",
        hole=0.4,
        title="Reporting Entity Share (All Systems)"
    )
    fig_pie.update_traces(
        hovertemplate="%{label}: %{percent:.1%} (%{value})",
        texttemplate="%{percent:.1%}"
    )

    # 9) Sunburst: State → Reporting Entity (all systems)
    df_sb = df.groupby(["State","Reporting Entity"]).size().reset_index(name="Crashes")
    fig_sunburst = px.sunburst(
        df_sb,
        path=["State","Reporting Entity"],
        values="Crashes",
        title="Crashes by State & Entity (All Systems)"
    )

    # 10) Stacked bar: SV Damage Locations by State (all systems)
    sv_cols = [c for c in df.columns if c.startswith("SV Contact Area")]
    df_dmg = (
        df.melt(
            id_vars=["State"],
            value_vars=sv_cols,
            var_name="DamageLocation",
            value_name="Flag"
        )
        .query("Flag=='Y'")
    )
    df_dmg["DamageLocation"] = df_dmg["DamageLocation"].str.replace("SV Contact Area - ","")
    pivot_dmg = df_dmg.groupby(["State","DamageLocation"]).size().unstack(fill_value=0)
    fig_stacked = px.bar(
        pivot_dmg,
        title="Damage Locations by State (SV Contact Areas, All Systems)",
        labels={"value":"Crashes","State":"State"},
        barmode="stack"
    )

    # Render all charts
    return render_template(
        "index.html",
        month=pyo.plot(fig_month, include_plotlyjs=False, output_type="div"),
        state=pyo.plot(fig_state, include_plotlyjs=False, output_type="div"),
        combo=pyo.plot(fig_combo, include_plotlyjs=False, output_type="div"),
        calendar=pyo.plot(fig_calendar, include_plotlyjs=False, output_type="div"),
        pie=pyo.plot(fig_pie, include_plotlyjs=False, output_type="div"),
        sunburst=pyo.plot(fig_sunburst, include_plotlyjs=False, output_type="div"),
        stacked=pyo.plot(fig_stacked, include_plotlyjs=False, output_type="div")
    )

if __name__ == "__main__":
    app.run(debug=True)
