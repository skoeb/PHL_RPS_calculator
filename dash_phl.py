import dash
import dash_table
import dash_daq as daq
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
dummy_df_display.columns = ['Year','Demand (MWh)','RPS Requirement','REC Balance','REC Balance Change']

irena_lcoe_df = pd.read_csv("irena_lcoe.csv")
irena_lcoe_df = irena_lcoe_df.dropna(subset = ['Technology'])

dummy_lcoe_df = pd.read_csv("dummy_lcoe.csv")

energy_mix_df = pd.read_csv("energy_mix.csv")
energy_mix_df['Percent of Utility Energy Mix'] = energy_mix_df['Percent of Utility Energy Mix'] * 100

new_build_df = pd.DataFrame({'Generation Source':['Utility-Scale Solar', '', ''],
                            'Annual Generation (MWh)': [0, '',''],
                            'Online Year': [2020,'','']})

dummy_desired_pct_df = pd.read_csv("dummy_desired_pct.csv")

utility_df = pd.read_csv("utility_data.csv", index_col='utility')
utility_dict = utility_df[~utility_df.index.duplicated(keep='first')].to_dict('index')

re_tech = ['Utility-Scale Solar','Net-Metering','GEOP','Wind','Geothermal','Biomass','Hydro']
fossil_tech = ['Coal', 'Natural Gas','Oil', 'WESM Purchases']

color_dict = {
    'biomass':('#00b159'),
    'geothermal':('#d11141'),
    'wind':('#00aedb'),
    'solar':('#ffc425'),
    'distributed PV':('#FFE896'),
    'utility-scale solar':('#ffc425'),
    'other':('#f37735'),
    'hydro':('#115CBF'),
    'coal':('#222222'),
    'natural gas':('#DE8F6E'),
    'wesm':('#004777')
}


def rps_df_maker(demand, demand_growth, future_procurement, fit_MW,
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

    df['fit'] =  fit_MW
    initial_fit_pct = fit_MW / demand

    future_procurement = future_procurement.groupby(['Online Year'], as_index=False)['Annual Generation (MWh)'].sum()
    future_procurement = future_procurement.rename({'Online Year':'year'}, axis='columns')
    future_procurement = future_procurement.set_index('year')
    dummy_years = df.copy() #for forward fill join
    dummy_years = dummy_years.drop(dummy_years.columns, axis='columns')
    future_procurement = dummy_years.merge(future_procurement, left_index=True, right_index=True, how='outer').sort_index()
    future_procurement = future_procurement.fillna(0)
    future_procurement['Annual Generation (MWh)'] = future_procurement['Annual Generation (MWh)'].cumsum()

    df['future_procurement'] = future_procurement['Annual Generation (MWh)']

    fit_requirement = pd.Series(initial_fit_pct, index = df.index)
    fit_requirement[2018] = 0
    fit_requirement[2019] = 0
    df['rps_req'] = df['rps_req'] + fit_requirement

    demand_for_calc = df['demand'].copy()
    demand_for_calc.index = [i + 1 for i in demand_for_calc.index]
    demand_for_calc.loc[2018] = 0
    demand_for_calc.loc[2019] = 0
    demand_for_calc.loc[2020] = df['demand'][2018]
    demand_for_calc = demand_for_calc.sort_index()
    df['demand_for_calc'] = demand_for_calc

    df['rec_req'] = df['rps_req'] * df['demand_for_calc']

    df['rec_change'] = (df['fit'] + df['future_procurement']) - df['rec_req']
    df['rec_balance'] = df['rec_change'].cumsum()

    return df
    
app = dash.Dash(__name__)

app.title = 'CEIA RPS Calculator'

server = app.server

# # Boostrap CSS.
# app.css.append_css({
#     "external_url":"https://codepen.io/chriddyp/pen/bWLwgP.css"
# })

app.layout = html.Div([

# Title - Row
    html.Div([
        html.H1(
            'Philippines Renewable Portfolio Standard Planning Calculator',
            style={'font-family': 'Helvetica',
                "margin-top": "25",
                "margin-bottom": "0"},
            className='nine columns',
        ),
        html.A([
            html.Img(
                src="assets/CEIA_Header_Logo.png",
                className='two columns',
                style={
                    'height': '20%',
                    'width': '20%',
                    'float': 'right',
                    'position': 'relative',
                    'padding-top': 10,
                    'padding-right': 0
                },
            )], href='https://www.cleanenergyinvest.org'),

        html.H4(
            'A decision support tool for renewable energy planning for utilities.',
            style={'font-family': 'Helvetica',
                'position':'left',
                'width':'100%'},
            className='twelve columns',
        )
    ],
    className='row',
    ),

    html.Div([

        html.Div([

            html.Div([
                html.Img(
                    src='assets/Tricolor_Spacer_Wide.png',
                    className='twelve columns')
            ],
            className = 'twelve columns',
            style={'margin-left':'auto','margin-right':'auto'}
            ),

            html.Div([
                html.H3(
                    'Overview and Data Input:',
                )],
                className='twelve columns',
                style={'margin-top':0}),

            html.Div([
                dcc.Markdown("""
                    The Philippines RPS is a legislative mandate requiring utilities to increase their use of renewable resources including
                    *“biomass, waste to energy technology, wind, solar, run-of-river, impounding hydropower sources that meet internationally accepted standards, ocean, hybrid systems, 
                    geothermal and other RE technologies that may be later identified by the DOE."* 
                    
                    The RPS requires all utilities to increase their utilization of renewable energy by 1% of their total demand (kWh) per year beginning in 2020. Although this percentage can be increased in the future by the National Renewable Energy Board.
                    For many utilities, the lower costs and higher customer satisfaction with renewables is encouraging adoption above what the RPS requires. This calculator is designed to help utilities understand when they will need to procure additional renewable capacity, and how procuring additional renewables can result in cost savings.

                    Click through the tabs below to input data for your utility, more details about each input can be found by hovering your mouse over the circled question-mark symbols.
                    """.replace('  ', ''),
                    className='twelve columns',
                ),
            ]),
        ]),

#Selectors
        html.Div([

            dcc.Tabs(id='utility_inputs', value='acronym', parent_className='custom-tabs', className='custom-tabs-container',
                children=[

                dcc.Tab(label='Automatic Utility Data Lookup', className='custom-tab', selected_className='custom-tab--selected', value='acronym',
                    children=[
                            html.Div([
                                html.Div([
                                    html.P("Enter Utility Acronym:",style={'display':'inline-block'}),
                                    #added question-mark 
                                    html.Div([
                                        ' \u003f\u20dd',
                                        html.Span('When a utility name (acronym) is selected, data such as annual demand, demand growth, and FiT allocation are automatically loaded from a 2017 DOE Database.'
                                        , className="tooltiptext")], className="tooltip", style={'padding-left':5}),
                                    dcc.Dropdown(
                                        id='utility_name',
                                        options=[{'label':i, 'value':i} for i in list(utility_dict.keys())],
                                        multi=False,
                                        value='MERALCO',
                                    )
                                ])
                            ], style={'margin-top': 30, 'margin-bottom':30})
                        ]),
                
                dcc.Tab(label='RPS Policy Details', className='custom-tab', selected_className='custom-tab--selected', value='rps-details',
                        children=[
                            html.Div([
                                html.Div([
                                    html.P("End Year of RPS:", style={'display':'inline-block'}),
                                    #added question-mark 
                                    html.Div([
                                        ' \u003f\u20dd',
                                        html.Span('Under current law, the RPS will expire in 2030, however this could be extended.'
                                        , className="tooltiptext")], className="tooltip", style={'padding-left':5}),
                                    dcc.Dropdown(
                                        id='end_year',
                                        options=[{'label':i, 'value': i} for i in range(2030,2051,5)],
                                        clearable=False,
                                        multi=False,
                                        value=2030)
                                        ],
                                    className = 'four columns',
                                    # style={'margin-top': 20}
                                ),

                                html.Div([
                                    html.P("2020-23 RPS Increment (%):",
                                    style={'display':'inline-block'}),
                                    #added question mark
                                    html.Div([
                                        '\u003f\u20dd',
                                        html.Span('The annual marginal increase of the RPS requirement, the current law requires 1%, however this could be increased in the future.'
                                        , className="tooltiptext")], className="tooltip", style={'padding-left':5}),        
                                    dcc.Input(id='annual_rps_inc_2020',value=1,type='number',step=0.25,style={'width':'100%'}, min=0.25)
                                        ],
                                    className='four columns',
                                    # style={'margin-top': 20}
                                ),

                                html.Div([
                                    html.P("2023 - End RPS Increment (%):",
                                    style={'display':'inline-block'}),
                                    #added question mark
                                    html.Div([
                                        '\u003f\u20dd',
                                        html.Span('The annual marginal increase of the RPS requirement, the current law requires 1%, however this could be increased in the future.'
                                        , className="tooltiptext")], className="tooltip", style={'padding-left':5}),        
                                    dcc.Input(id='annual_rps_inc_2023',value=1,type='number',step=0.25,style={'width':'100%'}, min=0.25)
                                        ],
                                    className='four columns',
                                ),
                            ], style={'margin-top':30, 'margin-bottom':126}) #not entirely sure why this is precisely 126, but it is so that tab lengths are even
                        ]),
                                
                dcc.Tab(label='Energy Mix and Cost Input', className='custom-tab', selected_className='custom-tab--selected', value='energy-mix',
                    children=[
                            html.Div([
                                html.Div([
                                    #Table Inputs for Energy Mix and Future Procurement
                                    html.P("Update Cells with Utility Cost and Energy Mix Data:",
                                    style={'display':'inline-block'}),
                                    #added question mark
                                    html.Div([
                                        '\u003f\u20dd',
                                        html.Span('For each generation source, please enter the Levelized Cost of Energy (LCOE) and percent of utility energy mix supplied by each generation source. For more information on what LCOE is, please refer to Part 3. The percent of utility energy mix represents generation supplied by each resource type divided by the total amount of supplied generation, this column must sum to 100%. Default LCOE data is from IRENA regional averages for South East Asia. Default values for percent of utility energy mix are derived from the average energy-mix for all utilities in the Philippines.'
                                        , className="tooltiptext")], className="tooltip", style={'padding-left':5}),

                                    dash_table.DataTable(
                                    id='energy_mix_table',
                                    columns=[{'name':i, 'id':i} for i in energy_mix_df.columns],
                                    data=energy_mix_df.to_dict('records'),
                                    style_cell_conditional=[
                                        {
                                    'if': {'column_id': c},
                                    'textAlign': 'middle'
                                        } for c in ['Generation Source']
                                    ],
                                    style_as_list_view=True,
                                    style_cell={'font-family': 'Helvetica', 'font-size':'90%', 'textAlign':'center', 'maxWidth':100,'whiteSpace':'normal'},
                                    style_table={'max-height':550},
                                    editable=True,
                                    style_data_conditional=[
                                            {
                                            'if': {'column_id':'Generation Source'},
                                            'backgroundColor':'rgb(248, 248, 248)',
                                            'textAlign':'left'
                                            }
                                        ],
                                    style_header={
                                        'backgroundColor':'rgb(230, 230, 230)',
                                        'fontWeight': 'bold'
                                        }),
                                    html.P(' '),
                                    dcc.Markdown(id="energy_mix_error_text", children=["init"]),
                                ],
                                className='six columns',
                                style={'margin-bottom':0, 'verticalAlign':'top'}),

                                html.Div([
                                    html.P("Add Any Planned Renewable Procurement:",
                                    style={'display':'inline-block'}),
                                    #added question mark
                                    html.Div([
                                        '\u003f\u20dd',
                                        html.Span('Use this sheet to add in any planned renewable procurement that will count towards the RPS. For instance, if your utility has signed a solar PPA beginning in 2020, select Utility-Scale Solar as the generation source, and then specify the anticipated annual generation and year that the project will begin producing RECs. Use the Add Row button for additional entries'
                                        , className="tooltiptext")], className="tooltip", style={'padding-left':5}),

                                    dash_table.DataTable(
                                    id='future_procurement_table',
                                    columns=[
                                        {'id':'Generation Source', 'name':'Generation Source', 'presentation':'dropdown'},
                                        {'id':'Annual Generation (MWh)', 'name':'Annual Generation (MWh)'},
                                        {'id':'Online Year', 'name':'Online Year'},
                                    ],
                                    editable=True,
                                    row_deletable=True,
                                    dropdown={
                                        'Generation Source':{
                                            'options':[{'label':i, 'value':i} for i in re_tech]
                                        }
                                    },
                                    # style_as_list_view=True,
                                    style_cell={'font-family': 'Helvetica', 'font-size':'90%', 'textAlign':'center', 'maxWidth':100,'whiteSpace':'normal'},
                                    style_table={'max-height':550},
                                    style_data_conditional=[
                                            {
                                            'if': {'column_id':'Generation Source'},
                                            'textAlign':'left',
                                            'backgroundColor':'rgb(248, 248, 248)'
                                            }
                                        ],
                                    style_header={
                                        'backgroundColor':'rgb(230, 230, 230)',
                                        'fontWeight': 'bold'
                                        },
                                    data=new_build_df.to_dict('records'),
                                        ),
                                    
                                    html.Div([
                                    html.P(' '),
                                    html.Button('Add Row', id='editing-rows-button', n_clicks=0),
                                    ], style={'margin-left':'35%'}),
                                    ],
                                className='six columns',
                                style={'verticalAlign':'top'}
                                ),
                            ], style={'margin-top':30, 'margin-bottom':126}) #not entirely sure why this is precisely 126, but it is so that tab lengths are even
                        ]),

            dcc.Tab(label='Renewable Capacity Factors', className='custom-tab', selected_className='custom-tab--selected', value='capacity-factors',
                    children=[
                            html.Div([
                                html.Div([
                                    #Table Inputs for Energy Mix and Future Procurement
                                    html.P("Enter Renewable Capacity Factors for Your Utility:",
                                    style={'display':'inline-block'}),
                                    #added question mark
                                    html.Div([
                                        '\u003f\u20dd',
                                        html.Span('Capacity factor is a percentage value that represents the actual generation potential of a resource type. It is calculated by dividing the total anticipated generation from a resource for a time period, over the total amount that would be generated if the resource is available at full nameplate capacity for the same time period. Resources such as the Renewable Eenrgy Data Explorer and the System Advisor Model (SAM) can help you determine renewable capacity factors for your area.'
                                        , className="tooltiptext")], className="tooltip", style={'padding-left':5}),
                                ],
                                className='twelve columns',
                                style={'verticalAlign':'top'}),

                                html.Div([
                                    html.Div([
                                        html.P("Solar Capacity Factor:",
                                            style={'margin-bottom':40,'display':'inline-block'}),
                                            
                                        daq.Slider(
                                            id='solar_cf',
                                            min=10,
                                            max=100,
                                            value=17,
                                            step=0.5,
                                            marks={
                                                20:{'label':'20%', 'style': {'color': '#77b0b1'}},
                                                40:{'label':'40%', 'style': {'color': '#77b0b1'}},
                                                60:{'label':'60%', 'style': {'color': '#77b0b1'}},
                                                80:{'label':'80%', 'style': {'color': '#77b0b1'}},
                                                100:{'label':'100%', 'style': {'color': '#77b0b1'}},
                                                },
                                            handleLabel={"showCurrentValue": True,"label": "Percent"},
                                            size={'width':'100%'} #resizes to window
                                        )
                                    ],
                                    className = 'four columns',
                                    style={'margin-top': 30, 'margin-bottom':30}
                                    ),

                                    html.Div([   
                                        html.P("Distributed Solar Capacity Factor:",
                                            style={'margin-bottom':40,'display':'inline-block'}),

                                        daq.Slider(
                                            id='dpv_cf',
                                            min=10,
                                            max=100,
                                            value=15,
                                            step=0.5,
                                            marks={
                                                20:{'label':'20%', 'style': {'color': '#77b0b1'}},
                                                40:{'label':'40%', 'style': {'color': '#77b0b1'}},
                                                60:{'label':'60%', 'style': {'color': '#77b0b1'}},
                                                80:{'label':'80%', 'style': {'color': '#77b0b1'}},
                                                100:{'label':'100%', 'style': {'color': '#77b0b1'}},
                                                },
                                            handleLabel={"showCurrentValue": True,"label": "Percent"},
                                            size={'width':'100%'} #resizes to window
                                        )
                                    ],
                                    className = 'four columns',
                                    style={'margin-top': 30, 'margin-bottom':30}
                                    ),

                                    html.Div([   
                                        html.P("Wind Capacity Factor:",
                                            style={'margin-bottom':40,'display':'inline-block'}),

                                        daq.Slider(
                                            id='wind_cf',
                                            min=10,
                                            max=100,
                                            value=30,
                                            step=0.5,
                                            marks={
                                                20:{'label':'20%', 'style': {'color': '#77b0b1'}},
                                                40:{'label':'40%', 'style': {'color': '#77b0b1'}},
                                                60:{'label':'60%', 'style': {'color': '#77b0b1'}},
                                                80:{'label':'80%', 'style': {'color': '#77b0b1'}},
                                                100:{'label':'100%', 'style': {'color': '#77b0b1'}},
                                                },
                                            handleLabel={"showCurrentValue": True,"label": "Percent"},
                                            size={'width':'100%'} #resizes to window
                                        )
                                    ],
                                    className = 'four columns',
                                    style={'margin-top': 30, 'margin-bottom':30}
                                    ),
                                ]),

                                html.Div([
                                    html.Div([
                                        html.P("Geothermal Capacity Factor:",
                                            style={'margin-bottom':40,'display':'inline-block'}),
                                            
                                        daq.Slider(
                                            id='geothermal_cf',
                                            min=10,
                                            max=100,
                                            value=79,
                                            step=0.5,
                                            marks={
                                                20:{'label':'20%', 'style': {'color': '#77b0b1'}},
                                                40:{'label':'40%', 'style': {'color': '#77b0b1'}},
                                                60:{'label':'60%', 'style': {'color': '#77b0b1'}},
                                                80:{'label':'80%', 'style': {'color': '#77b0b1'}},
                                                100:{'label':'100%', 'style': {'color': '#77b0b1'}},
                                                },
                                            handleLabel={"showCurrentValue": True,"label": "Percent"},
                                            size={'width':'100%'} #resizes to window
                                        )
                                    ],
                                    className = 'four columns',
                                    style={'margin-top': 30, 'margin-bottom':30}
                                    ),

                                    html.Div([   
                                        html.P("Biomass Capacity Factor:",
                                            style={'margin-bottom':40,'display':'inline-block'}),

                                        daq.Slider(
                                            id='biomass_cf',
                                            min=10,
                                            max=100,
                                            value=86,
                                            step=0.5,
                                            marks={
                                                20:{'label':'20%', 'style': {'color': '#77b0b1'}},
                                                40:{'label':'40%', 'style': {'color': '#77b0b1'}},
                                                60:{'label':'60%', 'style': {'color': '#77b0b1'}},
                                                80:{'label':'80%', 'style': {'color': '#77b0b1'}},
                                                100:{'label':'100%', 'style': {'color': '#77b0b1'}},
                                                },
                                            handleLabel={"showCurrentValue": True,"label": "Percent"},
                                            size={'width':'100%'} #resizes to window
                                        )
                                    ],
                                    className = 'four columns',
                                    style={'margin-top': 30, 'margin-bottom':30}
                                    ),

                                    html.Div([   
                                        html.P("Hydro Capacity Factor:",
                                            style={'margin-bottom':40,'display':'inline-block'}),

                                        daq.Slider(
                                            id='hydro_cf',
                                            min=10,
                                            max=100,
                                            value=48,
                                            step=0.5,
                                            marks={
                                                20:{'label':'20%', 'style': {'color': '#77b0b1'}},
                                                40:{'label':'40%', 'style': {'color': '#77b0b1'}},
                                                60:{'label':'60%', 'style': {'color': '#77b0b1'}},
                                                80:{'label':'80%', 'style': {'color': '#77b0b1'}},
                                                100:{'label':'100%', 'style': {'color': '#77b0b1'}},
                                                },
                                            handleLabel={"showCurrentValue": True,"label": "Percent"},
                                            size={'width':'100%'} #resizes to window
                                        )
                                    ],
                                    className = 'four columns',
                                    style={'margin-top': 30, 'margin-bottom':30}
                                    ),
                            ]),
                        ]),
                    ]),

                dcc.Tab(label='Manual Utility Data Input (Advanced)', className='custom-tab', selected_className='custom-tab--selected', value='manual',
                        children=[
                            html.Div([
                                html.Div([
                                    html.P("Annual Demand (MWh):",style={'display':'inline-block'}),
                                    #added question-mark 
                                    html.Div([
                                        ' \u003f\u20dd',
                                        html.Span('Annual demand is equal to total electricity sales, this does not include line losses.'
                                        , className="tooltiptext")], className="tooltip", style={'padding-left':5}),
                                    dcc.Input(id="demand", value=418355, type="number",style={'width':'100%'}) #this works RE: 
                                        ],
                                    className = 'four columns',
                                ),

                                html.Div([
                                    html.P("RECs from FiT (MWh):",style={'display':'inline-block'}),
                                    #added question-mark 
                                    html.Div([
                                        '\u003f\u20dd',
                                        html.Span('Under the 2008 RE Law, RECs from customer-subsidized feed-in-tariff projects are allocated to each utility for 3% of their demand'
                                        , className="tooltiptext")], className="tooltip", style={'padding-left':5}),
                                    dcc.Input(id="fit_MW", value=12942, type="number",style={'width':'100%'})
                                        ],
                                    className = 'four columns',
                                ),

                                html.Div([
                                    html.P("Annual Demand Growth (%):",
                                    style={'display':'inline-block'}),
                                    #added question-mark 
                                    html.Div([
                                        '\u003f\u20dd',
                                        html.Span('The rate of electricity growth in your utility service territory, this rate will be applied to the inputed annual demand.'
                                        , className="tooltiptext")], className="tooltip", style={'padding-left':5}),        
                                    dcc.Input(id='demand_growth',value=6.3,type='number',step=0.05,style={'width':'100%'})
                                        ],
                                    className='four columns',
                                ),
                            ], style={'margin-top':30, 'margin-bottom':126}) #not entirely sure why this is precisely 126, but it is so that tab lengths are even
                ]),
            ]),
        ]),
    ]),
    
    #Part 1
    html.Div([
        html.Div([
            html.Img(
                src='assets/Tricolor_Spacer_Wide.png',
                className='twelve columns')],
        className = 'twelve columns',
        style={'margin-left':'auto','margin-right':'auto'}),

        html.Div([
            html.H3(
                'Part 1: Your RPS Requirements')],
            className='twelve columns',
            style={'margin-top':0}),

        html.Div([
            dcc.Markdown("""
                    While your utility may already be using renewable energy, the RPS requires the sourcing of *new* renewable generation built since the implementation of the [2008 RE Law](https://www.doe.gov.ph/sites/default/files/pdf/issuances/dc2009-05-0008.pdf).
                    The level of renewable energy that must be procured is a percentage of your total energy sales; displayed in yellow and blue in the figure below.
                    While the RPS requirement is mandatory for utilities to meet, many often desire going beyond this requirement in order to convey to their customers that they are supporting renewable energy, or to achieve cost savings provided by renewables.

                    In order to demonstrate that your utility is complying with the RPS, you will be required to procure and retire Renewable Energy Certificates (RECs). RECs are bankable credits
                    that convey the environmental attributes for 1 MWh of renewable generation. Owning and retiring a REC allows an entity to make a specific legal claim of renewable energy consumption, 
                    for instance, when a utility retires RECs they can claim that a percentage of the energy-mix they are providing their customers is renewable. Other entities, such as corporations, value RECs as a means to demonstrate voluntary renewable energy purchases.
                    RECs will be entered into an online tracking system––the Renewable Energy Market (REM)––which will be operated through the existing Wholesale Electricity Spot Market (WESM).
                    The REM will allow trading of RECs between third-parties and utilities, although prices are expected to potentially be volatile. For more information on RECs, [please consult this technical report](https://www.nrel.gov/docs/fy19osti/72204.pdf). 

                    The RPS interacts with other components of the 2008 RE Law too, such as the Feed-in-Tariff (FiT) program, which procures blocks of renewable capacity at government-approved rates.
                    Since 2018, all utilities in the Philippines are receiving RECs from FiT projects in proportion to their market share of total electricity sales in the country. As of January 2019,
                    the number of RECs each utility receives is equal to 3.1% of their total sales. Because the RPS treats 2018 as 'year 0' of the RPS, and 2019 as a 'transition year', there is no RPS requirement
                    during these years. However, utilities will receive RECs from the FiT or eligible new renewable projects during this time. Because RECs can be banked for future years,
                    most utilities will enter year 1 (2020) of the RPS with an existing REC balance that will deplete over subsequent years as the RPS requirement increases.
                    
                    The table below displays a projection of RPS requirements for your utility. Additionally, the figures below display data such as
                    the end-of-year REC balance in green and the annual change in REC balance in red. If the REC balance becomes negative in any year, this indicates that additional renewable capacity will need to be procured in advance of the REC shortfall,
                    or REC purchases will need to be made on the spot market. 
            """.replace('  ',''))],
            # html.Ul([html.Li(x) for x in part_1_bullets])],
            className='twelve columns',
            # style={'font-family':'Helvetica','font-size':18,'margin-top':0},
            ),
        ],
        className='row',
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
            style_cell={'font-family': 'Helvetica', 'font-size':'90%', 'textAlign':'center', 'maxWidth':100,'whiteSpace':'normal'},
            style_table={'max-height':550, 'overflowY':'scroll'},
            style_data_conditional=[
                    {
                    'if': {'row_index':'odd'},
                    'backgroundColor':'rgb(248, 248, 248)',
                    }
                ],
            style_header={
                'backgroundColor':'rgb(230, 230, 230)',
                'fontWeight': 'bold'
                }),
        ],
    className='six columns',
    style={'margin-top':60}),
    ],
className = 'row',
),

html.Div([

    html.Div([
        html.Img(
            src='assets/Tricolor_Spacer_Wide.png',
            className='twelve columns')
    ],
    className = 'twelve columns',
    style={'margin-left':'auto','margin-right':'auto'}
    ),

    html.Div([
        html.H3(
            'Part 2: Future Capacity Needs'
    )],
    className='twelve columns',
    style={'margin-top':0}
    ),

    html.Div([
        html.Div([
            dcc.Markdown(id="capacity_text", children=["init"])
        ],
        className = 'twelve columns',
        style={'margin-top':15}),

        html.Div([
            html.H6('1) Purchase renewable capacity up-front:')],
        className='twelve columns'),

        html.Div([
            html.Div([
                dcc.Markdown("""
                One option to comply with the RPS is to procure enough renewable capacity up-front to meet your anticipated RPS requirements in the future.
                This strategy provides the ability to 'bank' RECs in early years for use later. Additionally, large procurement can be less expensive
                on a per-kW basis due to economies of scale. Using the dropdown below, you can select which year to make a one-time renewable procurement, the figure to the right will show the necessary capacity for different renewable
                technologies.
                """.replace('  ', '')),

                html.Div([
                    html.Div([
                        html.P('Select Year for One-Time RE Installation:')
                    ],
                    style={'margin-top':15}),

                    html.Div([
                        dcc.Dropdown(
                        id='one_year_build',
                        options=[{'label':i, 'value': i} for i in range(2019,2030,1)],
                        clearable=False,
                        value=2020),
                    ],
                    style={'margin-top':15}),
                ]),
            ], className='four columns', style={'margin-top':15}),

            html.Div([
                dcc.Graph(id='one_year_build_graph'),
            ],
            className='eight columns', style={'margin-top':15, 'verticalAlign':'top'}),
        ],
        className='twelve columns', style={'verticalAlign':'top'}),

        html.Div([
            html.H6('2) Incremental purchases of renewable capacity:')],
        className='twelve columns'),

        html.Div([
            html.Div([
                dcc.Graph(id="capacity_simple_graph")],
            className = 'eight columns',
            style={'margin-top':15}),

            html.Div([
                dcc.Markdown("""
                A second option is to purchase renewables incrementally to meet the marginal RPS requirement in each year. This strategy involves spreading
                procurement over multiple years, which can hedge risk against the falling costs of renewables. Additionally, this strategy allows
                for growth in distributed energy resources, such as rooftop PV under the net-metering and Green Energy Option Program (GEOP), to count towards your
                RPS capacity needs. 

                In reality, a utility should seek a balance of these two procurement options along with other options such as REC purchases through the WESM.
                This section of the calculator was merely intended to convey the scale of new capacity needed.
                """.replace('  ', '')),
            ],
            className='four columns', style={'margin-top':15}),
        ],
        className='twelve columns'),
    ]),
]),

# Part 3: Economic Analysis
html.Div([

    html.Div([
        html.Img(
            src='assets/Tricolor_Spacer_Wide.png',
            className='twelve columns')
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
    Not only will additional renewables help you meet your RPS requirements while providing customers with cleaner electricity, but renewables
    may be more cost-effective than fossil-fuel generators too. The International Renewable Energy Agency (IRENA) tracks the annual benchmark Levelized Cost of Energy (LCOE)
    for various renewable technologies. An LCOE comprises the all-in cost of energy generation on a per kWh basis, for renewables this accounts for differences in equipment and installation costs, 
    differences in resource capacity factor, and operations & maintenance expenses. For fossil-fuel generators, the LCOE also includes the cost of fuel such as coal or natural gas,
    which is can be in the Philippines. 

    IRENA's 2017 data suggests that the global LCOE for renewables ranges between $0.05 (Php 2.5) per kWh for hydro to $0.10 (Php 5) per kWh for utility-scale solar installations. Keep in mind that these are median values;
    issuing a request for proposals (RFP) or working with a local developer are good ways to better understand what the exact costs will be for you. 
    The graphs below display the median price, along with global prices between the fifth and ninety-fifth percentiles. Also understand that some technologies, like geothermal or hydro might only be suitable for larger capacity installations,
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
        className = 'twelve columns',
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
    className='row')
],
    className='row',
),

html.Div([
    html.Div([
        html.Img(
            src='assets/Tricolor_Spacer_Wide.png',
            className='twelve columns')
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
            dcc.Markdown(id='savings_text')
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
            html.P("Desired Renewables Percent:",
            style={'margin-bottom':40,'display':'inline-block'}),
            #added question-mark 
            html.Div([
                ' \u003f\u20dd',
                html.Span('This value can reflect your RPS goal, incremental RPS targets, or any other aspirational RE percentages.'
                , className="tooltiptext")], className="tooltip", style={'padding-left':5}),        
            daq.Slider(
                id='desired_pct',
                min=10,
                max=100,
                value=30,
                step=0.5,
                marks={
                    20:{'label':'20%', 'style': {'color': '#77b0b1'}},
                    40:{'label':'40%', 'style': {'color': '#77b0b1'}},
                    60:{'label':'60%', 'style': {'color': '#77b0b1'}},
                    80:{'label':'80%', 'style': {'color': '#77b0b1'}},
                    100:{'label':'100%', 'style': {'color': '#77b0b1'}},
                    },
                handleLabel={"showCurrentValue": True,"label": "PERCENT"},
                size={'width':'100%'} #resizes to window
                )
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

#Next Steps
html.Div([
    html.Div([
            html.Img(
                src='assets/Tricolor_Spacer_Wide.png',
                className='twelve columns')
        ],
        className = 'twelve columns',
        style={'margin-left':'auto','margin-right':'auto'}
        ),

    html.Div([
            html.H3(
                'Part 5: Next Steps'
        )],
        className='twelve columns',
        style={'margin-top':-20}
        ),
    
    html.Div([
        dcc.Markdown("""
        So far you have learned what your REC obligations are under the RPS are, you have explored how much capacity is needed for different renewable technologies to meet your utilities obligations, 
        and you have planned for what years you will need to procure renewables by.

        The next step is to conduct a detailed feasibility study examining the techno-economic potential of specific renewable energy projects. To begin this process,
        we recommend the following resources:
        """)
    ],
    className='twelve columns',
    style={'margin-top':30}),
    
    html.Div([
        html.Div([
            html.H6('Renewable Energy Data Explorer')
        ],
        className='twelve columns',
        ),

        html.Div([
            dcc.Markdown("""
            The RE Data Explorer is a user-friendly geospatial analysis tool for analyzing renewable energy potential and informing decisions. 
            It can be used to visualize  capacity factor data for solar, wind, and geothermal resources. 
            Assessing resource technical potential should be one of the first steps when conducting a feasibility study. 
            Examples of how to integrate the RE Data Explorer into your decision support planning process are outlined in [this technical report](https://www.nrel.gov/docs/fy18osti/68913.pdf), 
            and in [this fact-sheet](https://www.nrel.gov/docs/fy18osti/68899.pdf).
            """.replace('  ', ''))
        ],
        className='eight columns',
        style={'margin-left':0, 'margin-top':15}),

        html.A([
            html.Img(
                src='assets/rede_xsmall.png',
                className = 'four columns',
                style={
                    'width':'20%',
                    'height':'auto',
                    'float':'right',
                    'position':'relative',
                    })],
            href='https://www.re-explorer.org/',
        ),
    ],
    className='row'),

    html.Div([
        html.Div([
            html.H6('System Advisor Model')
        ],
        className='twelve columns',
        ),

        html.Div([
            dcc.Markdown("""
            The System Advisor Model (SAM) is a techno-economic model designed to facilitate decision making for people involved in the renewable energy industry.
            SAM provides comprehensive financial analysis and energy output modeling for renewables. This can be used to compare procurement methods such as equity financing,
            debt financing, and power purchase agreements. Outputs from the SAM model include cash-flow, payback period, and net present value.
            Secondly, SAM allows for detailed production modeling, including three-dimensional assessment of shading, azimuth, and supports user upload of custom weather files.
            For a more detailed explanation of SAM, see [this technical report](https://www.nrel.gov/docs/fy14osti/61019.pdf), or visit the [SAM website](https://sam.nrel.gov/forum.html).
            """.replace('  ', ''))
        ],
        className='eight columns',
        style={'margin-left':0, 'margin-top':15}),

        html.A([
            html.Img(
                src='assets/SAM_xsmall.png',
                className = 'four columns',
                style={
                    'width':'20%',
                    'height':'auto',
                    'float':'right',
                    'position':'relative',
                    })],
            href='https://sam.nrel.gov/forum.html',
        ),
    ],
    className='row'),

]),

html.Div([

    html.Div([
        html.Div([
            dcc.Markdown(
                """
                ###### About the CEIA:
                The CEIA is an innovative public-private partnership jointly led by Allotrope Partners, World Resources Institute,
                and the U.S. National Renewable Energy Laboratory. Through targeted engagement in key countries,
                the CEIA unlocks clean energy investment across commercial and industrial sectors.
                The CEIA helps companies meet their clean energy targets and supports countries to meet their climate and development goals.
                This includes implementation of Nationally Determined Contribution investment plans, long-term decarbonization strategies,
                and broader efforts to meet growing energy needs and support strong economic growth.

                Please contact the CEIA's in-country lead––Marlon Apanada––with any questions at [amj@allatropevc.com](amj@allatropevc.com)
                """.replace('  ', '')),
        ],
        className='row'),
    ],
    className = 'input_box',
    style={'margin-top':30}),

    html.Div([
        dcc.Markdown(
            """
            ###### References:
            *Additional tools to help conduct renewable feasibility studies:*

            [System Advisor Model](https://sam.nrel.gov/)

            [Renewable Energy Data Explorer](https://maps.nrel.gov/rede-southeast-asia/)

            [PVWatts](https://pvwatts.nrel.gov/)

            *More information on the RPS can be found in the following Department of Energy Circulars:*

            [Department of Energy. "Prescribing the Share of Renewable Energy Resources in the Country's Installed Capacity..." DC2015-07-0014. Published 2015.](https://www.doe.gov.ph/sites/default/files/pdf/issuances/dc_2015-07-0014.pdf)
            [Department of Energy. "Rules and Regulations Implementing Republic Act No.9513". DC2009-05-0008. Published 2009.](https://www.doe.gov.ph/sites/default/files/pdf/issuances/dc2009-05-0008.pdf)
           
           
            *Additional program information from:*

            [CEIA. "Webinar on Philippine RE at the Crossroads." Presented January 2019.](https://www.youtube.com/watch?v=gd744nnvfWk)


            *LCOE data from:*

            [International Renewable Energy Agency (IRENA). "Renewable Power Generation Costs in 2017." Published 2018.](https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2018/Jan/IRENA_2017_Power_Costs_2018.pdf)
           

            *Additional Price Data from:*

            Biomass Renewable Energy Alliance (BREA). "Biomass: Fueling the Economy of the Philippines". Presented March 2019.
            
            """.replace('  ', '')
        )],
        className = 'input_box',
        style={'margin-top':30}),
    html.Div([
        html.Img(
            src='assets/Tricolor_Spacer_Wide.png',
            className='twelve columns')
    ],
    className = 'twelve columns',
    style={'margin-left':'auto','margin-right':'auto'}
    ),
],
className='row',
),


],
className='row',
),

dcc.Store(id='intermediate_df'),
dcc.Store(id='intermediate_df_capacity'),
dcc.Store(id='intermediate_dict_scenario'),
dcc.Store(id='intermediate_lcoe_df'),

], 
className='ten columns offset-by-one'
)

@app.callback(
    Output('future_procurement_table', 'data'),
    [Input('editing-rows-button', 'n_clicks')],
    [State('future_procurement_table', 'data'),
     State('future_procurement_table', 'columns')])
def add_row(n_clicks, rows, columns):
    if n_clicks > 0:
        rows.append({c['id']: '' for c in columns})
    return rows

@app.callback(
    Output('energy_mix_error_text', 'children'),
    [
        Input('energy_mix_table', 'data'),
        Input('energy_mix_table', 'columns')
    ]
)
def energy_mix_text(rows, columns):
    energy_mix = pd.DataFrame(rows, columns=[c['name'] for c in columns])
    cols = ['Percent of Utility Energy Mix']
    energy_mix[cols] = energy_mix[cols].apply(pd.to_numeric, errors='coerce')

    energy_sum = energy_mix['Percent of Utility Energy Mix'].sum().round(1)
    renewable_sum = energy_mix.loc[energy_mix['Generation Source'].isin(re_tech), 'Percent of Utility Energy Mix'].sum().round(1)

    if energy_sum != 100:
        output = f"""
        **Please edit the 'Percent of Utility Energy Mix' column so that the values sum to 100%. Currently they sum to {energy_sum}%.**
        """.replace('  ', '')
    elif energy_sum == 100:
        output = f"""""".replace('  ', '')
    
    return output


@app.callback(
    Output("fit_MW","value"),
    [Input("demand","value")]
)
def fit_mw_updater(demand):
    if demand != '':
        national_demand = 105529277
        fit_total = 3264621
        utility_fit = round((float(demand)/national_demand)*fit_total)
        return utility_fit

"""
UPDATERS FOR UTILITY NAME INPUT
"""
@app.callback(
    Output("demand","value"),
    [Input("utility_name","value")]
)
def demand_mw_updater(utility):
    output = utility_dict[utility]['sales']
    return output

@app.callback(
    Output("demand_growth","value"),
    [Input("utility_name","value")]
)
def growth_mw_updater(utility):
    output = utility_dict[utility]['growth_floor'] * 100 #scaled to 100
    return output

@app.callback(
    Output("intermediate_df", "data"),
    [
        Input("demand", "value"),
        Input("demand_growth", "value"),
        Input("future_procurement_table", "data"),
        Input("future_procurement_table", "columns"), #needs to be redefined
        Input("fit_MW", "value"),
        Input("annual_rps_inc_2020", "value"),
        Input("annual_rps_inc_2023", "value"),
        Input("end_year", "value"),
    ])
def df_initializer(demand, demand_growth, future_procurement_rows, future_procurement_columns,
                    fit_MW, annual_rps_inc_2020, annual_rps_inc_2023, end_year):

    future_procurement = pd.DataFrame(future_procurement_rows, columns=[c['name'] for c in future_procurement_columns])
    future_procurement = future_procurement.loc[future_procurement['Generation Source'].isin(re_tech)]
    future_procurement = future_procurement.groupby(['Generation Source', 'Online Year'], as_index=False)['Annual Generation (MWh)'].sum()
    
    cols = ['Online Year', 'Annual Generation (MWh)']
    future_procurement[cols] = future_procurement[cols].apply(pd.to_numeric, errors='coerce')

    demand_growth = float(demand_growth) / 100
    annual_rps_inc_2020 = float(annual_rps_inc_2020) / 100
    annual_rps_inc_2023 = float(annual_rps_inc_2023) / 100
    end_year = int(end_year) + 1

    df = rps_df_maker(demand=demand, demand_growth=demand_growth, future_procurement=future_procurement, fit_MW=fit_MW,
                    annual_rps_inc_2020=annual_rps_inc_2020, annual_rps_inc_2023=annual_rps_inc_2023,
                    end_year=end_year)
    df = round(df, 3)
    return df.to_json()

@app.callback(
    Output('demand_and_REC_graph', 'figure'),
    [Input('intermediate_df', 'data')]
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
    [Input('intermediate_df', 'data')]
)
def html_REC_balance_table(json):
    df = pd.read_json(json)
    df['Year'] = df.index
    dfout = df[['Year','demand','rec_req','rec_balance','rec_change']]
    dfout.columns = ['Year','Demand (MWh)','RPS Requirement','REC Balance','REC Balance Change']
    dfout = round(dfout, 0)
    dictout = dfout.to_dict('records')
    return dictout

@app.callback(
    Output('intermediate_df_capacity', 'data'),
    [
        Input('intermediate_df', 'data'),
        Input('solar_cf', 'value'),
        Input('dpv_cf', 'value'),
        Input('wind_cf', 'value'),
        Input('geothermal_cf', 'value'),
        Input('biomass_cf', 'value'),
        Input('hydro_cf', 'value'),

    ]
)
def df_capacity_updater(json, solar_cf, dpv_cf, wind_cf, geothermal_cf, biomass_cf, hydro_cf):
    df = pd.read_json(json)
    def new_capacity_calc(row, capacity_factor):
        mwh_need = abs(row['rec_incremental_req'])
        mw_need = (abs(mwh_need) / 8760) / (capacity_factor/100)
        return mw_need

    df['rec_incremental_req'] = df['rec_change']
    df['rec_incremental_req'] = df['rec_incremental_req'].diff(1)
    df.loc[df['rec_balance'] > 0, 'rec_incremental_req'] = 0
    df['rec_incremental_req'] = abs(df['rec_incremental_req'])


    df['solar_need'] = df.apply(new_capacity_calc, args=([solar_cf]), axis = 1)
    df['distributed PV_need'] = df.apply(new_capacity_calc, args=([dpv_cf]), axis = 1)
    df['geothermal_need'] = df.apply(new_capacity_calc, args=([geothermal_cf]), axis = 1)
    df['hydro_need'] = df.apply(new_capacity_calc, args=([hydro_cf]), axis = 1)
    df['wind_need'] = df.apply(new_capacity_calc, args=([wind_cf]), axis = 1)
    df['biomass_need'] = df.apply(new_capacity_calc, args=([biomass_cf]), axis = 1)

    df = df[['solar_need','distributed PV_need', 'geothermal_need','wind_need','biomass_need','hydro_need','rec_balance','rec_incremental_req', 'rec_req', 'rec_change']]
    df = round(df, 2)

    return df.to_json()

@app.callback(
    Output('capacity_simple_graph', 'figure'),
    [
        Input('intermediate_df_capacity', 'data'),
        Input('solar_cf', 'value'),
        Input('geothermal_cf', 'value'),
    ]
)
def capacity_requirement_simple_graph(json, solar_cf, geothermal_cf):
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
            title='Incremental Capacity (MW) Requirements'
            )

    fig = go.Figure(data=traces, layout=layout)

    fig['layout']['yaxis'].update(title='MW')
    fig['layout']['margin'].update(l=60,r=20,b=100,t=50,pad=0)
    fig['layout'].update(legend=dict(orientation="h"))

    return fig

@app.callback(
    Output("one_year_build_graph","figure"),
    [
        Input('intermediate_df_capacity','data'),
        Input('one_year_build', 'value'),
        Input('solar_cf', 'value'),
        Input('dpv_cf', 'value'),
        Input('wind_cf', 'value'),
        Input('hydro_cf', 'value'),
        Input('geothermal_cf', 'value'),
        Input('biomass_cf', 'value'),
    ]
)
def one_year_build_graph(json, year_of_build, solar_cf, dpv_cf, wind_cf, hydro_cf, geothermal_cf, biomass_cf):
    df = pd.read_json(json)
    last_year = max(df.index)
    last_year_recs = round(df.loc[last_year, 'rec_balance'],0)
    last_year_rec_need = abs(min(0, last_year_recs))

    one_time_build_annual_need = last_year_rec_need / (last_year - year_of_build + 1)
    solar_one_time = (one_time_build_annual_need / 8760) / (solar_cf/100)
    dpv_one_time = (one_time_build_annual_need / 8760) / (dpv_cf/100)
    wind_one_time = (one_time_build_annual_need / 8760) / (wind_cf/100)
    hydro_one_time = (one_time_build_annual_need / 8760) / (hydro_cf/100)
    geothermal_one_time = (one_time_build_annual_need / 8760) / (geothermal_cf/100)
    biomass_one_time = (one_time_build_annual_need / 8760) / (biomass_cf/100)

    labels = ['Utility-Scale Solar', 'Distributed PV', 'Wind', 'Hydro', 'Geothermal', 'Biomass']
    values = [solar_one_time, dpv_one_time, wind_one_time, hydro_one_time, geothermal_one_time, biomass_one_time]
    colors = [color_dict['utility-scale solar'], color_dict['distributed PV'], color_dict['wind'], color_dict['hydro'], color_dict['geothermal'], color_dict['biomass']]
    fig = go.Figure(data=[go.Bar(
                x=labels, y=values,
                text=[f'{int(i):,} MW' for i in values],
                textposition='auto',
                marker = dict(color=colors)
            )])

    fig['layout'].update(title=f'Necessary Capacity for One-Time Renewable Purchase in {year_of_build}')
    fig['layout']['yaxis'].update(title='MW')
    fig['layout']['margin'].update(l=60,r=20,b=100,t=50,pad=0)

    return fig

@app.callback(
    Output("capacity_text","children"),
    [
        Input('intermediate_df_capacity','data'),
        Input('solar_cf', 'value'),
        Input('geothermal_cf', 'value')
    ]
)
def capacity_text_maker(json, solar_cf, geothermal_cf):
    df = pd.read_json(json)
    first_year_of_need = df.rec_balance.lt(0).idxmax()
    last_year = max(df.index)
    total_recs = round(abs(df[df['rec_balance'] < 0]['rec_balance'].sum()),0)
    first_year_recs = round(df.loc[first_year_of_need, 'rec_balance'],0)
    last_year_recs = round(df.loc[last_year, 'rec_balance'],0)


    if first_year_recs < 0: #make sure that any recs will be needed
        first_year_recs = abs(first_year_recs)
        out = f"""
        Based on the input data, your utility will require new capacity by {first_year_of_need}.
        Because contracting and construction both take time, you should consider building renewables before {first_year_of_need}. 
        By {last_year}, your utility needs to procure a cumulative total of **{int(total_recs):,}** RECs, starting with **{int(first_year_recs):,}** RECs in {first_year_of_need}.
        It is important to plan for *when* and *how much* capacity to procure. Two high-level procurement strategies worth considering:
        """.replace('  ', '')
    else:
        out="""
        Your utility will not need any Renewable Energy Certificates (RECs) to meet the RPS under this scenario, 
        but you should still consider installing additional renewable energy. Additional renewables can
        reduce your reliance on expensive imported fossil fuels, which will reduce your generation costs and rate volatility. 
        Customers will also be more likely to choose your service knowing that the power is clean.
        It is important for your utility to plan for *when* and *how much* capacity to procure. Two high-level procurement strategies worth considering:
        """.replace('  ','')

    return out


@app.callback(
    Output('lcoe_graph', 'figure'),
    [
        Input('energy_mix_table','data'),
        Input('energy_mix_table', 'columns')  
    ]
)
def lcoe_graph(rows, columns):

    input_cost_df = pd.DataFrame(rows, columns=[c['name'] for c in columns])

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

        input_cost = input_cost_df.loc[input_cost_df['Generation Source'] == t, 'Levelized Cost of Energy (₱ / kWh)'][0:1].item()

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


@app.callback(
    Output('intermediate_dict_scenario','data'),
    [
    Input('intermediate_df','data'),
    Input('energy_mix_table','data'),
    Input('energy_mix_table', 'columns'),
    Input('desired_pct','value'),
    Input('scenario_radio','value')
    ]
)
def scenario_dict_maker(json, rows, columns, desired_pct, scenario_tag):

    df = pd.read_json(json)

    starting_demand = int(list(df['demand'])[0])

    lcoe_df = pd.DataFrame(rows, columns=[c['name'] for c in columns])
    cols = lcoe_df.columns.drop('Generation Source')
    lcoe_df[cols] = lcoe_df[cols].apply(pd.to_numeric, errors='coerce') #convert all columns to numeric

    desired_pct = desired_pct/100

    lcoe_df['current_MWh'] = (lcoe_df['Percent of Utility Energy Mix'] / 100) * starting_demand

    lcoe_df['start_price'] = lcoe_df['Levelized Cost of Energy (₱ / kWh)'] * lcoe_df['current_MWh'] * 1000

    start_year = list(df.index)[0]
    end_year = list(df.index)[-1]
    start_demand = list(df.demand)[0]
    end_demand = list(df.demand)[-1]
    start_recs = list(df.fit)[0]

    start_re = lcoe_df.loc[lcoe_df['Generation Source'].isin(re_tech)]['current_MWh'].sum()
    start_re_pct = round(start_re / start_demand,2)
    start_expense = round(lcoe_df['start_price'].sum(),0)
    start_fossil = lcoe_df.loc[lcoe_df['Generation Source'].isin(fossil_tech)]['current_MWh'].sum()

    scenario_pct_dict = {
        'SUN':{'Utility-Scale Solar':1},
        'NEM':{'Net-Metering':0.5, 'GEOP':0.5},
        'WND':{'Wind':1},
        'BIO':{'Biomass':1},
        'GEO':{'Geothermal':1},
        'HYDRO':{'Hydro':1},
        'BAL':{'Utility-Scale Solar':1/7, 'Net-Metering':1/7, 'GEOP':1/7, 'Wind':1/7, 'Biomass':1/7, 'Geothermal':1/7, 'Hydro':1/7}
    }

    new_re_need = (end_demand  * desired_pct) - start_re #include losses, because this is interms of generation pct, not RECS
    fossil_need = end_demand * (1-desired_pct)
    scenario = scenario_pct_dict[scenario_tag]

    lcoe_df['future_generation'] = 0
    for f in re_tech:
        current_gen_f = lcoe_df.loc[lcoe_df['Generation Source'] == f, 'current_MWh'][0:1].item()
        if f in scenario.keys():
            lcoe_df.loc[lcoe_df['Generation Source'] == f, 'future_generation'] = (scenario[f] * new_re_need) + current_gen_f
        else:
            lcoe_df.loc[lcoe_df['Generation Source'] == f, 'future_generation'] = current_gen_f


    
    for f in fossil_tech:
        current_pct_f = lcoe_df.loc[lcoe_df['Generation Source'] == f, 'current_MWh'][0:1].item() / start_fossil
        lcoe_df.loc[lcoe_df['Generation Source'] == f, 'future_generation'] = fossil_need * current_pct_f

    lcoe_df['future_price'] = lcoe_df['Levelized Cost of Energy (₱ / kWh)'] * lcoe_df['future_generation'] * 1000
    end_expense = round(lcoe_df['future_price'].sum(),0)

    techs = list(lcoe_df['Generation Source'])
    end_generation_list = list(lcoe_df['future_generation'])
    start_generation_list = list(lcoe_df['current_MWh'])

    end_re = lcoe_df.loc[lcoe_df['Generation Source'].isin(re_tech)]['future_generation'].sum()
    end_recs = end_re - (start_re - start_recs)

    rps_min_increase = df['rps_marginal_req'].sum()

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

    total_gen = sum(end_generation_list)
    end_gen_pct = [round(i/total_gen,2) for i in end_generation_list]
    end_gen_dict = dict(zip(techs, end_gen_pct))
    return json_func.dumps(output_dict)

@app.callback(Output('doughnut_graph', 'figure'),
[
    Input('intermediate_dict_scenario','data')
])
def doughnut_graph(json):
    input_dict = json_func.loads(json)

    fossil_start_generation = sum(input_dict['start_generation_list'][0:3])

    # solar_start_generation = sum(input_dict['start_generation_list'][0:3])
    start_generation_list = input_dict['start_generation_list'][3:] + [fossil_start_generation]

    fossil_end_generation = sum(input_dict['end_generation_list'][0:3])
    # solar_end_generation = sum(input_dict['end_generation_list'][0:3])
    end_generation_list = input_dict['end_generation_list'][3:] + [fossil_end_generation]

    techs = input_dict['techs'][3:] + ['Fossil']

    start = go.Pie(
            labels=techs,
            values=start_generation_list,
            marker={'colors': [
                                # '#545454', #gray
                                # '#00b159', #go green
                                # '#d11141', #crimson
                                # '#115CBF', #denim
                                # '#00aedb', #vivid cerulean (blue)
                                # '#ffc425', #sunglow
                                # '#FFD25C', #mustard
                                # '#FFDC80', #mellow yellow     
                                # '#222222', #rasin black            
                                color_dict['wesm'],
                                color_dict['biomass'],
                                color_dict['geothermal'],
                                color_dict['hydro'],
                                color_dict['wind'],
                                color_dict['utility-scale solar'],
                                color_dict['distributed PV'],
                                '#FFDC80',
                                '#222222',
                                ]},
            domain={"column": 0},
            textinfo='none',
            hole = 0.55,
            hoverinfo = 'label+percent',
            sort=False,
            title=f"{input_dict['start_year']}<br>{int(input_dict['start_re_pct'] *100)}% Renewables")
    
    end = go.Pie(
            labels=techs,
            values=end_generation_list,
            marker={'colors': [
                                color_dict['wesm'],
                                color_dict['biomass'],
                                color_dict['geothermal'],
                                color_dict['hydro'],
                                color_dict['wind'],
                                color_dict['utility-scale solar'],
                                color_dict['distributed PV'],
                                '#FFDC80',
                                '#222222',   
                                ]},
            domain={"column": 1},
            textinfo='none',
            hole=0.55,
            hoverinfo = 'label+percent',
            sort=False,
            title=f"{input_dict['end_year']} Power Mix<br>{int(input_dict['end_re_pct'] * 100)}% Renewables")

    traces = [start, end]

    layout = go.Layout(autosize = True, grid={"rows": 1, "columns": 2},showlegend=True, title=f"Current Power Mix & {input_dict['end_year']} Scenario")
    fig = go.Figure(data = traces, layout = layout)

    return fig

@app.callback(
    Output("economic_text","children"),
    [
        Input('energy_mix_table','data'),
        Input('energy_mix_table','columns')
    ]
)
def economic_text_maker(rows, columns):
    lcoe_df = pd.DataFrame(rows, columns=[c['name'] for c in columns])
    cols = lcoe_df.columns.drop('Generation Source')
    lcoe_df[cols] = lcoe_df[cols].apply(pd.to_numeric, errors='coerce') #convert all columns to numeric

    solar_cost = lcoe_df.loc[lcoe_df['Generation Source'] == 'Utility-Scale Solar']['Levelized Cost of Energy (₱ / kWh)'][0:1].item()
    biomass_cost = lcoe_df.loc[lcoe_df['Generation Source'] == 'Biomass']['Levelized Cost of Energy (₱ / kWh)'][0:1].item()
    coal_cost = lcoe_df.loc[lcoe_df['Generation Source'] == 'Coal']['Levelized Cost of Energy (₱ / kWh)'][0:1].item()


    out = f"""
    The IRENA LCOE data informs us that the price of renewables has declined dramatically in recent years. Since 2010, the average LCOE for solar has declined 72% from $0.36 (Php 18) to $0.10 (Php 5) per kWh.
    Over the same time period, wind's LCOE has declined 25% from $0.08 (Php 4) to $0.06 (Php 3) per kWh, while other technologies like geothermal, biomass, and hydro have remained constant or seen slight increases in cost. Renewables may be less expensive on a per kWh basis than coal or natural gas. 

    The Levelized Cost of Energy (PhP / kWh) data used in this calculator can be changed in the 'Energy Mix and Cost Input' tab of User Inputs. You can edit this to reflect prices that are specific to your utility. 
    Based on the current entries, the cost of utility-scale solar for you is **Php {round(solar_cost - coal_cost, 1)} / kWh** compared with the cost of coal generation,
    and the cost of biomass has a difference of **Php {round(biomass_cost - coal_cost, 1)} / kWh**.

    Finally, consider that some REC procurement can be done through utility programs such as solar net-metering and the new GEOP, which allow customers to build their own renewables while providing the utility with RECs. 
    These programs may offer the least-expensive method of procuring new RECs as the customer pays for the entire system cost, while the utility receives all RECs. 
   """.replace('  ', '')

    return out
    
@app.callback(
    Output("savings_text","children"),
    [Input('intermediate_dict_scenario','data')]
)
def savings_text_maker(json):
    input_dict = json_func.loads(json)

    start_cost = int(input_dict['start_expense'])
    start_demand = input_dict['start_demand']
    start_cost_kwh = round(start_cost / start_demand / 1000,2)

    end_re_pct = input_dict['end_re_pct']

    end_cost = input_dict['end_expense']
    end_demand = input_dict['end_demand']
    end_cost_kwh = round(end_cost / end_demand / 1000,2)

    out = f"""
    ###### Your current generation costs are Php {start_cost:,}, or **Php {start_cost_kwh} / kWh**. By switching to **{int(end_re_pct * 100)}% renewables** in {input_dict['end_year']}, your estimated generation costs would be Php {end_cost:,}, or **Php {end_cost_kwh} / kWh**. Currently you are creating {input_dict['start_recs']:,} RECS, and in 2030 you would be creating {int(input_dict['end_recs']):,} RECs per year. Please keep in mind that there is inherent risk in forecasting future generation costs.
        """.replace('  ', '')

    return out

@app.callback(
    Output("desired_pct","value"),
    [
        Input('intermediate_df','data'),
        Input('energy_mix_table','data'),
        Input('energy_mix_table', 'columns')
    ]
)
def desired_pct_updater(json, rows, columns):
    df = pd.read_json(json)

    lcoe_df = pd.DataFrame(rows, columns=[c['name'] for c in columns])
    cols = lcoe_df.columns.drop('Generation Source')
    lcoe_df[cols] = lcoe_df[cols].apply(pd.to_numeric, errors='coerce') #convert all columns to numeric

    starting_demand = list(df['demand'])[0]
    lcoe_df['current_MWh'] = lcoe_df['Percent of Utility Energy Mix'] * starting_demand

    re_tech = ['Utility-Scale Solar','Net-Metering','GEOP','Feed-in-Tariff','Wind','Geothermal','Biomass','Hydro']
    start_re = lcoe_df.loc[lcoe_df['Generation Source'].isin(re_tech)]['current_MWh'].sum()
    start_re_pct = start_re / lcoe_df['current_MWh'].sum()

    # rps_min_increase = df['rec_req'].sum() / df['demand'].sum()
    rps_min_increase = df['rps_marginal_req'].sum()
    minimum_desired_pct = start_re_pct + rps_min_increase

    return int(minimum_desired_pct * 100)
    
@app.callback(
    Output("goal_text","children"),
    [Input('intermediate_dict_scenario','data')]
)
def goal_text_maker(json):
    
    input_dict = json_func.loads(json)

    rps_min_increase = input_dict['rps_min_increase'] *100


    out = f"""
    While the RPS will require your utility to increase your renewable energy supply by {round(rps_min_increase,1)},
    it may be cost-effective to go beyond this amount. Additional renewable procurement can provide price stability and may increase customer satisfaction with your utility. 
    Additional renewables also allow you to bank RECs, which can be sold through the WESM as a secondary revenue stream, or held for future compliance years.

    Using the slider below, you can change the desired percentage of renewables for your utility. This has been preset at the minimum RPS requirement. 
    Below the slider, you can also select the mix of renewables that will be installed. As you change the desired renewable percentage and the mix of new renewables, the price per kWh will is updated.
    These prices are derived from the LCOE values specified in the 'Energy Mix and Cost Input'. 
   """.replace('  ', '')

    return out

if __name__ == "__main__":
    app.run_server(debug=False)