import dash
import dash_table
import dash_daq as daq
import dash_core_components as dcc
import dash_html_components as html

# --- Module Imports ---
import resources
import layout

# --- Layout ---
html_obj = html.Div([

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
                ), 
            ],
            className='twelve columns',
            ),

            html.Div([
                dcc.Markdown("""
                    The Philippines RPS is a legislative mandate requiring utilities to increase their use of renewable resources including
                    *“biomass, waste to energy technology, wind, solar, run-of-river, impounding hydropower sources that meet internationally accepted standards, ocean, hybrid systems, 
                    geothermal and other RE technologies that may be later identified by the DOE."* 
                    
                    The RPS requires all utilities to increase their utilization of renewable energy by 1% of their total energy sales (kWh) each year beginning in 2020, although this percentage can be increased in the future by the National Renewable Energy Board.
                    For many utilities, the lower costs and higher customer satisfaction with renewables is encouraging adoption above what the RPS requires. This calculator is designed to help utilities understand when they will need to procure additional renewable capacity, and how procuring additional renewables could result in cost savings.

                    Click through the tabs below to input data for your utility. More details about each input can be found by hovering your mouse over the circled question-mark symbols.
                    """.replace('  ', ''),
                    className='twelve columns',
                ),
            ]),
        ],
        className='twelve columns'
        ),

#Selectors
        html.Div([

            dcc.Tabs(id='utility_inputs', value='acronym', parent_className='custom-tabs', className='custom-tabs-container',
                children=[

                dcc.Tab(label='Automatic Utility Data Lookup', className='custom-tab', selected_className='custom-tab--selected', value='acronym',
                    children=[
                            html.Div([
                                html.Div([
                                    html.P("Enter Utility Acronym:",style={'display':'inline-block'}),

                                    html.Div([
                                        ' \u003f\u20dd',
                                        html.Span('When a utility name (acronym) is selected, data such as annual energy sales, demand growth, and FiT allocation are automatically loaded from a 2017 DOE Database. Users can overwrite this data in the Manual Utility Data Input tab.'
                                        , className="tooltiptext")], className="tooltip", style={'padding-left':5}),
                                    dcc.Dropdown(
                                        id='utility_name',
                                        options=[{'label':i, 'value':i} for i in list(resources.utility_dict.keys())],
                                        multi=False,
                                        value='MERALCO',
                                    )
                                ],
                                style={'margin-top':30, 'margin-bottom':30})
                            ])
                        ]),
                
                dcc.Tab(label='RPS Policy Details', className='custom-tab', selected_className='custom-tab--selected', value='rps-details',
                        children=[
                            html.Div([
                                html.Div([
                                    html.P("End Year of RPS:", style={'display':'inline-block'}),

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
                                ),

                                html.Div([
                                    html.P("2020-23 RPS Increment (%):",
                                    style={'display':'inline-block'}),

                                    html.Div([
                                        '\u003f\u20dd',
                                        html.Span('The annual marginal increase of the RPS requirement, the current law requires 1%, however this could be increased in the future.'
                                        , className="tooltiptext")], className="tooltip", style={'padding-left':5}),        
                                    dcc.Input(id='annual_rps_inc_2020',value=1,type='number',step=0.25,style={'width':'100%'}, min=0.25)
                                        ],
                                    className='four columns',
                                ),

                                html.Div([
                                    html.P("2023 - End RPS Increment (%):",
                                    style={'display':'inline-block'}),

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

                                    html.Div([
                                        '\u003f\u20dd',
                                        html.Span('For each generation source, please enter the Levelized Cost of Energy (LCOE) and percent of utility energy mix supplied by each generation source. For more information on what LCOE is, please refer to Part 3. The percent of utility energy mix represents generation supplied by each resource type divided by the total amount of supplied generation, this column must sum to 100%. Default LCOE data is from IRENA regional averages for South East Asia. Default values for percent of utility energy mix are derived from the average energy-mix for all utilities in the Philippines.'
                                        , className="tooltiptext")], className="tooltip", style={'padding-left':5}),

                                    dash_table.DataTable(
                                        id='energy_mix_table',
                                        columns=[{'name':i, 'id':i} for i in resources.energy_mix_df.columns],
                                        data=resources.energy_mix_df.to_dict('records'),
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
                                        dcc.Markdown(id="energy_mix_error_text", children=["init"],
                                        ),
                                ],
                                className='six columns',
                                style={'margin-bottom':0, 'verticalAlign':'top'}),

                                html.Div([
                                    html.P("Add Any Planned Renewable Procurement:",
                                    style={'display':'inline-block'}),

                                    html.Div([
                                        '\u003f\u20dd',
                                        html.Span('Use this sheet to add in any planned renewable procurement that will count towards the RPS. For instance, if your utility has signed a solar PPA beginning in 2020, select Utility-Scale Solar as the generation source, and then specify the anticipated annual generation and year that the project will begin producing RECs. Use the Add Row button for additional entries'
                                        , className="tooltiptext")], className="tooltip", style={'padding-left':5}),

                                    dash_table.DataTable(
                                    id='future_procurement_table',
                                    columns=[
                                        {'id':'Generation Source', 'name':'Generation Source', 'presentation':'dropdown'},
                                        {'id':'Capacity (MW)', 'name':'Capacity (MW)'},
                                        {'id':'Online Year', 'name':'Online Year'},
                                    ],
                                    editable=True,
                                    row_deletable=True,
                                    dropdown={
                                        'Generation Source':{
                                            'options':[{'label':i, 'value':i} for i in resources.re_tech]
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
                                    data=resources.new_build_df.to_dict('records'),
                                        ),
                                    
                                    html.Div([
                                    html.P(' '),
                                    html.Button('Add Row', id='editing-rows-button', n_clicks=0),
                                    ], style={'margin-left':'35%'}),
                                    html.P('*Please note: existing RPS compliant plants and PPAs with the DUs are not included in the Automatic Utility Lookup. Please add them manually above.')
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

                                    html.Div([
                                        '\u003f\u20dd',
                                        html.Span('Capacity factor is a percentage value that represents the actual generation potential of a resource type. It is calculated by dividing the total anticipated generation from a resource for a time period, over the total amount that would be generated if the resource is available at full nameplate capacity for the same time period. Resources such as the Renewable Energy Data Explorer and the System Advisor Model (SAM) can help you determine renewable capacity factors for your area.'
                                        , className="tooltiptext")], className="tooltip", style={'padding-left':5}),
                                ],
                                className='twelve columns',
                                style={'margin-top':30,'verticalAlign':'top'}),

                                html.Div([
                                    html.Div([
                                        html.P("Utility-Scale Solar Capacity Factor:",
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
                                    html.P("Annual Energy Sales (MWh):",style={'display':'inline-block'}),

                                    html.Div([
                                        ' \u003f\u20dd',
                                        html.Span('Annual energy sales are equal to total electricity sales, this does not include line losses.'
                                        , className="tooltiptext")], className="tooltip", style={'padding-left':5}),
                                    dcc.Input(id="demand", value=418355, type="number",style={'width':'100%'}) #this works RE: 
                                        ],
                                    className = 'four columns',
                                ),

                                html.Div([
                                    html.P("Annual Fit Percent (%):",style={'display':'inline-block'}),

                                    html.Div([
                                        '\u003f\u20dd',
                                        html.Span('Under the 2008 RE Law, RECs from customer-subsidized feed-in-tariff projects are allocated to each utility proportional to their total energy sales. This value is expressed as a percent, sometimes called K0'
                                        , className="tooltiptext")], className="tooltip", style={'padding-left':5}),
                                    dcc.Input(id="fit_pct", value=3.34, type="number",style={'width':'100%'})
                                        ],
                                    className = 'four columns',
                                ),

                                html.Div([
                                    html.P("Annual Demand Growth (%):",
                                    style={'display':'inline-block'}),

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
            className='twelve columns'),

        html.Div([
            dcc.Markdown("""
                    While your utility may already be using renewable energy, the RPS requires the sourcing of *new* renewable generation built since the implementation of the [2008 RE Law](https://www.doe.gov.ph/sites/default/files/pdf/issuances/dc2009-05-0008.pdf).
                    The level of renewable energy that must be procured is a percentage of your total energy sales––see the yellow and blue bars in the chart below.
                    While the RPS requirement is mandatory for utilities to meet, many often desire going beyond this requirement in order to convey to their customers that they are supporting renewable energy, or to achieve cost savings provided by renewables.

                    In order to demonstrate that your utility is complying with the RPS, you will be required to procure and retire Renewable Energy Certificates (RECs). RECs are bankable credits
                    that convey the environmental attributes for 1 MWh of renewable generation. Owning and retiring a REC allows an entity to make a specific legal claim of renewable energy consumption, 
                    for instance, when a utility retires RECs they can claim that a percentage of the energy-mix they are providing their customers is renewable. Other entities, such as corporations, value RECs as a means to demonstrate voluntary renewable energy purchases.
                    RECs will be entered into an online tracking system––the Renewable Energy Market (REM)––which will be operated through the existing Wholesale Electricity Spot Market (WESM).
                    The REM will allow trading of RECs between third-parties and utilities, although prices are expected to potentially be volatile. For more information on RECs, [please consult this technical report](https://www.nrel.gov/docs/fy19osti/72204.pdf). 

                    The RPS interacts with other components of the 2008 RE Law such as the Feed-in-Tariff (FiT) program, which procures blocks of renewable capacity at government-approved rates.
                    Since 2018, all utilities in the Philippines are receiving RECs from FiT projects in proportion to their market share of total electricity sales in the country. As of January 2019,
                    the number of RECs each utility receives is equal to 3.1% of their total energy sales. Because the RPS treats 2018 as 'year 0' of the RPS, and 2019 as a 'transition year', there is no RPS requirement
                    during these years. However, utilities will receive RECs from the FiT or eligible new renewable projects during this time. Because RECs can be banked for future years,
                    most utilities will enter year 1 (2020) of the RPS with an existing REC surplus that will deplete over subsequent years as the RPS requirement increases.
                    
                    The table below displays a projection of RPS requirements for your utility based on your data inputs. Additionally, the figure displays data such as
                    the end-of-year REC balance in green (if one exists), or the annual REC shortfall in red. **If there is a REC shortfall in any year, this indicates that additional renewable capacity will need to be procured in advance of a REC shortfall,
                    or REC purchases will need to be made on the RE market to ensure the utility is in compliance.** 
            """.replace('  ',''))],
            className='twelve columns',
            ),
        ],
        className='row',
    ),
        
html.Div([
    html.Div([
        dcc.Graph(id="demand_and_REC_graph")
    ], 
    className = 'twelve columns'),

    html.Div([
        dash_table.DataTable(
            id='demand_and_REC_table',
            columns=[{'name':i, 'id':i} for i in resources.dummy_df_display.columns],
            data=resources.dummy_df_display.to_dict('records'),
            export_format = 'csv',
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
    className='twelve columns'),
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
    className='twelve columns'),

    html.Div([
        html.Div([
            dcc.Markdown(id="capacity_text", children=["init"])
        ],
        className = 'twelve columns'),

        html.Div([
            html.Div([
                dcc.Graph(id="capacity_incremental_graph")],
            className = 'six columns'),
            
            html.Div([
                dcc.Graph(id="capacity_cum_graph")],
            className = 'six columns'),
        ])
    ],
    className='rows'),
]),

html.Div([

    html.Div([
        dcc.Markdown("""
                The table below displays a projection of **cumulative capacity requirements** for your utility by year and technology.
                This table is identical to the Cumulative Capacity Table above this to the right. This data can be interpreted as the cumulative amount of RE capacity to be procured
                by the utility by a given year. Keep in mind that RECs can be banked for future years, so procuring capacity earlier than required could reduce your overall requirement.
                The export button above allows you to download this table.
        """.replace('  ',''))],
        className='twelve columns',
        style={'margin-top':30}
        ),

    html.Div([
        dash_table.DataTable(
            id='capacity_cum_table',
            columns=[{'name':i, 'id':i} for i in resources.dummy_requirements_df.columns],
            data=resources.dummy_requirements_df.to_dict('records'),
            export_format = 'csv',
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
    className='twelve columns',
    style={'margin-top':30}),
    ],
className = 'row',
),

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
    className='twelve columns'),

    html.Div([
        dcc.Markdown("""
    Not only will additional renewables help you meet your RPS requirements while providing customers with cleaner electricity, but renewables
    may be more cost-effective than fossil-fuel generators. The International Renewable Energy Agency (IRENA) tracks the annual benchmark Levelized Cost of Energy (LCOE)
    for various renewable technologies. An LCOE comprises the all-in cost of energy generation on a per kWh basis, for renewables this accounts for differences in equipment and installation costs, 
    resource capacity factor, and operations & maintenance expenses. For fossil-fuel generators, the LCOE also includes the cost of fuel such as coal or natural gas,
    which can be quite expensive in the Philippines. 

    IRENA's 2017 data suggests that the global LCOE for renewables ranges between $0.05 (Php 2.5) per kWh for hydro to $0.10 (Php 5) per kWh for utility-scale solar installations.
    The graphs below display the median price, along with global prices between the fifth and ninety-fifth percentiles. Note that some technologies, like geothermal or hydro might only be suitable for larger capacity installations,
    while solar, biomass, and wind are more likely to be scalable to your custom capacity requirements. 

    The IRENA LCOE data informs us that the price of renewables has declined dramatically in recent years. Since 2010, the average LCOE for solar has declined 72% from $0.36 (Php 18) to $0.10 (Php 5) per kWh in 2017.
    Over the same time period, wind's LCOE has declined 25% from $0.08 (Php 4) to $0.06 (Php 3) per kWh, while other technologies like geothermal, biomass, and hydro have remained constant or seen slight increases in cost. 
    Renewables may be less expensive on a per kWh basis than coal or natural gas and also are not susceptible to fluctuations in fuel prices. 

    Finally, consider that some REC procurement can be done through utility programs such as solar net-metering and the new GEOP, which allow customers to build their own renewables while providing the utility with RECs. 
    Under the current GEOP design, a customer would pay for the entire system cost, while the utility would receive all RECs.

    """.replace('  ', ''))
    ],
    className='twelve columns'),
    
    html.Div([
        html.Div([
            dcc.Markdown(id="economic_text", children=["init"])
        ],
        className = 'reference_box'),
    ],
    className='twelve columns',
    ),

    html.Div([
        html.Div([
            dcc.Graph(id='lcoe_graph')
        ],
        className = 'twelve columns'),
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
    className='twelve columns'),

    html.Div([
            dcc.Markdown(id='goal_text')
        ],
        style={'margin-bottom':20},
        className = 'twelve columns'),

    html.Div([
        
        html.Div([
            html.Div([
                dcc.Graph(id='doughnut_graph')
            ],
            className = 'eight columns',
            ),

            html.Div([
                html.Div([
                    html.P("Desired Renewables Percent:")],
                    style={'margin-bottom':40, 'display':'inline-block'}
                ),

                html.Div([
                    ' \u003f\u20dd',
                    html.Span('This value can reflect your RPS goal, incremental RPS targets, or any other aspirational RE percentages. Note: Any fossil retirements needed to meet this percentage will be distributed proportionately amongst available fossil capacity.'
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
                    # size={'width':'100%'} #resizes to window
                    )
                    ],
                className = 'four columns'),
            
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
        className='twelve columns'),

        html.Div([
            html.Div([
                dcc.Markdown(id='savings_text')
            ],
            className = 'reference_box'),
        ],
        className='twelve columns'),
    ],
    className='row',
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
        className='twelve columns'),
    
    html.Div([
        dcc.Markdown("""
        So far you have learned what your REC obligations are under the RPS, you have explored how much capacity is needed for different renewable technologies to meet your utility's obligations, 
        and you have planned for what years you will need to procure renewables by.

        The next step is to conduct a detailed feasibility study examining the techno-economic potential of specific renewable energy projects. To begin this process,
        we recommend the following resources:
        """)
    ],
    className='twelve columns'),
    
    html.Div([
        html.Div([
            html.H6('Renewable Energy Data Explorer')
        ],
        className='twelve columns',
        ),

        html.Div([
            dcc.Markdown("""
            The RE Data Explorer is a user-friendly geospatial analysis tool for analyzing renewable energy potential and informing decisions. 
            It can be used to visualize capacity factor data for solar, wind, and geothermal resources. 
            Assessing resource technical potential should be one of the first steps when conducting a feasibility study. 
            Examples of how to integrate the RE Data Explorer into your decision support planning process are outlined in [this technical report](https://www.nrel.gov/docs/fy18osti/68913.pdf)
            and in [this fact-sheet](https://www.nrel.gov/docs/fy18osti/68899.pdf).
            """.replace('  ', ''))
        ],
        className='eight columns'),

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
        className='eight columns'),

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
                ###### About the Clean Energy Investment Accelerator (CEIA):
                The CEIA is an innovative public-private partnership jointly led by Allotrope Partners, World Resources Institute,
                and the U.S. National Renewable Energy Laboratory. Through targeted engagement in key countries,
                the CEIA unlocks clean energy investment across commercial and industrial sectors.
                The CEIA helps companies meet their clean energy targets and supports countries to meet their climate and development goals.
                This includes implementation of Nationally Determined Contribution investment plans, long-term decarbonization strategies,
                and broader efforts to meet growing energy needs and support strong economic growth.

                Please contact the CEIA's in-country lead––Marlon Apanada––with any questions at <amj@allotropepartners.com>.
                """.replace('  ', '')),
        ],
        className='twelve columns'),
    ],
    className = 'reference_box'),

    html.Div([
        html.Div([
            dcc.Markdown(
                """
                ###### References:

                *Additional CEIA program information:*
                
                [CEIA Website](https://www.cleapenergyinvest.org/)
            
                [CEIA. "Webinar on Philippine RE at the Crossroads." Presented January 2019.](https://www.youtube.com/watch?v=gd744nnvfWk)


                *Additional tools to help conduct renewable feasibility studies:*

                [System Advisor Model](https://sam.nrel.gov/)

                [Renewable Energy Data Explorer](https://maps.nrel.gov/rede-southeast-asia/)

                [PVWatts](https://pvwatts.nrel.gov/)


                *More information on the RPS can be found in the following Department of Energy Circulars:*

                [Department of Energy. "Prescribing the Share of Renewable Energy Resources in the Country's Installed Capacity..." DC2015-07-0014. Published 2015.](https://www.doe.gov.ph/sites/default/files/pdf/issuances/dc_2015-07-0014.pdf)
                
                [Department of Energy. "Rules and Regulations Implementing Republic Act No.9513". DC2009-05-0008. Published 2009.](https://www.doe.gov.ph/sites/default/files/pdf/issuances/dc2009-05-0008.pdf)
            

                *LCOE data from:*

                [International Renewable Energy Agency (IRENA). "Renewable Power Generation Costs in 2017." Published 2018.](https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2018/Jan/IRENA_2017_Power_Costs_2018.pdf)
            

                *Additional Price Data from:*

                Biomass Renewable Energy Alliance (BREA). "Biomass: Fueling the Economy of the Philippines". Presented March 2019.
                
                """.replace('  ', '')
        )],
        className = 'twelve columns'),
    ],
    className = 'reference_box'),

    # --- CEIA Info ---
    html.Div([

        html.Div([
            html.P("The CEIA is jointly implemented by WRI, NREL, and Allotrope Partners",
                   style={'font-size': '125%',
                          'font-style': 'italic', 'text-align': 'center'}
            )
        ],
        className='four columns'),

        html.Div([
            
            html.Img(
                src='assets/WRI_logo_4c.png',
                className='two columns',
                style={
                    'width':'30%',
                    'height':'auto',
                    'float':'center',
                    'position':'relative',
                }
            ),

            html.Img(
                src='assets/Allotrope_Logo_hi-res.png',
                className='two columns',
                style={
                    'width': '30%',
                    'height': 'auto',
                    'float': 'center',
                    'position': 'relative',     
                }
            ),

            html.Img(
                src='assets/NREL logo w tagline.png',
                className='two columns',
                style={
                    'width':'30%',
                    'height':'auto',
                    'float':'center',
                    'position':'relative',
                }
            ),
        ],
        className='five columns'),
    ],
    className='ten columns offset-by-two',
    style={'margin-top':25}
    ),

    # --- Funder info ---
    html.Div([

        html.Div([
            html.P("The CEIA is supported by a range of public, private, and philanthropic partners",
                   style={'font-size': '125%', 'font-style': 'italic', 'text-align':'center'}
                   )
        ],
            className='four columns'),

        html.Div([

            html.Img(
                src='assets/United States govt logo.png',
                className='two columns',
                style={
                    'width': '20%',
                    'height': 'auto',
                    'float': 'center',
                    'position': 'relative',
                }
            ),

            html.Img(
                src='assets/BMUB logo.png',
                className='two columns',
                style={
                    'width': '40%',
                    'height': 'auto',
                    'float': 'center',
                    'position': 'relative',
                }
            ),

            html.Img(
                src='assets/P4G large_logo.png',
                className='two columns',
                style={
                    'width': '30%',
                    'height': 'auto',
                    'float': 'center',
                    'position': 'relative',
                }
            ),
        ],
            className='five columns'),
    ],
        className='ten columns offset-by-two',
        style={'margin-top': 25, 'text-align':'center'}
    ),


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

dcc.Store(id='intermediate_df'), #rps policy scenario, requirements, demand, rec balance
dcc.Store(id='intermediate_df_capacity'),
dcc.Store(id='intermediate_dict_scenario'),
dcc.Store(id='intermediate_lcoe_df'),
dcc.Store(id='future_procurement_df')

], 
className='ten columns offset-by-one'
)
