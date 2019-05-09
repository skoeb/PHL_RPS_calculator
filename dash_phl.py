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
import json as json_func

dummy_df = pd.read_csv('dummy_df.csv')
dummy_df['Year'] = dummy_df.index
dummy_df_display = dummy_df[['Year','demand','rec_req','rec_balance','rec_change']]
dummy_df_display.columns = ['Year','Demand (MWh)','RPS Requirement (RECs/MWhs)','REC Balance (RECs)','REC Balance Change (RECs)']

irena_lcoe_df = pd.read_csv("irena_lcoe.csv")
irena_lcoe_df = irena_lcoe_df.dropna(subset = ['Technology'])

dummy_lcoe_df = pd.read_csv("dummy_lcoe.csv")

energy_mix_df = pd.read_csv("energy_mix.csv")
energy_mix_df = energy_mix_df.set_index('resource', drop=True)
energy_mix_dict = energy_mix_df.to_dict()['pct']

dummy_desired_pct_df = pd.read_csv("dummy_desired_pct.csv")

color_dict = {
    'biomass':('#00b159'),
    'geothermal':('#d11141'),
    'wind':('#00aedb'),
    'solar':('#ffc425'),
    'utility-scale solar':('#ffc425'),
    'other':('#f37735'),
    'hydro':('#115CBF'),
    'coal':('#222222'),
    'natural gas':('#DE8F6E'),
    'wesm':('#004777')
}


def rps_df_maker(demand, demand_growth, eligible_re_2018,
                 annual_rps_inc_2020, annual_rps_inc_2023,
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

    df['fit'] =  eligible_re_2018
    fit_requirement = df['fit'].copy()
    fit_requirement[2018] = 0
    fit_requirement[2019] = 0
    df['rec_req'] = (df['rps_req'] * df['demand']) + fit_requirement

    
    df['rec_change'] = df['fit'] - df['rec_req']
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
                'Philippines Renewable Portfolio Standard Planning Calculator [BETA]',
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
                'A decision support tool for renewable energy planning for distribution utilities and rural cooperatives.',
                style={'font-family': 'Helvetica',
                       'position':'left',
                       'width':'80%'},
                className='twelve columns',
            ),
            dcc.Markdown("""
                The Philippines RPS is a legislative mandate requiring utilities to increase their use of renewable resources including
                *“biomass, waste to energy technology, wind, solar, run-of-river, impounding hydropower sources that meet internationally accepted standards, ocean, hybrid systems, 
                geothermal and other RE technologies that may be later identified by the DOE."* 
                
                The RPS requires all utilities to increase their utilization of renewable energy by 1% of their total demand per year begining in 2020, although this number could increase in the future.
                For many utilities, the lower costs and customer satisfaction withrenewables is encouraging adoption above what the RPS requires.
                This calculator is designed to help utilities understand when they will need to procure additional renewable capacity, and how procuring additional renewables can result in cost savings.
                """.replace('  ', ''),
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
                    In this portion of the calculator, enter basic data about your utility such as your annual demand,
                    and existing renewables. While RECs are created based on renewable generation (including line losses), RPS requirements are based on sales (demand).
                    For the sake of simplicity, losses are ignored by this calculator, but consider them when deciding how much renewables you need to build. 

                    * Existing Eligible RE Annual Generation includes generation received from Feed-in-Tariffs,
                    existing customer net-metering installations, and other renewables owned or contracted by the utility which have been installed since 2008. Keep in mind that this number does not include *all* renewable power, such as renewables built before 2008. 
                    * The default Annual RPS Increment is 1% per year, although this is subject to change.
                    Other factors, such as elections in 2022 could also have an impact on this policy. Additionally, utilities often desire going beyond this requirement in order to convey to their customers that they are supporting renewable energy or to achieve cost savings.
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
            dcc.Input(id="eligible_re_2018", value=3000, type="text")
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
                value=5.75,
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
            className = 'four columns',
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
            className = 'four columns',
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
            className = 'four columns',
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

    html.Div([
        dcc.Markdown("""
    Not only will additional renewables help you meet your RPS requirements while providing your customers with cleaner electricity, but renewables
    are now more cost-effective than fossil-fuel generators too. The International Renewable Energy Agency (IRENA) Tracks the annual benchmark Levelized Cost of Energy (LCOE)
    for various renewable technologies. An LCOE comprises the all-in cost of energy generation on a per kWh basis, for renewables this accounts for differences in equipment and installation costs, 
    differences in resource capacity factor, and operations & maintence expenses. For fossil-fuel generators, the LCOE also includes the cost of fuel such as coal or natural gas,
     which is often volitle in the Philippines. 

    IRENA's 2017 data suggests that the global LCOE for renewables ranges from $0.05 (Php 2.5) per kWh for hydro to $0.10 (Php 2.5) per kWh for solar installations. Keep in mind that these are median values,
    and that ranges between the fifth and ninety-fifth percentile are displayed in the graph below. Also understand that some technologies, like geothermal or hydro might only be suitable for larger capacity installations,
    while solar, biomass, and wind are more likely to be scalable to your custom capacity requirements. 
    """.replace('  ', ''))
    ],
    className='twelve columns',
    style={'margin-top':20}
    ),
    
    html.Div([
        html.Div([
            dcc.Markdown(id="economic_text", children=["init"])
        ],
        className = 'seven columns',
        style={'margin-top':20}
        ),

        html.Div([
                html.H5('Update the LCOE and MWh numbers here:'),

                dash_table.DataTable(
                id='lcoe_table',
                columns=[{'name':i, 'id':i} for i in dummy_lcoe_df.columns],
                data=dummy_lcoe_df.to_dict('records'),
                style_cell_conditional=[
                    {
                'if': {'column_id': c},
                'textAlign': 'middle'
                    } for c in ['Source of Power']
                ],
                style_as_list_view=True,
                style_cell={'font-family': 'Helvetica', 'font-size':'115%', 'maxWidth':100,'whiteSpace':'normal'},
                style_table={'max-height':550, 'overflowY':'scroll'},
                editable=True
                )
        ],
        className = 'five columns',
        style={'margin-top':20}
        ),
    ],
    className='row',
    ),

    html.Div([
        html.Div([
            dcc.Graph(id='lcoe_graph')
        ],
        className = 'twelve columns',
        style={'margin-top':20}),
    ],
    className='row'),

    html.Div([
            dcc.Markdown(id='savings_text')
        ],
        className = 'twelve columns',
        style={'margin-top':0}),

],
    className='row',
),

html.Div([
    html.Div([
        html.Hr(id='hr4')
    ],
    className = 'twelve columns',
    style={'margin-left':'auto','margin-right':'auto'}
    ),

    html.Div([
        html.H3(
            'Part 4: Goal Setting'
    )],
    className='twelve columns',
    style={'margin-top':-20}
    ),

    html.Div([
            dcc.Markdown(id='goal_text')
        ],
        className = 'twelve columns',
        style={'margin-top':0}),

    html.Div([
        
        html.Div([
            dcc.Graph(id='doughnut_graph')
        ],
        className = 'eight columns',
        ),

        html.Div([
            html.P("Your Utilities Desired Renewables Percent:"),
            dcc.Slider(
                id='desired_pct',
                min=10,
                max=100,
                value=30,
                step=1,
                marks={
                    20:{'label':'20%', 'style': {'color': '#77b0b1'}},
                    40:{'label':'40%', 'style': {'color': '#77b0b1'}},
                    60:{'label':'60%', 'style': {'color': '#77b0b1'}},
                    80:{'label':'80%', 'style': {'color': '#77b0b1'}},
                    100:{'label':'100%', 'style': {'color': '#77b0b1'}},
                    })
                ],
            className = 'four columns',
            style={'margin-top': 20}
            ),
        
        html.Div([
            dcc.RadioItems(
                id='scenario_radio',
                options=[
                    {'label':'Utility-Scale Solar Growth', 'value':'SUN'},
                    {'label':'High Net-Metering and GEOP Adoption', 'value':'NEM'},
                    {'label':'Balanced Utility-Scale, Net-Metering, and GEOP Solar Adoption','value':'SUNALL'},
                    {'label':'Wind Growth', 'value':'WND'},
                    {'label':'Biomass Growth', 'value':'BIO'},
                    {'label':'Geothermal Growth', 'value':'GEO'},
                    {'label':'Hydro Growth', 'value':'HYDRO'},
                    {'label':'Balanced Renewable Adoption', 'value':'BAL'},
                ],
                value='BAL'
            )
            ],
            className='four columns',
            style={'margin-top':60}
            ),
    ],
    className='row',
    ),



    # html.Div([
    #             dash_table.DataTable(
    #             id='desired_pct_table',
    #             columns=[{'name':i, 'id':i} for i in dummy_desired_pct_df.columns],
    #             data=dummy_desired_pct_df.to_dict('records'),
    #             style_cell_conditional=[
    #                 {
    #             'if': {'column_id': c},
    #             'textAlign': 'middle'
    #                 } for c in ['Source of Power']
    #             ],
    #             style_as_list_view=True,
    #             style_cell={'font-family': 'Helvetica', 'font-size':'115%', 'maxWidth':100,'whiteSpace':'normal'},
    #             style_table={'max-height':550, 'overflowY':'scroll'},
    #             editable=True
    #             )
    # ],
    # className = 'six columns',
    # style={'margin-top':60}
    # ),

],
className='row',
),

html.Div(id='intermediate_df', style={'display':'none'}),
html.Div(id='intermediate_df_capacity', style={'display':'none'}),
html.Div(id='intermediate_dict_scenario', style={'display':'none'}),
html.Div(id='intermediate_lcoe_df', style={'display':'none'}),
dcc.Markdown("""
Todo:
* Format integers as strings with commas
* Check with Marlon about email
* Figure out how to change color of Update Scenario button, or do away with and have autoupdates?
* List capacity factors, or find a better way to expalin. This is kind of included in the LCOE table though. 
* Add in project pipeline (i.e. confirmed projects)?
* Add citations
* Add CEIA footer
* Other additional text needs?
* URL redirect to CEIA
* Double check sensitivities, try to break things
* Make sure I'm understanding how line losses are incorporated in the RPS
* Copy text out of editor and into Word to spell check
""")

# dcc.Storage(id='intermediate_dict_scenario', storage_type='session'),

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
        State("end_year", "value"),
    ])
def df_initializer(n_clicks, demand, demand_growth, eligible_re_2018,annual_rps_inc_2020, annual_rps_inc_2023,
                            end_year):
    demand = float(demand)
    demand_growth = float(demand_growth) / 100
    eligible_re_2018 = float(eligible_re_2018)
    annual_rps_inc_2020 = float(annual_rps_inc_2020) / 100
    annual_rps_inc_2023 = float(annual_rps_inc_2023) / 100
    end_year = int(end_year) + 1

    df = rps_df_maker(demand=demand, demand_growth=demand_growth, eligible_re_2018=eligible_re_2018,
                    annual_rps_inc_2020=annual_rps_inc_2020, annual_rps_inc_2023=annual_rps_inc_2023,
                    end_year=end_year)
    df = round(df, 3)
    #print(df)
    return df.to_json()

@app.callback(
    Output('lcoe_table', 'data'),
    [Input("submit-button", "n_clicks"),
    Input('intermediate_df','children')],
    [State('lcoe_table','data'),
    State('lcoe_table','columns')]
)
def current_generation_updater(n_clicks, json, rows, columns):
    df = pd.read_json(json)
    lcoe_df = pd.DataFrame(rows, columns=[c['name'] for c in columns])

    starting_demand = list(df['demand'])[0]

    guess_solar = round(starting_demand * energy_mix_dict['Utility-Scale Solar'])
    guess_nem = round(starting_demand * energy_mix_dict['Net-Metering'])
    guess_geop = round(starting_demand * energy_mix_dict['GEOP'])
    guess_fit = round(starting_demand * energy_mix_dict['Feed-in-Tariff'])
    guess_wind = round(starting_demand * energy_mix_dict['Wind'])
    guess_hydro = round(starting_demand * energy_mix_dict['Hydro'])
    guess_biomass = round(starting_demand * energy_mix_dict['Biomass'])
    guess_geothermal = round(starting_demand * energy_mix_dict['Geothermal'])
    guess_coal = round(starting_demand * energy_mix_dict['Coal'])
    guess_ng = round(starting_demand * energy_mix_dict['Natural Gas'])
    guess_oil = round(starting_demand * energy_mix_dict['Oil'])
    guess_wesm = round(starting_demand * energy_mix_dict['WESM'])

    lcoe_df['Current Annual Generation from Source (MWh)'] = [
        guess_solar, guess_nem, guess_geop, guess_fit, guess_wind, guess_geothermal, guess_hydro,
        guess_biomass, guess_coal, guess_ng, guess_oil, guess_wesm
    ]

    return lcoe_df.to_dict('records')

# @app.callback(
#     Output('lcoe_table','data'),
#     [Input('intermediate_lcoe_df','children')
#     ]
# )
# def lcoe_table_updater(json):
#     lcoe_df = pd.read_json(json)
#     return lcoe_df.to_dict('records')

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
    dfout = round(dfout, 0)
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

    df['solar_need'] = df.apply(new_capacity_calc, args=([0.17]), axis = 1)
    df['geothermal_need'] = df.apply(new_capacity_calc, args=([0.79]), axis = 1)
    df['hydro_need'] = df.apply(new_capacity_calc, args=([0.48]), axis = 1)
    df['wind_need'] = df.apply(new_capacity_calc, args=([0.30]), axis = 1)
    df['biomass_need'] = df.apply(new_capacity_calc, args=([0.86]), axis = 1)

    # first_year_of_need = df.rec_balance.lt(0).idxmax()
    #all_at_once_dict = {}
    #for c in df[['solar_need','geothermal_need','hydro_need','wind_need','biomass_need']]:
    #    all_at_once_dict[c] = df[c].sum()
    #    df[f"{c}_all_at_once"] = 0
    #    df.loc[first_year_of_need, f"{c}_all_at_once"] = all_at_once_dict[c]

    df = df[['solar_need','geothermal_need','wind_need','biomass_need','hydro_need','rec_balance']]
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
        Based on the inputed data, your utility will require new capacity by {first_year_of_need},
        although contracting and construction both take time, so you should consider building renewables before they are needed. 

        To meet the RPS, you need Renewable Energy Certificates (RECs), which represent 1 MWh of renewable generation. By 2030,
        your utility needs to procure a total of **{total_recs}** RECs, starting with **{first_year_recs}** in {first_year_of_need}.

        Because different types of renewable generators produce electricity at different rates, or capacity factors, the amount of capacity
        needed to procure this many RECs varies by the type of renewable resource. 
        To meet the entirity of your DU's RPS requirement through {last_year}, you will need approximately **{solar_total} MW**
        of new solar capacity with a 26% capacity factor. Or, around **{geothermal_total} MW** of geothermal, which has a higher capacity factor of 77%.
        """.replace('  ', '')
    else:
        out="""
        Your utility will not need any Renewable Energy Certificates (RECs) to meet the RPS under this scenario, 
        but that does not mean that you still shouldn't consider installing additional renewable energy. Additional renewables can
        reduce your reliance on expensive imported fossil fuels, which will reduce your generation costs and rate volitility. 
        Customers will also be more likely to choose your service knowing that the power is clean. 
        """.replace('  ','')

    return out


@app.callback(
    Output('lcoe_graph', 'figure'),
    [Input('intermediate_lcoe_df','children')]
)
def lcoe_graph(json):

    input_cost_df = pd.read_json(json)

    input_traces = []
    traces = []
    line_traces = []
    spacer_traces = []
    for t in ['Utility-Scale Solar','Wind','Geothermal','Biomass','Hydro']:

        color = color_dict[t.lower()]
        dfloc = irena_lcoe_df.loc[irena_lcoe_df['Technology'] == t]
        min_2010 = round(dfloc.loc[(dfloc['Year'] == 2010) & (dfloc['Item'] == 'MIN')]['pesos'][0:1].item(),2)
        max_2010 = round(dfloc.loc[(dfloc['Year'] == 2010) & (dfloc['Item'] == 'MAX')]['pesos'][0:1].item(),2)
        avg_2010 = round(dfloc.loc[(dfloc['Year'] == 2010) & (dfloc['Item'] == 'AVG')]['pesos'][0:1].item(),2)
        min_2017 = round(dfloc.loc[(dfloc['Year'] == 2017) & (dfloc['Item'] == 'MIN')]['pesos'][0:1].item(),2)
        max_2017 = round(dfloc.loc[(dfloc['Year'] == 2017) & (dfloc['Item'] == 'MAX')]['pesos'][0:1].item(),2)
        avg_2017 = round(dfloc.loc[(dfloc['Year'] == 2017) & (dfloc['Item'] == 'AVG')]['pesos'][0:1].item(),2)

        input_cost = input_cost_df.loc[input_cost_df['Source of Power'] == t, 'Levelized Cost of Energy (₱ / kWh)'][0:1].item()

        #.2 serves as an offset from the y axis
        x = [1.2,1.2,1.2,1.2,1.2,1.2,2.2,2.2,2.2,2.2,2.2,2.2]
        y = [min_2010,min_2010,avg_2010,avg_2010,max_2010,max_2010,min_2017,min_2017,avg_2017,avg_2017,max_2017,max_2017]

        trace = go.Box(
                x=x,
                y=y,
                name=t,
                boxpoints=False,
                width = 0.2,
                line=dict(width=2, color=color),
                )
        traces.append(trace)
        
        input_trace = go.Scatter(
                x=[3.2],
                y=[input_cost],
                name=t,
                marker=dict(size=12, color=color))
        input_traces.append(input_trace)
        
        line_trace = go.Scatter(
                x=[1.2,2.2],
                y=[avg_2010,avg_2017],
                line = dict(
                    color = color,
                    width = 3,
                    dash = 'dash'),
                name=t
                )
        line_traces.append(line_trace)
        
        spacer_trace = go.Scatter(
                    x=[1],
                    y=[1],
                    opacity=0)
        spacer_traces.append(spacer_trace)
    
    fig = tls.make_subplots(rows=1, cols=len(traces), shared_yaxes=True, horizontal_spacing=0.03,
                            subplot_titles=['Utility-Scale Solar','Wind','Geothermal','Biomass','Hydro'])
    
    fig['layout'].update(title='Global Average LCOE of Renewables')

    for i, t in enumerate(traces):
        fig.append_trace(t, 1, i + 1)
        
    for i, t in enumerate(line_traces):
        fig.append_trace(t, 1, i + 1)
        
    for i, t in enumerate(input_traces):
        fig.append_trace(t, 1, i + 1)

    for i, t in enumerate(spacer_traces):
        fig.append_trace(t, 1, i + 1)

    fig['layout'].update(boxmode='group', showlegend=False, margin=dict(l=60,r=20,b=50,t=70,pad=0))

    for i in range(1,len(traces) + 1):
        fig['layout'][f'xaxis{i}'].update(tickvals=[1,1.2,2.2,3.2],
        ticktext=[' ','Global<br>2010 LCOE','Global<br>2017 LCOE','Your Actual<br>2019 LCOE'],
        tickangle=0, tickfont=dict(size=10))
        
    fig['layout']['yaxis'].update(title='₱ / kWh LCOE', range=[0,20])
    
    return fig

# @app.callback(
#     Output('desired_pct_table','data'),
#     [
#         Input('lcoe_table','data'),
#         Input('lcoe_table','columns'),
#     ]
# )
# def update_desired_capacity_table(rows, columns):
#     lcoe_df = pd.DataFrame(rows, columns=[c['name'] for c in columns])
#     lcoe_df['Percent of Supply from Source'] = lcoe_df['Current Annual Generation from Source (MWh)'] / lcoe_df['Current Annual Generation from Source (MWh)'].sum()
#     lcoe_df['Percent of Supply from Source'] = lcoe_df['Percent of Supply from Source'] * 100
#     lcoe_df['Percent of Supply from Source'] = round(lcoe_df['Percent of Supply from Source'], 0)

#     lcoe_out_df = lcoe_df[['Source of Power','Percent of Supply from Source']]
    
#     return lcoe_out_df.to_dict('records')
    
@app.callback(
    Output('intermediate_lcoe_df','children'),
    [
        Input('lcoe_table','data'),
        Input('lcoe_table','columns')
        ]
)
def lcoe_table_to_intermediate(rows, columns):
    lcoe_df = pd.DataFrame(rows, columns=[c['name'] for c in columns])
    return lcoe_df.to_json()


@app.callback(
    Output('intermediate_dict_scenario','children'),
    [
    Input('intermediate_df','children'),
    Input('intermediate_lcoe_df','children'),
    Input('desired_pct','value'),
    Input('scenario_radio','value')
    ]
)
def scenario_dict_maker(json, json2, desired_pct, scenario_tag):

    df = pd.read_json(json)
    lcoe_df = pd.read_json(json2)
    lcoe_df = lcoe_df.sort_index()

    desired_pct = desired_pct/100

    lcoe_df['start_price'] = lcoe_df['Levelized Cost of Energy (₱ / kWh)'] * lcoe_df['Current Annual Generation from Source (MWh)'] * 1000

    start_year = list(df.index)[0]
    end_year = list(df.index)[-1]
    start_demand = list(df.demand)[0]
    end_demand = list(df.demand)[-1]
    start_recs = list(df.fit)[0]

    re_tech = ['Utility-Scale Solar','Net-Metering','GEOP','Feed-in-Tariff','Wind','Geothermal','Biomass','Hydro']
    fossil_tech = ['Coal', 'Natural Gas','Oil', 'WESM Purchases']

    start_re = lcoe_df.loc[lcoe_df['Source of Power'].isin(re_tech)]['Current Annual Generation from Source (MWh)'].sum()
    start_re_pct = round(start_re / start_demand,2)
    start_expense = round(lcoe_df['start_price'].sum(),0)

    scenario_pct_dict = {
        'SUN':{'Utility-Scale Solar':1},
        'NEM':{'Net-Metering':0.5, 'GEOP':0.5},
        'SUNALL':{'Utility-Scale Solar':0.34, 'Net-Metering':0.33, 'GEOP':0.33},
        'WND':{'Wind':1},
        'BIO':{'Biomass':1},
        'GEO':{'Geothermal':1},
        'HYDRO':{'Hydro':1},
        'BAL':{'Utility-Scale Solar':0.15, 'Net-Metering':0.14, 'GEOP':0.14, 'Wind':0.14, 'Biomass':0.14, 'Geothermal':0.14, 'Hydro':0.14}
    }

    new_re_need = (end_demand  * desired_pct) - start_re #include losses, because this is interms of generation pct, not RECS

    fossil_need = end_demand - new_re_need - start_re

    scenario = scenario_pct_dict[scenario_tag]

    lcoe_df['future_generation'] = 0
    for f in re_tech:
        current_gen_f = lcoe_df.loc[lcoe_df['Source of Power'] == f]['Current Annual Generation from Source (MWh)'][0:1].item()
        if f in scenario.keys():
            lcoe_df.loc[lcoe_df['Source of Power'] == f, 'future_generation'] = (scenario[f] * new_re_need) + current_gen_f
        else:
            lcoe_df.loc[lcoe_df['Source of Power'] == f, 'future_generation'] = current_gen_f
    
    for f in fossil_tech:
        current_pct_f = lcoe_df[lcoe_df['Source of Power'] == f]['Current Annual Generation from Source (MWh)'][0:1].item() / lcoe_df['Current Annual Generation from Source (MWh)'].sum()
        lcoe_df.loc[lcoe_df['Source of Power'] == f, 'future_generation'] = fossil_need * current_pct_f
    
    lcoe_df['future_price'] = lcoe_df['Levelized Cost of Energy (₱ / kWh)'] * lcoe_df['future_generation'] * 1000
    end_expense = round(lcoe_df['future_price'].sum(),0)

    techs = list(lcoe_df['Source of Power'])
    end_generation_list = list(lcoe_df['future_generation'])
    start_generation_list = list(lcoe_df['Current Annual Generation from Source (MWh)'])

    end_re = lcoe_df.loc[lcoe_df['Source of Power'].isin(re_tech)]['future_generation'].sum()
    end_recs = end_re - (start_re - start_recs)

    rps_min_increase = df['rec_req'].sum() / df['demand'].sum()

    #print(lcoe_df)

    output_dict = dict()
    output_dict['start_year'] = int(start_year)
    output_dict['start_demand'] = int(start_demand)
    output_dict['start_re'] = int(start_re)
    output_dict['start_recs'] = int(start_recs)
    output_dict['start_re_pct'] = float(start_re_pct)
    output_dict['start_expense'] = int(start_expense)
    output_dict['start_generation_list'] = [int(i) for i in start_generation_list]
    output_dict['end_year'] = int(end_year)
    output_dict['end_demand'] = int(end_demand)
    output_dict['end_re'] = int(end_re)
    output_dict['end_recs'] = float(end_recs)
    output_dict['end_re_pct'] = float(desired_pct)
    output_dict['end_expense'] = int(end_expense)
    output_dict['end_generation_list'] = [int(i) for i in end_generation_list]
    output_dict['techs'] = techs
    output_dict['rps_min_increase'] = rps_min_increase

    return json_func.dumps(output_dict)

@app.callback(Output('doughnut_graph', 'figure'),
[
    Input('intermediate_dict_scenario','children')
])
def doughnut_graph(json):
    input_dict = json_func.loads(json)

    fossil_start_generation = sum(input_dict['start_generation_list'][-4:])
    # solar_start_generation = sum(input_dict['start_generation_list'][0:3])
    start_generation_list = input_dict['start_generation_list'][0:-4] + [fossil_start_generation]

    fossil_end_generation = sum(input_dict['end_generation_list'][-4:])
    # solar_end_generation = sum(input_dict['end_generation_list'][0:3])
    end_generation_list = input_dict['end_generation_list'][0:-4] + [fossil_end_generation]

    techs = input_dict['techs'][0:-4] + ['Fossil']

    start = go.Pie(
            labels=techs,
            values=start_generation_list,
            marker={'colors': [
                                '#ffc425',
                                '#FFD25C',
                                '#FFDC80',
                                '#f37735',
                                '#00aedb',
                                '#d11141',
                                '#115CBF',
                                '#00b159',
                                '#222222',
                                ]},
            domain={"column": 0},
            textinfo='none',
            hole = 0.4,
            hoverinfo = 'label+percent',
            sort=False,
            title=f"{input_dict['start_year']} <br>{int(input_dict['start_re_pct'] * 100)}% Renewables")
    
    end = go.Pie(
            labels=techs,
            values=end_generation_list,
            marker={'colors': [
                                '#ffc425',
                                '#FFD25C',
                                '#FFDC80',
                                '#f37735',
                                '#00aedb',
                                '#d11141',
                                '#115CBF',
                                '#00b159',
                                '#222222',
                                ]},
            domain={"column": 1},
            textinfo='none',
            hole=0.4,
            hoverinfo = 'label+percent',
            sort=False,
            title=f"{input_dict['end_year']} Power Mix<br>{int(input_dict['end_re_pct'] * 100)}% Renewables")

    traces = [start, end]

    layout = go.Layout(autosize = True, grid={"rows": 1, "columns": 2},showlegend=True, title=f"Current Power Mix and in {input_dict['end_year']} Scenario")
    fig = go.Figure(data = traces, layout = layout)

    return fig

@app.callback(
    Output("economic_text","children"),
    [Input('intermediate_lcoe_df','children')]
)
def economic_text_maker(json):
    lcoe_df = pd.read_json(json)

    solar_cost = lcoe_df.loc[lcoe_df['Source of Power'] == 'Utility-Scale Solar']['Levelized Cost of Energy (₱ / kWh)'][0:1].item()
    biomass_cost = lcoe_df.loc[lcoe_df['Source of Power'] == 'Biomass']['Levelized Cost of Energy (₱ / kWh)'][0:1].item()
    coal_cost = lcoe_df.loc[lcoe_df['Source of Power'] == 'Coal']['Levelized Cost of Energy (₱ / kWh)'][0:1].item()


    out = f"""
    One fact that is certain is the dramatic decline in cost of renewables. Since 2010, the average LCOE for solar has declined 72% from $0.36 (Php 18) to $0.10 (Php 2.5) per kWh.
    Wind's LCOE has declined 25% from $0.08 (Php 4) to $0.06 (Php 3) per kWh, while other technolgies like geothermal, biomass, and hydro have remained constant or seen slight increases in cost. **Any of these renewable resources are likely less expensive on a per kWh basis than coal or natural gas**. The Philippine's largest utility, MERALCO, reports that it pays over $0.12 (₱ 6) per kWh from coal generators, 
    while another utility, CEPALCO, reports paying over $0.16 (Php 8) per kWh for it's coal generation. For most utilities, the cost of natural gas is also high at an average of $0.11 (Php 5.5). 

    The *Levelized Cost of Energy (₱ / kWh)* column in the table to the right is pre-populated with average values. You can edit this column to reflect prices that are specific to your utility. 
    Based on the current entries, the cost of utility-scale solar for you is **Php {round(solar_cost - coal_cost, 1)} / kWh** compared with the cost of coal generation,
    and the cost of biomass has a difference of **Php {round(biomass_cost - coal_cost, 1)} / kWh**. In the next column, *Current Annual Generation from Source (MWh)*, you can input the number of MWhs your utility currently
    procures from each source of power. The default values are based on the demand you entered above, scaled to the proportional Philippine's energy mix. Please enter exact values in this column if possible. 

    Finally, consider the economics of programs such as solar net-metering and the new Green Energy Option Program (GEOP), which allow customers to build their own renewables while providing the utility with RECs. 
    In some cases, these programs offer utilities the least-expensive method of procuring new RECs.
   """.replace('  ', '')

    return out
    
@app.callback(
    Output("savings_text","children"),
    [Input('intermediate_dict_scenario','children')]
)
def savings_text_maker(json):
    input_dict = json_func.loads(json)

    start_cost = int(input_dict['start_expense'])
    start_demand = input_dict['start_demand']
    start_cost_kwh = round(start_cost / start_demand / 1000,1)

    end_re_pct = input_dict['end_re_pct']

    end_cost = input_dict['end_expense']
    end_demand = input_dict['end_demand']
    end_cost_kwh = round(end_cost / end_demand / 1000,1)

    out = f"""
    ##### Your current generation costs are Php {start_cost}, or **Php {start_cost_kwh} / kWh**. By switching to **{int(end_re_pct * 100)}% renewables** in {input_dict['end_year']}, your generation costs would be Php {end_cost}, or **Php {end_cost_kwh} / kWh**. Currently you are creating {input_dict['start_recs']} RECS, and in 2030 you would be creating {int(input_dict['end_recs'])} RECs per year.
        """.replace('  ', '')

    return out

@app.callback(
    Output("desired_pct","value"),
    [Input('intermediate_df','children'),
    Input('intermediate_lcoe_df','children')]
)
def desired_pct_updater(json, json2):
    df = pd.read_json(json)
    lcoe_df = pd.read_json(json2)

    re_tech = ['Utility-Scale Solar','Net-Metering','GEOP','Feed-in-Tariff','Wind','Geothermal','Biomass','Hydro']
    start_re = lcoe_df.loc[lcoe_df['Source of Power'].isin(re_tech)]['Current Annual Generation from Source (MWh)'].sum()
    start_re_pct = start_re / lcoe_df['Current Annual Generation from Source (MWh)'].sum()

    rps_min_increase = df['rec_req'].sum() / df['demand'].sum()
    minimum_desired_pct = start_re_pct + rps_min_increase

    return minimum_desired_pct * 100
    
@app.callback(
    Output("goal_text","children"),
    [Input('intermediate_dict_scenario','children')]
)
def goal_text_maker(json):
    
    input_dict = json_func.loads(json)

    rps_min_increase = input_dict['rps_min_increase'] * 100


    out = f"""
    While the RPS will require your utility to increase your renewable energy penetration by {rps_min_increase}, it is likely cost-effective to go beyond this amount.
    Additional renewable procurement will further decrease your reliance on import fossil-fuels with volitle proces and will make your customers happy to know they purchase
    their electricity from a proactive and forward-looking utility. Aditional renewables also allow you to bank RECs, which can be sold through the WESM as a secondary revenue stream,
    or held for future compliance years. 

    Using the slider below, you can change the desired percentage of renewables for your utility. This has been preset at the minimum RPS requirement created by the policy scenario input in Part 1. 
    Below the slider, you can also select the mix of renewables that will be installed. As you change the desired renewable percentage and the mix of new renewables, the price per kWh above and the energy mix
    displayed in the doughnut-charts below will change. 
   """.replace('  ', '')

    return out

if __name__ == "__main__":
    app.run_server(debug=True)