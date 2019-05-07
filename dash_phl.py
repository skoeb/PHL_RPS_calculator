import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Input, State
import datetime
from dateutil.relativedelta import relativedelta
import plotly.graph_objs as go
import pandas as pd
import requests
import pandas as pd

import pandas as pd
import plotly as py

import plotly.graph_objs as go

def rps_df_maker(demand, demand_growth, eligible_re_2018,
                 annual_rps_inc_2020, annual_rps_inc_2023, losses,
                 end_year):

    daterange = pd.date_range(start = '2018', end = str(end_year), freq = 'Y')

    df = pd.DataFrame(index = daterange)

    df['year'] = df.index.year
    df = df.set_index('year')

    df['demand_growth'] = demand_growth + 1
    df.loc[2018, 'demand_growth'] = 1
    df['demand_growth'] = df['demand_growth'].cumprod()
    df['demand'] = demand * df['demand_growth']

    df.loc[2020:2022,'rps_marginal_req'] = annual_rps_inc_2020 #no requirement till 2020
    df.loc[2023:, 'rps_marginal_req'] = annual_rps_inc_2023 #presidential elections in 2022
    df['rps_req'] = df['rps_marginal_req'].cumsum()

    df = df.fillna(0)

    df['rec_req'] = df['rps_req'] * df['demand'] * (1 + losses)

    df['re'] =  eligible_re_2018
    df['rec_change'] = df['re'] - df['rec_req']
    df['rec_balance'] = df['rec_change'].cumsum()

    return df
    
app = dash.Dash(__name__)

# Boostrap CSS.
app.css.append_css({
    "external_url":"https://codepen.io/chriddyp/pen/bWLwgP.css"
})


app.layout = html.Div([

# Title - Row
    html.Div(
        [
            html.H1(
                'Philippines REC Calculator',
                style={'font-family': 'Helvetica',
                       "margin-top": "25",
                       "margin-bottom": "0"},
                className='eight columns',
            ),
            html.Img(
                src="https://cleanenergysolutions.org/sites/default/files/clean-energy-investment-accelerator-2-300x88.png",
                className='two columns',
                style={
                    'height': '15%',
                    'width': '15%',
                    'float': 'right',
                    'position': 'relative',
                    'padding-top': 10,
                    'padding-right': 0
                },
            ),
            html.P(
                'A decision support system for renewable adoption by distribution utilities.',
                style={'font-family': 'Helvetica',
                       "font-size": "120%",
                       "width": "80%"},
                className='eight columns',
            ),
        ],
        className='row'
    ),

    html.Div(
        [
        html.Div([
            html.P("End Year of RPS:"),
            dcc.Dropdown(
                id='end_year',
                options=[{'label':i, 'value': i} for i in range(2030,2051,5)],
                value=2030)
                ],
            className = 'three columns',
            style={'margin-top': '20px'}
        ),

        html.Div([
            html.P("Demand Annual (MWh):"),
            dcc.Input(id="demand", value=100000, type="text")
                ],
            className = 'three columns',
            style={'margin-top': '20px'}
        ),

        html.Div([
            html.P("Existing Eligible RE Annual Generation (MWh):"),
            dcc.Input(id="eligible_re_2018", value=10000, type="text",),
                ], 
            className = 'three columns',
            style={'margin-top': '20px'}
        ),
        ], 
    className = 'row'
    ),

    html.Div(
        [
        html.Div([
            html.P("Annual Demand Growth (%):"),
            dcc.Slider(
                id='demand_growth',
                min=0,
                max=15,
                value=4.5,
                step=0.25,
                marks={
                    0:{'label':'0%', 'style': {'color': '#77b0b1'}},
                    3:{'label':'3%', 'style': {'color': '#77b0b1'}},
                    6:{'label':'6%', 'style': {'color': '#77b0b1'}},
                    9:{'label':'9%', 'style': {'color': '#77b0b1'}},
                    12:{'label':'12%', 'style': {'color': '#77b0b1'}},
                    15:{'label':'15%', 'style': {'color': '#77b0b1'}}
                    })
                ],
            className = 'three columns',
            style={'margin-top': '20px'}
        ),
        
        html.Div([
            html.P("2020-2023 Annual RPS Increment (%):"),
            dcc.Slider(
                id='annual_rps_inc_2020',
                min=0,
                max=3,
                value=1,
                step=0.25,
                marks={
                    0:{'label':'0%', 'style': {'color': '#77b0b1'}},
                    1:{'label':'1%', 'style': {'color': '#77b0b1'}},
                    2:{'label':'2%', 'style': {'color': '#77b0b1'}},
                    3:{'label':'3%', 'style': {'color': '#77b0b1'}},
                    })
                ],
            className = 'three columns',
            style={'margin-top': '20px'}
        ),

        html.Div([
            html.P("2023-On Annual RPS Increment (%):"),
            dcc.Slider(
                id='annual_rps_inc_2023',
                min=0,
                max=3,
                value=1,
                step=0.25,
                marks={
                    0:{'label':'0%', 'style': {'color': '#77b0b1'}},
                    1:{'label':'1%', 'style': {'color': '#77b0b1'}},
                    2:{'label':'2%', 'style': {'color': '#77b0b1'}},
                    3:{'label':'3%', 'style': {'color': '#77b0b1'}},
                    })
                ],
            className = 'three columns',
            style={'margin-top': '20px'}
        ),

        html.Div([
            html.P("Line Losses (%):"),
            dcc.Slider(
                id='losses',
                min=0,
                max=25,
                value=12.5,
                step=0.5,
                marks={
                    0:{'label':'0%', 'style': {'color': '#77b0b1'}},
                    5:{'label':'5%', 'style': {'color': '#77b0b1'}},
                    10:{'label':'10%', 'style': {'color': '#77b0b1'}},
                    15:{'label':'15%', 'style': {'color': '#77b0b1'}},
                    20:{'label':'20%', 'style': {'color': '#77b0b1'}},
                    25:{'label':'25%', 'style': {'color': '#77b0b1'}},
                    })
                ],
            className = 'three columns',
            style={'margin-top': '20px'}
        ),

    html.Div([
        html.Button(id="submit-button", n_clicks=0, children="Submit")
        ],
        className = 'four columns',
        style={'margin-top':'50px'}
    ),

        ],
        className = 'row'
    ),

html.Div([
    html.Div([
        dcc.Graph(id="rec_balance")
    ], 
    className = 'six columns')
],
className = 'row',
)

], 
className='ten columns offset-by-one'
)

@app.callback(
    Output("rec_balance", "figure"),
    [Input("submit-button", "n_clicks")],
    [
        State("demand", "value"),
        State("demand_growth", "value"),
        State("eligible_re_2018", "value"),
        State("annual_rps_inc_2020", "value"),
        State("annual_rps_inc_2023", "value"),
        State("losses", "value"),
        State("end_year", "value"),
    ])
def html_REC_balance_maker(n_clicks, demand, demand_growth, eligible_re_2018,annual_rps_inc_2020, annual_rps_inc_2023, losses,
                            end_year):

    demand = float(demand)
    demand_growth = float(demand_growth) / 100
    eligible_re_2018 = float(eligible_re_2018)
    annual_rps_inc_2020 = float(annual_rps_inc_2020) / 100
    annual_rps_inc_2023 = float(annual_rps_inc_2023) / 100
    losses = float(losses) / 100
    end_year = int(end_year)

    df = rps_df_maker(demand=demand, demand_growth=demand_growth, eligible_re_2018=eligible_re_2018,
                    annual_rps_inc_2020=annual_rps_inc_2020, annual_rps_inc_2023=annual_rps_inc_2023, losses=losses,
                    end_year=end_year)
    print(df)

    dfout = df[['demand','rec_req','rec_balance','rec_change']]
    dfout.columns = ['Demand (MWh)','RPS Retirements (RECs)','REC Balance (RECs)','REC Balance Change (RECs)']

    traces = []
    for c in dfout.columns:
        trace = go.Bar(
                x = list(dfout.index),
                y = list(dfout[c]),
                name = c)
        traces.append(trace)

    layout = go.Layout(barmode='group',
                        height = 800,
                        xaxis = dict(
                                tickmode = 'linear',
                                dtick=1))

    # fig = go.Figure(data=traces, layout=layout)
    # py.offline.plot(fig, filename='grouped-bar.html')
    return {"data":traces, "layout":layout}

if __name__ == "__main__":
    app.run_server(debug=True)