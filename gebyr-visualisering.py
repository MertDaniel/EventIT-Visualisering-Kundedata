import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output

# 1) Indlæs CSV
df = pd.read_csv(
    'Gebyr omsætning og deltager opgørelse pr år Daniel (1).csv',
    header=2,
    sep=';',
    parse_dates=['Periode start'],
    dayfirst=False
)

# 2) Rens og konvertér
df['Vores gebyr'] = pd.to_numeric(df['Vores gebyr'], errors='coerce')
df = df.dropna(subset=['Periode start', 'Vores gebyr'])
df['År'] = df['Periode start'].dt.year

# 3) Årsvalg
år_valg = sorted(df['År'].unique())
år_min, år_max = int(min(år_valg)), int(max(år_valg))

# 4) Top 25 arrangører (samlet set)
top_kunder = (
    df.groupby('Arrangør')['Vores gebyr']
      .sum()
      .sort_values(ascending=False)
      .head(25)
      .index
)
df_top25 = df[df['Arrangør'].isin(top_kunder)]

# 5) Dash-app setup
app = Dash(__name__)
app.title = "Gebyrvisualisering"

app.layout = html.Div([
    html.H1("Gebyr pr. år", style={'textAlign': 'center'}),

    # Søg + slider
    html.Div([
        html.Label("🔍 Søg efter arrangør:"),
        dcc.Input(id='søgefelt', type='text', placeholder='fx Lystrup', style={'width': '300px'}),
    ], style={'padding': '10px'}),

    html.Div([
        html.Label("📅 Vis op til år:"),
        dcc.Slider(
            id='år-slider',
            min=år_min,
            max=år_max,
            step=1,
            value=år_max,
            marks={int(y): str(y) for y in år_valg},
            tooltip={"placement": "bottom", "always_visible": True}
        )
    ], style={'padding': '10px'}),

    html.H2("Udvikling for valgt arrangør"),
    dcc.Graph(id='gebyr-graf'),

    # Dropdown til top 25
    html.H2("Vælg top 25 arrangører"),
    dcc.Dropdown(
        id='top25-selector',
        options=[{'label': a, 'value': a} for a in top_kunder],
        value=list(top_kunder[:5]),   # vis de 5 største som default
        multi=True,
        placeholder="Vælg én eller flere arrangører…",
        style={'width': '80%', 'margin-bottom': '20px'}
    ),

    html.H2("📊 Udvikling for valgte top 25 arrangører"),
    dcc.Graph(id='top25-graf')
])

# 6a) Callback til den søgte arrangør
@app.callback(
    Output('gebyr-graf', 'figure'),
    Input('søgefelt', 'value'),
    Input('år-slider', 'value')
)
def opdater_graf(søgning, maks_år):
    søgning = søgning or ""
    filtreret = df[
        df['Arrangør'].str.contains(søgning, case=False, na=False) &
        (df['År'] <= maks_år)
    ]
    if filtreret.empty:
        return {
            "data": [],
            "layout": {"title": "Ingen data fundet for dette filter", "height": 400}
        }
    df2 = filtreret.groupby('År')['Vores gebyr'].sum().reset_index()
    fig = px.line(
        df2, x='År', y='Vores gebyr', markers=True,
        title=f"Vores gebyr pr. år (op til {maks_år}) – filtreret på: '{søgning}'",
        labels={'Vores gebyr': 'Vores gebyr (DKK)', 'År': 'År'}
    )
    fig.update_layout(hovermode='x unified', height=500)
    return fig

# 6b) Callback til top 25-graf
@app.callback(
    Output('top25-graf', 'figure'),
    Input('top25-selector', 'value')
)
def opdater_top25(valgte):
    if not valgte:
        return {
            "data": [],
            "layout": {"title": "Vælg mindst én arrangør ovenfor!", "height": 400}
        }
    dff = df_top25[df_top25['Arrangør'].isin(valgte)]
    df_plot = (
        dff.groupby(['År','Arrangør'])['Vores gebyr']
           .sum()
           .reset_index()
    )
    fig = px.line(
        df_plot,
        x='År',
        y='Vores gebyr',
        color='Arrangør',
        markers=True,
        title="Udvikling i 'Vores gebyr' for valgte arrangører",
        labels={'Vores gebyr': 'Vores gebyr (DKK)', 'År': 'År'}
    )
    fig.update_layout(hovermode='x unified', height=600)
    return fig

# 7) Kør server
if __name__ == '__main__':
    app.run(debug=True)
