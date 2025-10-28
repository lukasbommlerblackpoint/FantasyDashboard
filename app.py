import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
from sklearn.linear_model import LinearRegression

df_players = pd.read_excel('df_players.xlsx').drop(columns='Unnamed: 0')
df_players = df_players[~(df_players.overallADP==0)]
df_teams = pd.read_excel('df_teams.xlsx').drop(columns='Unnamed: 0')
# -------------------------
# Initialize Dash App
# -------------------------
app = dash.Dash(__name__)
app.title = "Fantasy Football Dashboard"

# -------------------------
# Layout
# -------------------------
app.layout = html.Div([
    html.H1("🏈 Fantasy Football Dashboard", 
            style={'textAlign': 'center', 'marginBottom': '30px'}),

    html.Div([
        html.Div([
            html.Label("Select Player", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='player-dropdown',
                options=[{'label': n, 'value': n} for n in sorted(df_players['Name'].unique())],
                value=df_players['Name'].iloc[0],
                clearable=False,
                style={'backgroundColor': 'white'}
            ),
        ], style={'width': '48%', 'display': 'inline-block'}),

        html.Div([
            html.Label("Filter by Week", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='week-dropdown',
                options=([{'label': 'All Weeks', 'value': 'All'}, {'label': 'Sum Of All Weeks', 'value': 'Sum'}] +
                         [{'label': p, 'value': p} for p in sorted(df_players['week'].unique())]),
                value='All',
                clearable=False,
                style={'backgroundColor': 'white'}
            ),
        ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
    ], style={'margin': '20px 40px'}),

    html.Div([
        dcc.Graph(id='player-weekly-bar', style={'marginBottom': '40px','width': '48%', 'display': 'inline-block'}),
        dcc.Graph(id='teams-yds', style={'marginBottom': '40px','width': '48%', 'display': 'inline-block'}),
        dcc.Graph(id='position-scatter', style={'marginBottom': '40px','width': '48%', 'display': 'inline-block'}),
        dcc.Graph(id='adp-vs-score', style={'marginBottom': '40px','width': '48%', 'display': 'inline-block'})
    ], style={'padding': '0 40px'})
], style={'backgroundColor': '#fafafa', 'fontFamily': 'Arial, sans-serif'})

# -------------------------
# Callbacks
# -------------------------
def update_chart_style(fig, title):
    fig.update_layout(
        title=title,
        title_x=0.5,
        plot_bgcolor='#fafafa',
        paper_bgcolor='#fafafa',
        font=dict(family='Arial', size=13),
        margin=dict(l=50, r=40, t=80, b=60),
        xaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            zeroline=False,
            linecolor='black',
            mirror=False
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            zeroline=False,
            linecolor='black',
            mirror=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor='#fafafa'
        )
    )
    return fig

def add_regression_line(fig, df, x_col, y_col, color='red'):
    # Remove rows with NaN
    df_clean = df[[x_col, y_col]].dropna()
    if len(df_clean) < 2:
        return fig  # Not enough points for regression

    X = df_clean[[x_col]].values
    y = df_clean[y_col].values

    model = LinearRegression()
    model.fit(X, y)
    y_pred = model.predict(X)
    r2 = model.score(X, y)

    # Add regression line
    fig.add_traces(px.line(
        x=df_clean[x_col],
        y=y_pred,
        labels={x_col: x_col, y_col: y_col}
    ).data)

    # Add R^2 annotation
    fig.add_annotation(
        xref='paper', yref='paper',
        x=0.95, y=0.95,
        text=f"R² = {r2:.3f}",
        showarrow=False,
        font=dict(color=color, size=14),
        align='right'
    )
    return fig

# Bar chart for selected player
@app.callback(
    Output('player-weekly-bar', 'figure'),
    Input('player-dropdown', 'value')
)
def update_player_weekly(player_name):
    df_p = df_players[df_players['Name'] == player_name]
    fig = px.bar(
        df_p,
        x='week',
        y=['projected_points', 'scored_points'],
        barmode='group',
        labels={'value': 'Points', 'variable': 'Type', 'week': 'Week'},
        color_discrete_sequence=['#1f77b4', '#ff7f0e']
    )
    return update_chart_style(fig, f"Weekly Projected vs Scored Points - {player_name}")


# Scatter: Projected vs Scored Points for selected position
@app.callback(
    Output('position-scatter', 'figure'),
    Input('week-dropdown', 'value')
)
def update_position_scatter(week):
    df_pos = df_players if week in ('All', 'Sum') else df_players[df_players['week'] == week]
    if week == 'Sum':
        df_pos = df_pos.groupby(
            ['playerID', 'Name', 'Position', 'Team', 'overallADP'], as_index=False
        ).agg({
            'projected_points': 'sum',
            'scored_points': 'sum'
        })
        df_pos['week'] = week

    fig = px.scatter(
        df_pos,
        x='projected_points',
        y='scored_points',
        color='Position',
        hover_data=['Name', 'Team', 'week'],
        color_discrete_sequence=px.colors.qualitative.Plotly
    )
    fig = update_chart_style(fig, f"Projected vs Scored Points (week: {week})")
    fig = add_regression_line(fig, df_pos, 'projected_points', 'scored_points', color='gray')
    return fig

# Scatter: ADP vs Scored Points (all players)
@app.callback(
    Output('adp-vs-score', 'figure'),
    Input('week-dropdown', 'value')
)
def update_adp_vs_score(week):
    df_pos = df_players if week in ('All', 'Sum') else df_players[df_players['week'] == week]
    if week == 'Sum':
        df_pos = df_pos.groupby(
            ['playerID', 'Name', 'Position', 'Team', 'overallADP'], as_index=False
        ).agg({
            'projected_points': 'sum',
            'scored_points': 'sum'
        })
        df_pos['week'] = week

    fig = px.scatter(
        df_pos,
        x='overallADP',
        y='scored_points',
        color='Position',
        hover_data=['Name', 'Team', 'week'],
        color_discrete_sequence=px.colors.qualitative.Plotly
    )
    fig = update_chart_style(fig, f"Scored Points vs Average Draft Nr (week: {week})")
    fig = add_regression_line(fig, df_pos, 'overallADP', 'scored_points', color='gray')
    return fig

# Scatter: ADP vs Scored Points (all players)
@app.callback(
    Output('teams-yds', 'figure'),
    Input('week-dropdown', 'value')
)
def update_teams_yds(weeks):
    df_yds = df_teams.copy()
    df_yds['bubble size'] = (df_yds['rushTD'] + df_yds['recTD'])*20
    fig = px.scatter(
        df_yds,
        x='rushYds',
        y='recYds',
        size='bubble size',
        color='wins',
        hover_data=['teamAbv', 'rushYds', 'rushTD', 'recYds', 'recTD', 'wins'],
        color_discrete_sequence=px.colors.qualitative.Plotly
    )
    fig = update_chart_style(fig, f"Rushing vs Receiving Yards per Team (Size ~ #TD)")
    return fig


# -------------------------
# Run app
# -------------------------
if __name__ == '__main__':
    app.run_server(debug=False)
