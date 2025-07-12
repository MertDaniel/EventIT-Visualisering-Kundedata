# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide")

#
# ─── 1) LOAD & CLEAN EXCEL (KUNDE-DATA) ─────────────────────────────────────────
#
@st.cache_data
def load_kunde_data(path):
    df = pd.read_excel(path, header=4)
    df = df.dropna(axis=1, how="all")

    # Total indtjening
    rev_cols = [c for c in df.columns if "indtjening" in c.lower()]
    rev_col = "Indtjening" if "Indtjening" in rev_cols else rev_cols[0]
    df[rev_col] = (
        df[rev_col]
        .astype(str)
        .str.replace(r"[^0-9,.\-]", "", regex=True)
        .str.replace(",", ".", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
    )

    # Subscriptions
    sub_col = "Indtjening på abonnement (pr. år)"
    df[sub_col] = (
        df[sub_col]
        .astype(str)
        .str.replace(r"[^0-9,.\-]", "", regex=True)
        .str.replace(",", ".", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
    )

    # Fees
    fee_col = "indtjening gebyr/i alt"
    df[fee_col] = (
        df[fee_col]
        .astype(str)
        .str.replace(r"[^0-9,.\-]", "", regex=True)
        .str.replace(",", ".", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
    )

    # Frakturer = total - fee
    df["Frakturer"] = df[rev_col] - df[fee_col]

    # Start År
    df["Start Dato"] = pd.to_datetime(df["Start Dato"], errors="coerce")
    df["Start År"] = df["Start Dato"].dt.year.astype("Int64")

    df = df.dropna(subset=["Name", rev_col])
    return df, rev_col, sub_col, fee_col


#
# ─── 2) LOAD & CLEAN CSV (GEBYR-DATA) ────────────────────────────────────────────
#
@st.cache_data
def load_gebyr_data(path):
    df2 = pd.read_csv(
        path,
        header=2,
        sep=";",
        parse_dates=["Periode start"],
        dayfirst=False,
    )
    df2["Vores gebyr"] = pd.to_numeric(df2["Vores gebyr"], errors="coerce")
    df2 = df2.dropna(subset=["Periode start", "Vores gebyr"])
    df2["År"] = df2["Periode start"].dt.year
    top25_idx = df2.groupby("Arrangør")["Vores gebyr"].sum().nlargest(25).index
    df2_top25 = df2[df2["Arrangør"].isin(top25_idx)]
    return df2, df2_top25


#
# ─── MAIN ───────────────────────────────────────────────────────────────────────
#
kundedf, rev_col, sub_col, fee_col = load_kunde_data(
    "Kunder_Aktive_Brugere_1752151546.xlsx"
)
gebyrdf, gebyr_top25 = load_gebyr_data(
    "Gebyr omsætning og deltager opgørelse pr år Daniel (1).csv"
)

st.title("📊 EventIT – Samlet Visualiserings-App")
tabs = st.tabs(["1) Kunde-data", "2) Gebyr pr. arrangør"])


#
# ─── TAB #1: KUNDE-DATA ──────────────────────────────────────────────────────────
#
with tabs[0]:
    st.header("Kunde-visualiseringer")

    søg = st.sidebar.text_input("🔍 Søg kunde-navn", "")
    maxår = st.sidebar.slider(
        "📅 Max Start-År",
        int(kundedf["Start År"].min()),
        int(kundedf["Start År"].max()),
        int(kundedf["Start År"].max()),
    )
    kontr = st.sidebar.multiselect(
        "🗂️ Kontrakttype", options=kundedf["Kontrakttype"].unique()
    )

    mask = kundedf["Name"].str.contains(søg, case=False, na=False)
    mask &= kundedf["Start År"].fillna(0) <= maxår
    if kontr:
        mask &= kundedf["Kontrakttype"].isin(kontr)
    dff = kundedf[mask]

    k_tabs = st.tabs(
        [
            "Alle kunder",
            "Top 25 indtjening",
            "Kontrakt-fordeling",
            "Abonnements-growth",
            "Gratis vs Betalt",
            "Betalte Fakturaer",
        ]
    )

    # ───── Alle kunder
    with k_tabs[0]:
        st.subheader("Alle nuværende kunder")
        st.dataframe(dff[["Name", rev_col, "Kontrakttype"]], use_container_width=True)

    # ───── Top 25 samlet indtjening
    with k_tabs[1]:
        st.subheader("Top 25 efter samlet indtjening")
        top25 = dff.nlargest(25, rev_col)
        fig = px.bar(top25, x="Name", y=rev_col, hover_data=[rev_col], labels={rev_col: "DKK"})
        fig.update_layout(xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig, use_container_width=True)

    # ───── Kontrakt-fordeling m. hover-tooltip navne
    with k_tabs[2]:
        st.subheader("Fordeling af Kontrakttyper")
        cnt = dff["Kontrakttype"].value_counts().reset_index()
        cnt.columns = ["Kontrakt", "Antal"]

        name_lists = (
            dff.groupby("Kontrakttype")["Name"]
            .apply(lambda names: "<br>".join(names.tolist()))
            .reindex(cnt["Kontrakt"])
            .tolist()
        )

        fig = go.Figure(
            go.Pie(
                labels=cnt["Kontrakt"],
                values=cnt["Antal"],
                hole=0.4,
                customdata=name_lists,
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "Antal: %{value}<br><br>"
                    "Kunder:<br>%{customdata}<extra></extra>"
                ),
            )
        )
        fig.update_layout(title_text="Kontrakt-fordeling", height=500)
        st.plotly_chart(fig, use_container_width=True)

    # ───── Abonnements-growth
    with k_tabs[3]:
        st.subheader("Growth i abonnementsindtjening efter Start-År")
        agg = dff.groupby("Start År")[sub_col].sum().reset_index()
        fig = px.line(agg, x="Start År", y=sub_col, markers=True, labels={sub_col: "DKK"})
        fig.update_layout(xaxis_title="År", height=500)
        st.plotly_chart(fig, use_container_width=True)

    # ───── Gratis vs. Betalt m. hover-tooltip navne
    with k_tabs[4]:
        st.subheader("Gratis vs. Betalt abonnement")
        dff["Type"] = dff[sub_col].fillna(0).apply(lambda x: "Betalt" if x > 0 else "Gratis")
        cnt2 = dff["Type"].value_counts().reset_index()
        cnt2.columns = ["Type", "Antal"]

        name_lists2 = (
            dff.groupby("Type")["Name"]
            .apply(lambda names: "<br>".join(names.tolist()))
            .reindex(cnt2["Type"])
            .tolist()
        )

        fig2 = go.Figure(
            go.Pie(
                labels=cnt2["Type"],
                values=cnt2["Antal"],
                hole=0.4,
                customdata=name_lists2,
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "Antal: %{value}<br><br>"
                    "Kunder:<br>%{customdata}<extra></extra>"
                ),
            )
        )
        fig2.update_layout(title_text="Gratis vs. Betalt abonnement", height=500)
        st.plotly_chart(fig2, use_container_width=True)

    # ───── Top 10 Betalte Frakturer
    with k_tabs[5]:
        st.subheader("Top 10 Betalte Fakturaer")
        top10 = dff.nlargest(10, "Frakturer")
        fig = px.bar(top10, x="Name", y="Frakturer", labels={"Frakturer": "DKK"}, hover_data=["Frakturer"])
        fig.update_layout(xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig, use_container_width=True, key="top10_frakturer")


#
# ─── TAB #2: GEBYR pr. ARRANGØR ────────────────────────────────────────────────────
#
with tabs[1]:
    st.header("Gebyr pr. arrangør (CSV-data)")

    søg2 = st.text_input("🔍 Søg arrangør")
    max2 = st.slider(
        "📅 Max År", int(gebyrdf["År"].min()), int(gebyrdf["År"].max()), int(gebyrdf["År"].max())
    )

    filt = (
        gebyrdf["Arrangør"].str.contains(søg2 or "", case=False, na=False)
        & (gebyrdf["År"] <= max2)
    )
    df1 = gebyrdf[filt].groupby("År")["Vores gebyr"].sum().reset_index()
    fig1 = px.line(df1, x="År", y="Vores gebyr", markers=True, title=f"Op til {max2}, filter: {søg2}")
    fig1.update_layout(hovermode="x unified", height=500)
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Udvikling for top 25 arrangører")
    top25_opts = gebyr_top25["Arrangør"].unique().tolist()
    default = top25_opts[:5]
    valgt = st.multiselect(
        "Vælg arrangører (kun top 25)", options=top25_opts, default=default
    )
    if valgt:
        df2 = gebyr_top25[gebyr_top25["Arrangør"].isin(valgt)]
        plot2 = df2.groupby(["År", "Arrangør"])["Vores gebyr"].sum().reset_index()
        fig2 = px.line(
            plot2,
            x="År",
            y="Vores gebyr",
            color="Arrangør",
            markers=True,
            title="Top 25 – valgte arrangørers udvikling",
        )
        fig2.update_layout(hovermode="x unified", height=500)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Vælg mindst én arrangør fra dropdown’en ovenfor.")
