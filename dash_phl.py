import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Input, State
import plotly.graph_objs as go
import pandas as pd
import requests
import pandas as pd
import plotly.tools as tls

dummy_df = pd.read_csv('dummy_df.csv')
dummy_df['Year'] = dummy_df.index
dummy_df_display = dummy_df[['Year','demand','rec_req','rec_balance','rec_change']]
dummy_df_display.columns = ['Year','Demand (MWh)','RPS Requirement (RECs/MWhs)','REC Balance (RECs)','REC Balance Change (RECs)']

color_dict = {
    'biomass':('#00b159'),
    'geothermal':('#d11141'),
    'wind':('#00aedb'),
    'solar':('#ffc425'),
    'other':('#f37735')
}

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

server = app.server

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
                className='nine columns',
            ),
            html.Img(
                src="https://cleanenergysolutions.org/sites/default/files/clean-energy-investment-accelerator-2-300x88.png",
                className='one columns',
                style={
                    'height': '5%',
                    'width': '15%',
                    'float': 'right',
                    'position': 'relative',
                    'padding-top': 0,
                    'padding-right': 0
                },
            ),
            html.H4(
                'A decision support system for renewable adoption by distribution utilities.',
                style={'font-family': 'Helvetica',
                       'position':'left',
                       'width':'80%'},
                className='twelve columns',
            ),
            dcc.Markdown(
                "The Philippines RPS is a legislative mandate requiring utilities to increase their use of renewable resources such as solar, wind, hydropower, and biomass. The RPS requires all utilities to increase their utilization of renewable energy by 1% of their total demand per year. For many utilities, the lower costs and customer demand for renewables is encouraging adoption above what the RPS requires. This calculator is designed to help utilities understand when they will need to procure additional renewable capacity, and how procuring additional renewables can result in savings.",
                # style={'font-family':'Helvetica','horizontalAlign':'left', 'font-size':18},
                className='twelve columns',
            ),
        ],
        className='row',
    ),

#Part 1
    html.Div(
        [
        
        html.Div([
            html.Hr(id='hr1')
        ],
        className = 'twelve columns',
        style={'margin-left':'auto','margin-right':'auto'}
        ),

        html.Div([
            html.H3(
                'Part 1: Your RPS Requirements',
            )],
            className='twelve columns',
            style={'margin-top':-40}),

        html.Div([
            dcc.Markdown("""
                    * In this portion of the calculator, enter basic data about your distribution utility such as your annual demand,
                    existing renewables, and line losses.
                    * Existing Eligible RE Annual Generation includes generation received from Feed-in-Tariffs,
                    existing customer net-metering installations, and other renewables owned or contracted by the distribution utility which have been installed since 2008.
                    * The default Annual RPS Increment is 1% per year, although this is subject to change.
                    Other factors, such as elections in 2022 could also have an impact on this policy. Additionally, distribution utilities often desire going beyond this requirement in order to convey to their customers that they are supporting renewable energy or to achieve cost savings.
                    * Please contact the CEIA's in-country lead––Marlon Apanada––with any questions at [amj@allatropevc.com](amj@allatropevc.com)
            """.replace('  ',''))],
            # html.Ul([html.Li(x) for x in part_1_bullets])],
            className='twelve columns',
            # style={'font-family':'Helvetica','font-size':18,'margin-top':0},
            ),
        ],
        className='row',
    ),

#Selectors
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
            style={'margin-top': 20}
        ),

        html.Div([
            html.P("Demand Annual (MWh):"),
            dcc.Input(id="demand", value=100000, type="text")
                ],
            className = 'three columns',
            style={'margin-top': 20}
        ),

        html.Div([
            html.P("Existing Eligible RE Annual Generation (MWh):"),
            dcc.Input(id="eligible_re_2018", value=5000, type="text")
                ], 
            className = 'three columns',
            style={'margin-top': 20}
        ),

        html.Div([
        html.Button(id="submit-button", n_clicks=0, children="Update Scenario")
        ],
        className = 'one columns',
        style={'margin-top':50}
        ),

        ], 
    className = 'row',
    style={'alignVertical':True}
    ),

    html.Div(
        [
        html.Div([
            html.P("Annual Demand Growth:"),
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
            style={'margin-top': 20}
        ),
        
        html.Div([
            html.P("2020-2023 Annual Increment:"),
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
            style={'margin-top': 20}
        ),

        html.Div([
            html.P("2023-End Annual Increment:"),
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
            style={'margin-top': 20}
        ),

        html.Div([
            html.P("Line Losses:"),
            dcc.Slider(
                id='losses',
                min=0,
                max=25,
                value=15,
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
            style={'margin-top': 20}
        ),


        ],
        className = 'row'
    ),

html.Div([
    html.Div([
        dcc.Graph(id="demand_and_REC_graph")
    ], 
    className = 'six columns',
    style={'margin-top':'60px'}),

    html.Div([
       dash_table.DataTable(
            id='demand_and_REC_table',
            columns=[{'name':i, 'id':i} for i in dummy_df_display.columns],
            data=dummy_df_display.to_dict('records'),
            style_cell_conditional=[
                {
            'if': {'column_id': c},
            'textAlign': 'middle'
                } for c in ['Year']
            ],
            style_as_list_view=True,
            style_cell={'font-family': 'Helvetica', 'font-size':'115%', 'maxWidth':100,'whiteSpace':'normal'},
            style_table={'max-height':550, 'overflowY':'scroll'}
            )
    ],
    className = 'six columns',
    style={'margin-top':60}),

],
className = 'row',
),

html.Div([

    html.Div([
        html.Hr(id='hr2')
    ],
    className = 'twelve columns',
    style={'margin-left':'auto','margin-right':'auto'}
    ),

    html.Div([
        html.H3(
            'Part 2: Future Capacity Needs'
        )],
        className='twelve columns',
        style={'margin-top':-20}
        ),

    html.Div([
        html.Div([
            dcc.Markdown(id="capacity_text", children=["init"])
        ],
        className = 'five columns',
        style={'margin-top':20}),

        html.Div([
            dcc.Graph(id="capacity_simple_graph")
        ],
        className = 'seven columns',
        style={'margin-top':20}),
    ],
    className = 'row',
    style={'alignVertical':True},
    ),

],
    className = 'row',
),

html.Div([

    html.Div([
        html.Hr(id='hr3')
    ],
    className = 'twelve columns',
    style={'margin-left':'auto','margin-right':'auto'}
    ),

    html.Div([
        html.H3(
            'Part 3: Economic Analysis'
        )],
        className='twelve columns',
        style={'margin-top':-20}
        ),
]),

html.Div(id='intermediate_df', style={'display':'none'}),
html.Div(id='intermediate_df_capacity', style={'display':'none'})

], 
className='ten columns offset-by-one'
)

@app.callback(
    Output("intermediate_df", "children"),
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
def df_initializer(n_clicks, demand, demand_growth, eligible_re_2018,annual_rps_inc_2020, annual_rps_inc_2023, losses,
                            end_year):
    demand = float(demand)
    demand_growth = float(demand_growth) / 100
    eligible_re_2018 = float(eligible_re_2018)
    annual_rps_inc_2020 = float(annual_rps_inc_2020) / 100
    annual_rps_inc_2023 = float(annual_rps_inc_2023) / 100
    losses = float(losses) / 100
    end_year = int(end_year) + 1

    df = rps_df_maker(demand=demand, demand_growth=demand_growth, eligible_re_2018=eligible_re_2018,
                    annual_rps_inc_2020=annual_rps_inc_2020, annual_rps_inc_2023=annual_rps_inc_2023, losses=losses,
                    end_year=end_year)
    df = round(df, 0)
    return df.to_json()

@app.callback(
    Output('demand_and_REC_graph', 'figure'),
    [Input('intermediate_df', 'children')]
)
def html_REC_balance_graph(json):
    df = pd.read_json(json)

    dfout_dem = df[['demand','rec_req']]
    dfout_dem.columns = ['Demand (MWh)','RPS Requirement (RECs/MWhs)']

    dfout_rec = df[['rec_balance','rec_change']]
    dfout_rec.columns = ['REC Balance (RECs)','REC Balance Change (RECs)']

    color_count = 0
    traces_rec = []
    for c in dfout_rec.columns:
        color_ = list(color_dict.values())[color_count]
        trace = go.Bar(
                x = list(dfout_rec.index),
                y = list(dfout_rec[c]),
                name = c,
                marker = dict(color=color_))
        traces_rec.append(trace)
        color_count+=1
    
    traces_dem = []
    for c in dfout_dem.columns:
        color_ = list(color_dict.values())[color_count]
        trace = go.Bar(
                x = list(dfout_dem.index),
                y = list(dfout_dem[c]),
                name = c,
                marker = dict(color=color_))
        traces_dem.append(trace)
        color_count+=1

    fig = tls.make_subplots(rows=2, cols=1, specs = [[{}], [{}]],
                            shared_xaxes=True, vertical_spacing = 0.1)

    for t in traces_dem:
        fig.append_trace(t, 1, 1)
    
    for t in traces_rec:
        fig.append_trace(t, 2, 1)
    
    fig['layout'].update(height=550, barmode='group', xaxis=dict(tickmode='linear', dtick=1))
    fig['layout'].update(legend=dict(orientation="h"))
    fig['layout']['yaxis1'].update(title='MWhs')
    fig['layout']['yaxis2'].update(title='RECs')
    fig['layout']['margin'].update(l=60,r=20,b=100,t=50,pad=0)
    fig['layout'].update(title = 'RPS Requirements and REC Balance by Year')
    
    return fig
    
@app.callback(
    Output('demand_and_REC_table', 'data'),
    [Input('intermediate_df', 'children')]
)
def html_REC_balance_table(json):
    df = pd.read_json(json)
    df['Year'] = df.index
    dfout = df[['Year','demand','rec_req','rec_balance','rec_change']]
    dfout.columns = ['Year','Demand (MWh)','RPS Requirement (RECs/MWhs)','REC Balance (RECs)','REC Balance Change (RECs)']
    dictout = dfout.to_dict('records')
    return dictout

@app.callback(
    Output('intermediate_df_capacity', 'children'),
    [Input('intermediate_df', 'children')]
)
def df_capacity_updater(json):
    df = pd.read_json(json)

    def new_capacity_calc(row, capacity_factor):
        mwh_need = row['rec_balance']
        if mwh_need < 0:
            mw_need = (abs(mwh_need) / 8760) / capacity_factor
            return mw_need
        else:
            return 0

    df['solar_need'] = df.apply(new_capacity_calc, args=([0.26]), axis = 1)
    df['geothermal_need'] = df.apply(new_capacity_calc, args=([0.77]), axis = 1)
    # df['hydro_need'] = df.apply(new_capacity_calc, args=([0.43]), axis = 1)
    df['wind_need'] = df.apply(new_capacity_calc, args=([0.37]), axis = 1)
    df['biomass_need'] = df.apply(new_capacity_calc, args=([0.49]), axis = 1)

    # first_year_of_need = df.rec_balance.lt(0).idxmax()
    #all_at_once_dict = {}
    #for c in df[['solar_need','geothermal_need','hydro_need','wind_need','biomass_need']]:
    #    all_at_once_dict[c] = df[c].sum()
    #    df[f"{c}_all_at_once"] = 0
    #    df.loc[first_year_of_need, f"{c}_all_at_once"] = all_at_once_dict[c]

    df = round(df, 2)
    return df.to_json()

@app.callback(
    Output('capacity_simple_graph', 'figure'),
    [Input('intermediate_df_capacity','children')]
)
def capacity_requirement_simple_graph(json):
    df = pd.read_json(json)

    traces = []
    for c in df.columns:
        if 'need' in c:
            color_ = color_dict[c.split('_')[0]]
            trace = go.Scatter(
                x=list(df.index),
                y=list(df[c]),
                name=c.replace('_',' ').capitalize(),
                mode='lines+markers',
                line=dict(shape='hv', color=color_, width = 3),
                )
            traces.append(trace)

    layout = dict(
            height=450,
            title='Capacity (MW) Needs with Different Renewable Resource Types'
            )

    fig = go.Figure(data=traces, layout=layout)

    fig['layout']['yaxis'].update(title='MW')
    fig['layout']['margin'].update(l=60,r=20,b=100,t=50,pad=0)
    fig['layout'].update(legend=dict(orientation="h"))

    return fig

@app.callback(
    Output("capacity_text","children"),
    [Input('intermediate_df_capacity','children')]
)
def capacity_text_maker(json):
    df = pd.read_json(json)
    first_year_of_need = df.rec_balance.lt(0).idxmax()
    last_year = max(df.index)
    solar_total = round(df.solar_need.sum(),2)
    geothermal_total = round(df.geothermal_need.sum(),2)
    total_recs = round(abs(df[df['rec_balance'] < 0]['rec_balance'].sum()),0)
    first_year_recs = round(df.loc[first_year_of_need, 'rec_balance'],0)

    if first_year_recs < 0: #make sure that any recs will be needed
        first_year_recs = abs(first_year_recs)
        out = f"""
        Based on the inputed data, your distribution utility will require new capacity by {first_year_of_need},
        although contracting and construction both take time, so you should consider building renewables before they are needed. 

        To meet the RPS, you need Renewable Energy Certificates (RECs), which represent 1 MWh of renewable generation. By 2030,
        your distribution utility needs to procure a total of **{total_recs}** RECs, starting with **{first_year_recs}** in {first_year_of_need}.

        Because different types of renewable generators produce electricity at different rates, or capacity factors, the amount of capacity
        needed to procure this many RECs varies by the type of renewable resource. 
        To meet the entirity of your DU's RPS requirement through {last_year}, you will need approximately **{solar_total} MW**
        of new solar capacity with a 26% capacity factor. Or, around **{geothermal_total} MW** of geothermal, which has a higher capacity factor of 77%.
        """.replace('  ', '')
    else:
        out="""
        Your distribution utility will not need any Renewable Energy Certificates (RECs) to meet the RPS under this scenario, 
        but that does not mean that you still shouldn't consider installing additional renewable energy. Additional renewables can
        reduce your reliance on expensive imported fossil fuels, which will reduce your generation costs and rate volitility. 
        Customers will also be more likely to choose your service knowing that the power is clean. 
        """.replace('  ','')

    return out

if __name__ == "__main__":
    app.run_server(debug=True)