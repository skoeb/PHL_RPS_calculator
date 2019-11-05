import dash
import dash_table
import dash_daq as daq
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Input, State
import plotly.graph_objs as go
import pandas as pd
import plotly.tools as tls
import plotly.io as pio
import json as json_func

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~ Set up server ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# --- Theming ---
pio.templates.default = 'seaborn'

# --- Module Imports ---
import resources
import layout

# --- Initialize App ---
app = dash.Dash(__name__)

# --- Set Name and Layout ---
app.title = 'CEIA RPS Calculator'
app.layout = layout.html_obj

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~ Non-Callbacks ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# --- Helper Functions ---
def add_commas(df):
    """Add commas to thousands"""
    for c in df.columns:
        df[c] = df[c].apply(lambda x : "{:,}".format(int(x)))
    return df

# --- General Functions ---
def rps_df_maker(demand, demand_growth, future_procurement, fit_pct,
                 annual_rps_inc_2020, annual_rps_inc_2023, 
                 end_year):
    """
    Funciton to calculate RPS obligations in the Philippines.

    Input
    -----
        -demand (float): 2018 Demand in MWh
        -demand_growth (float): percent demand growth annual (i.e. 5 year average)
        -future_procurement (df): df of future procurement, with MWh specified in a 'generation' column. Assumed to be RE that is creating RECs.
        -fit_pct (float): pct of FiT allocation (see Hot Topic Paper for primer on FiT in PHL)
        -annual_rps_inc_2020 (float): pct RPS requirement in 2020 (set at 1%)
        -annual_rps_inc_2023 (float): pct RPS requirement between 2023 and 2030
        -end_year (int): last year of RPS.  
    """
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

    # --- Calculate FIT MWs (static, only based on first year) --- 
    df['fit_MWh'] = fit_pct * demand / 100

    future_procurement = future_procurement.groupby(['Online Year'], as_index=False)['generation'].sum()
    future_procurement = future_procurement.rename({'Online Year':'year'}, axis='columns')
    future_procurement = future_procurement.set_index('year')
    dummy_years = df.copy() #for forward fill join
    dummy_years = dummy_years.drop(dummy_years.columns, axis='columns')
    future_procurement = dummy_years.merge(future_procurement, left_index=True, right_index=True, how='outer').sort_index()
    future_procurement = future_procurement.fillna(0)
    future_procurement['generation'] = future_procurement['generation'].cumsum()

    df['future_procurement'] = future_procurement['generation']

    demand_for_calc = df['demand'].copy()
    demand_for_calc.index = [i + 1 for i in demand_for_calc.index]
    demand_for_calc.loc[2018] = 0
    demand_for_calc.loc[2019] = 0
    demand_for_calc.loc[2020] = df['demand'][2018]
    demand_for_calc = demand_for_calc.sort_index()
    df['demand_for_calc'] = demand_for_calc

    # --- clip RPS requirement to 100% ---
    df['rps_req'] = df['rps_req'].clip(upper=1)

    df['rec_req'] = df['rps_req'] * df['demand_for_calc']
    fit_requirement_MW = df['fit_MWh'].copy()
    fit_requirement_MW[2018] = 0
    fit_requirement_MW[2019] = 0
    df['rec_req'] = df['rec_req'] + fit_requirement_MW

    df['rec_created'] = df['fit_MWh'] + df['future_procurement']

    df['rec_change'] = df['rec_created'] - df['rec_req']

    # --- Calculate cumulative production and sales --- 
    df['rec_cum_production'] = df['rec_created'].cumsum()
    df['rec_cum_withdraws'] = df['rec_req'].cumsum()

    # --- Annual expirations based on three-year old surplus --- 
    df['rec_expired'] = df['rec_created'].shift(3, fill_value=0) - df['rec_req'].shift(3, fill_value=0)
    df['rec_expired'] = df['rec_expired'].clip(0) #no negative surpluses
    df.loc[df.index < 2023, 'rec_expired'] = 0 #Assuming that RECs from transition period will be spent
    df['rec_cum_expired'] = df['rec_expired'].cumsum() #cumulative expirations

    # --- Total inventory is difference of cumulatives ---
    df['end_rec_balance'] = df['rec_cum_production'] - df['rec_cum_withdraws'] - df['rec_cum_expired']

    # --- clip rec_balance --- 
    df['end_rec_balance'] = df['end_rec_balance'].clip(0)
    df['begin_rec_balance'] = df['end_rec_balance'].shift(1).fillna(0)

    # --- Calculate Annual REC Need (purchase requirements)---
    df['rec_shortfall'] = (df['begin_rec_balance'] + df['rec_created'] - df['rec_req'] - df['rec_expired']) * -1
    df['rec_shortfall'] = df['rec_shortfall'].clip(0)

    return df

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~ Data Input ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@app.callback(
    Output("demand","value"),
    [Input("utility_name","value")]
)
def demand_mw_updater(utility):
    """Update utility demand."""
    output = resources.utility_dict[utility]['sales']
    return output

@app.callback(
    Output("demand_growth","value"),
    [Input("utility_name","value")]
)
def growth_mw_updater(utility):
    """Update utility growth %."""
    output = resources.utility_dict[utility]['growth_floor'] * 100 #scaled to 100
    return output

@app.callback(
    Output("future_procurement_df", "data"),
    [   
        Input("future_procurement_table","data"),
        Input("future_procurement_table","columns"),
        Input("solar_cf", "value"),
        Input("dpv_cf", "value"),
        Input("wind_cf", "value"),
        Input("geothermal_cf", "value"),
        Input("biomass_cf", "value"),
        Input("hydro_cf", "value"),
    ])
def future_procurement_generation(future_procurement_rows, future_procurement_columns,
                                    solar_cf, dpv_cf, wind_cf, geothermal_cf, biomass_cf, hydro_cf):
    """Update df of future RE procurement."""
    future_procurement = pd.DataFrame(future_procurement_rows, columns=[c['name'] for c in future_procurement_columns])
    future_procurement = future_procurement.loc[future_procurement['Generation Source'].isin(resources.re_tech)]
    future_procurement = future_procurement.groupby(['Generation Source', 'Online Year'], as_index=False)['Capacity (MW)'].sum()
    
    cols = ['Online Year', 'Capacity (MW)']
    future_procurement[cols] = future_procurement[cols].apply(pd.to_numeric, errors='coerce')

    cf_dict = {'Utility-Scale Solar': solar_cf,
               'Net-Metering': dpv_cf,
               'GEOP': dpv_cf,
               'Wind': wind_cf,
               'Geothermal': geothermal_cf,
               'Biomass' : biomass_cf,
               'Hydro' : hydro_cf
               }
               
    future_procurement['cf'] = future_procurement['Generation Source'].map(cf_dict)
    future_procurement['cf'] = future_procurement['cf'] / 100
    future_procurement['generation'] = future_procurement['Capacity (MW)'] * future_procurement['cf'] * 8760
    return future_procurement.to_json()


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

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~ Data Processing ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@app.callback(
    Output("intermediate_df", "data"),
    [
        Input("demand", "value"),
        Input("demand_growth", "value"),
        Input("future_procurement_df", "data"),
        Input("fit_pct", "value"),
        Input("annual_rps_inc_2020", "value"),
        Input("annual_rps_inc_2023", "value"),
        Input("end_year", "value"),
    ])
def df_initializer(demand, demand_growth, json,
                    fit_pct, annual_rps_inc_2020, annual_rps_inc_2023, end_year):
    """Initialize df with RPS req info."""
    future_procurement = pd.read_json(json)

    demand_growth = float(demand_growth) / 100
    annual_rps_inc_2020 = float(annual_rps_inc_2020) / 100
    annual_rps_inc_2023 = float(annual_rps_inc_2023) / 100
    end_year = int(end_year) + 1

    df = rps_df_maker(demand=demand, demand_growth=demand_growth, future_procurement=future_procurement, fit_pct=fit_pct,
                    annual_rps_inc_2020=annual_rps_inc_2020, annual_rps_inc_2023=annual_rps_inc_2023,
                    end_year=end_year)
    df = round(df, 3)
    return df.to_json()

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
    """Update capacity needs by multiplying against a capacity factor."""
    df = pd.read_json(json)
    def new_capacity_calc(row, capacity_factor):
        mwh_Need = abs(row['rec_incremental_req'])
        mw_Need = (abs(mwh_Need) / 8760) / (capacity_factor/100)
        return mw_Need

    df['rec_incremental_req'] = df['rec_shortfall'].diff(1)
    df['rec_incremental_req'] = df['rec_incremental_req'].cumsum()

    df['Utility-Scale Solar_Need'] = df.apply(new_capacity_calc, args=([solar_cf]), axis = 1)
    df['Distributed PV_Need'] = df.apply(new_capacity_calc, args=([dpv_cf]), axis = 1)
    df['Geothermal_Need'] = df.apply(new_capacity_calc, args=([geothermal_cf]), axis = 1)
    df['Hydro_Need'] = df.apply(new_capacity_calc, args=([hydro_cf]), axis = 1)
    df['Wind_Need'] = df.apply(new_capacity_calc, args=([wind_cf]), axis = 1)
    df['Biomass_Need'] = df.apply(new_capacity_calc, args=([biomass_cf]), axis = 1)

    df = df[['Utility-Scale Solar_Need','Distributed PV_Need', 'Geothermal_Need','Wind_Need','Biomass_Need','Hydro_Need','end_rec_balance','rec_incremental_req', 'rec_shortfall', 'rec_req', 'rec_change']]
    df = round(df, 2)

    return df.to_json()


@app.callback(
    Output('intermediate_dict_scenario','data'),
    [
    Input('intermediate_df','data'),
    Input('future_procurement_df','data'),
    Input('energy_mix_table','data'),
    Input('energy_mix_table', 'columns'),
    Input('desired_pct','value'),
    Input('scenario_radio','value'),
    ]
)
def scenario_dict_maker(json1, json2, rows, columns, desired_pct, scenario_tag): #remember to define optimization 
    """Calc final year RE pct, costs, etc., package as a json."""
    df = pd.read_json(json1)
    future_procurement = pd.read_json(json2)

    starting_demand = int(list(df['demand'])[0])

    lcoe_df = pd.DataFrame(rows, columns=[c['name'] for c in columns])
    cols = lcoe_df.columns.drop(['Generation Source'])
    lcoe_df[cols] = lcoe_df[cols].apply(pd.to_numeric, errors='coerce') #convert all columns to numeric

    desired_pct = desired_pct/100

    start_year = list(df.index)[0]
    end_year = list(df.index)[-1]
    start_demand = list(df.demand)[0]
    end_demand = list(df.demand)[-1]
    start_recs = list(df.rec_change)[0] #RECs currently being created

    lcoe_df['current_MWh'] = (lcoe_df['Percent of Utility Energy Mix'] / 100) * starting_demand

    lcoe_df['start_price'] = lcoe_df['Levelized Cost of Energy (₱ / kWh)'] * lcoe_df['current_MWh'] * 1000
    
    lcoe_df['fuel_emissions'] = lcoe_df['Generation Source'].map(resources.emissions_dict)
    lcoe_df['emissions'] = lcoe_df['fuel_emissions'] * lcoe_df['current_MWh']

    # --- Merge on planned procurement ---
    future_procurement = future_procurement.groupby('Generation Source', as_index=False)['generation'].sum()
    lcoe_df = lcoe_df.merge(future_procurement, on=['Generation Source'], how = 'left')
    lcoe_df['generation'] = lcoe_df['generation'].fillna(0)
    lcoe_df = lcoe_df.rename({'generation':'planned_generation'}, axis='columns')

    start_re = lcoe_df.loc[lcoe_df['Generation Source'].isin(resources.re_tech)]['current_MWh'].sum()
    start_re_pct = round(start_re / start_demand,2)
    start_expense = round(lcoe_df['start_price'].sum(),0)
    start_fossil = lcoe_df.loc[lcoe_df['Generation Source'].isin(resources.fossil_tech)]['current_MWh'].sum()

    planned_re = lcoe_df['planned_generation'].sum()
    new_re_Need = (end_demand  * desired_pct) - start_re - planned_re #include losses, because this is interms of generation pct, not RECS
    new_re_Need = max(new_re_Need, 0)
    fossil_Need = end_demand - new_re_Need - start_re - planned_re
    scenario = resources.scenario_pct_dict[scenario_tag]

    curr_total_fossil_gen = lcoe_df.loc[lcoe_df['Generation Source'].isin(resources.fossil_tech), 'current_MWh'].sum() #df of fossil fuels
    fossil_discrepancy = fossil_Need - curr_total_fossil_gen #if negative, indicates the amount that can be retired, if positive, the amount of new fossil gen needed

    lcoe_df['future_generation'] = 0
    for f in resources.re_tech:
        current_gen_f = lcoe_df.loc[lcoe_df['Generation Source'] == f, 'current_MWh'][0:1].item()
        if f in scenario.keys():
            lcoe_df.loc[lcoe_df['Generation Source'] == f, 'future_generation'] = (scenario[f] * new_re_Need) + current_gen_f
        else:
            lcoe_df.loc[lcoe_df['Generation Source'] == f, 'future_generation'] = current_gen_f


    for f in resources.fossil_tech:
        current_pct_f = lcoe_df.loc[lcoe_df['Generation Source'] == f, 'current_MWh'][0:1].item() / start_fossil
        lcoe_df.loc[lcoe_df['Generation Source'] == f, 'future_generation'] = fossil_Need * current_pct_f

    # --- Add Planned RE Generation from input ---
    lcoe_df['future_generation'] += lcoe_df['planned_generation']

    lcoe_df['future_price'] = lcoe_df['Levelized Cost of Energy (₱ / kWh)'] * lcoe_df['future_generation'] * 1000
    end_re = lcoe_df.loc[lcoe_df['Generation Source'].isin(resources.re_tech)]['future_generation'].sum()
    end_recs = end_re - (start_re - start_recs)
    end_re_pct = end_re / lcoe_df['future_generation'].sum()


    output_dict = dict()
    output_dict['start_year'] = int(start_year)
    output_dict['start_demand'] = int(start_demand)
    output_dict['start_re'] = int(start_re)
    output_dict['start_recs'] = int(start_recs)
    output_dict['start_re_pct'] = float(start_re_pct)
    output_dict['start_expense'] = int(start_expense)
    output_dict['start_generation_list'] = [int(i) for i in list(lcoe_df['current_MWh'])]
    output_dict['end_year'] = int(end_year)
    output_dict['end_demand'] = int(end_demand)
    output_dict['end_re'] = int(end_re)
    output_dict['end_recs'] = float(end_recs)
    output_dict['end_re_pct'] = float(end_re_pct)
    output_dict['end_expense'] = int(lcoe_df['future_price'].sum())
    output_dict['end_generation_list'] = [int(i) for i in list(lcoe_df['future_generation'])]
    output_dict['techs'] = list(lcoe_df['Generation Source'])
    output_dict['rps_min_increase'] = df['rps_marginal_req'].sum()
    output_dict['scenario_lcoe_df'] = lcoe_df.to_json()

    return json_func.dumps(output_dict)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~ Plotting ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ------ SECTION 1 ------
@app.callback(
    Output('demand_and_REC_graph', 'figure'),
    [Input('intermediate_df', 'data')]
)
def html_REC_balance_graph(json):
    """Plot REC requirements and REC balance (section 1)"""
    df = pd.read_json(json)

    df_bar = df[['fit_MWh','future_procurement', 'begin_rec_balance', 'rec_shortfall']]
    df_bar.columns = ['RECs from FiT','RECs from Planned Procurement','Beginning REC Balance', 'Annual REC Shortfall']

    color_count = 0
    traces = []

    for c in df_bar.columns:
        color_ = list(resources.color_dict.values())[color_count]
        trace = go.Bar(
                x = list(df_bar.index),
                y = list(df_bar[c]),
                name = c,
                marker = dict(color=color_))
        traces.append(trace)
        color_count+=1
    
    color_ = list(resources.color_dict.values())[color_count]
    line_trace = go.Scatter(
                    x = list(df_bar.index),
                    y = list(df['rec_req']),
                    name = 'REC Requirement',
                    line=dict(color=color_, width=5),
                    marker = dict(color=color_))

    traces.append(line_trace)
    
    layout = dict(
        height=450,
        title='RPS Requirements'
        )

    fig = go.Figure(data=traces, layout=layout)
    
    fig['layout'].update(barmode='stack')
    fig['layout'].update(height=400, xaxis=dict(tickmode='linear', dtick=1))
    fig['layout'].update(legend=dict(orientation="h"))
    fig['layout']['margin'].update(l=20,r=20,b=20,t=40,pad=0)
    fig['layout']['yaxis'].update(title='RECs')
    fig['layout']['title'].update(text='RPS Requirements and REC Balance by Year', x=0.5)

    return fig


    # ----- SECTION 2 ------
@app.callback(
    Output('capacity_incremental_graph', 'figure'),
    [Input('intermediate_df_capacity', 'data')]
)
def capacity_requirement_simple_graph(json):
    """Incremental capacity requirement."""
    df = pd.read_json(json)
    
    traces = []
    for c in df.columns:
        if 'Need' in c:
            color_ = resources.color_dict[c.split('_')[0]]
            name_ = c.replace('_',' ')
            trace = go.Scatter(
                x=list(df.index),
                y=list(df[c]),
                name=name_,
                mode='lines+markers',
                line=dict(shape='hv', color=color_, width=5),
                )
            traces.append(trace)

    layout = dict(
            height=450,
            title='Incremental Capacity (MW) Requirements'
            )

    fig = go.Figure(data=traces, layout=layout)

    fig['layout']['yaxis'].update(title='MW')
    fig['layout']['margin'].update(l=40,r=40,b=100,t=50,pad=0)
    fig['layout'].update(legend=dict(orientation="h"))
    fig['layout']['title'].update(x=0.5)

    return fig

@app.callback(
Output('capacity_cum_graph', 'figure'),
[Input('intermediate_df_capacity', 'data')]
)
def capacity_requirement_cumulative_graph(json):
    """Cumulative capacity requirement."""
    df = pd.read_json(json)

    traces = []
    for c in df.columns:
        if 'Need' in c:
            color_ = resources.color_dict[c.split('_')[0]]
            name_ = c.replace('_',' ')
            trace = go.Scatter(
                x=list(df.index),
                y=list(df[c].cumsum()), #cumsum for cumulative
                name=name_,
                mode='lines+markers',
                line=dict(shape='spline', color=color_, width=5),
                )
            traces.append(trace)

    layout = dict(
            height=450,
            title='Cumulative Capacity (MW) Requirements'
            )

    fig = go.Figure(data=traces, layout=layout)

    fig['layout']['yaxis'].update(title='MW')
    fig['layout']['margin'].update(l=40,r=40,b=100,t=50,pad=0)
    fig['layout'].update(legend=dict(orientation="h"))
    fig['layout']['title'].update(x=0.5)

    return fig


# ------ SECTION 3 ------
@app.callback(
    Output('lcoe_graph', 'figure'),
    [
        Input('energy_mix_table','data'),
        Input('energy_mix_table', 'columns')  
    ]
)
def lcoe_graph(rows, columns):
    """IRENA LCOE comparison plots."""
    input_cost_df = pd.DataFrame(rows, columns=[c['name'] for c in columns])

    input_traces = []
    traces = []
    line_traces = []
    spacer_traces = []

    # --- Calc min and max fossil cost ---
    coal_input_cost = float(input_cost_df.loc[input_cost_df['Generation Source'] == 'Coal', 'Levelized Cost of Energy (₱ / kWh)'][0:1].item())
    gas_input_cost = float(input_cost_df.loc[input_cost_df['Generation Source'] == 'Natural Gas', 'Levelized Cost of Energy (₱ / kWh)'][0:1].item())
    oil_input_cost = float(input_cost_df.loc[input_cost_df['Generation Source'] == 'Oil', 'Levelized Cost of Energy (₱ / kWh)'][0:1].item())
    fossil_costs = [coal_input_cost, gas_input_cost, oil_input_cost]
    fossil_range_low = min(fossil_costs)
    fossil_range_high = max(fossil_costs)
    
    for t in ['Utility-Scale Solar','Wind','Geothermal','Biomass','Hydro']:

        color = resources.color_dict[t]
        dfloc = resources.irena_lcoe_df.loc[resources.irena_lcoe_df['Technology'] == t]

        min_2010 = round(dfloc.loc[(dfloc['Year'] == 2010) & (dfloc['Item'] == 'MIN')]['pesos'][0:1].item(),2)
        max_2010 = round(dfloc.loc[(dfloc['Year'] == 2010) & (dfloc['Item'] == 'MAX')]['pesos'][0:1].item(),2)
        avg_2010 = round(dfloc.loc[(dfloc['Year'] == 2010) & (dfloc['Item'] == 'AVG')]['pesos'][0:1].item(),2)
        min_2017 = round(dfloc.loc[(dfloc['Year'] == 2018) & (dfloc['Item'] == 'MIN')]['pesos'][0:1].item(),2)
        max_2017 = round(dfloc.loc[(dfloc['Year'] == 2018) & (dfloc['Item'] == 'MAX')]['pesos'][0:1].item(),2)
        avg_2017 = round(dfloc.loc[(dfloc['Year'] == 2018) & (dfloc['Item'] == 'AVG')]['pesos'][0:1].item(),2)

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

    # --- Define rectangle fossil shape ---
    y_bottom_percent = min(fossil_range_low / 20, 1)
    y_top_percent = min(fossil_range_high / 20, 1)

    shapes = [
        {'type': 'rect', 'x0':0, 'x1':1, 'y0':y_bottom_percent, 'y1':y_top_percent, 'xref': 'paper', 'yref': 'paper', 'fillcolor':'Brown', 'opacity':0.2, 'layer':'below'}
    ]
    fig['layout'].update(shapes=shapes)

    fig.add_trace(go.Scatter(
        x=[3],
        y=[fossil_range_high - 1],
        text=["Fossil Fuel<br>LCOE Range"],
        mode="text",
        textfont={'size':10}
    ))

    for i in range(1,len(traces) + 1):
        fig['layout'][f'xaxis{i}'].update(tickvals=[1,1.2,2.2,3.2],
        ticktext=[' ','Global<br>2010 LCOE','Global<br>2018 LCOE','Your Actual<br>2019 LCOE'],
        tickangle=0, tickfont=dict(size=10))
        
    fig['layout']['yaxis'].update(title='₱ / kWh LCOE', range=[0,20])
    fig['layout']['title'].update(x=0.5)
    
    return fig

# ------ SECTION 4 ------
@app.callback(Output('doughnut_graph', 'figure'),
[
    Input('intermediate_dict_scenario','data')
])
def doughnut_graph(json):
    """Doughnut graph of capacity now/then."""
    input_dict = json_func.loads(json)

    start_generation_list = input_dict['start_generation_list']
    end_generation_list = input_dict['end_generation_list']
    techs = input_dict['techs']
    colors = [resources.color_dict[t] for t in techs]

    start = go.Pie(
            labels=techs,
            values=start_generation_list,
            marker={'colors':colors},
            domain={"column": 0},
            textinfo='none',
            hole = 0.45,
            hoverinfo = 'label+percent',
            sort=False,
            title=f"{input_dict['start_year']} Power Mix<br>{int(input_dict['start_re_pct'] *100)}% Renewables")
    
    end = go.Pie(
            labels=techs,
            values=end_generation_list,
            marker={'colors':colors},
            domain={"column": 1},
            textinfo='none',
            hole=0.45,
            hoverinfo = 'label+percent',
            sort=False,
            title=f"{input_dict['end_year']} Power Mix<br>{int(input_dict['end_re_pct'] * 100)}% Renewables")

    traces = [start, end]

    layout = go.Layout(height=350, grid={"rows": 1, "columns": 2}, showlegend=True)
    fig = go.Figure(data = traces, layout = layout)
    fig['layout']['title'].update(text='Comparative Generation Mix 2018 vs. 2030', x=0.5)
    fig['layout'].update(legend=dict(orientation="h"))
    fig['layout']['margin'].update(l=40,r=40,b=40,t=40,pad=0)
    
    return fig

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~ Table Outputs ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ----- SECTION 1 -----
@app.callback(
    Output('demand_and_REC_table', 'data'),
    [Input('intermediate_df', 'data')]
)
def html_REC_balance_table(json):
    """Table with Year, Energy Sales, RPS Requirements (%/RECs), RECs Created, RECs Expired, Year End REC Balance, and REC Purchase Requirement columns."""
    df = pd.read_json(json)
    df['Year'] = df.index
    dfout = df[['Year','demand','rps_req','rec_req','rec_created','rec_expired','end_rec_balance','rec_shortfall']]
    dfout.columns = ['Year','Energy Sales (MWh)','RPS Requirement (%)','RPS Requirement (RECs)', 'RECs Created', 'RECs Expired','Year End REC Balance','REC Purchase Requirement']
    float_columns = ['Energy Sales (MWh)','RPS Requirement (RECs)', 'RECs Created', 'RECs Expired', 'Year End REC Balance','REC Purchase Requirement']
    dfout[float_columns] = dfout[float_columns].round(0)
    dfout[float_columns] = add_commas(dfout[float_columns])
    dfout['RPS Requirement (%)'] = [str(round(i*100, 1))+'%' for i in dfout['RPS Requirement (%)']]
    dictout = dfout.to_dict('records')
    return dictout


@app.callback(
Output('capacity_cum_table', 'data'),
[Input('intermediate_df_capacity', 'data')]
)
def cumulative_table(json):
    """Cumulative capacity requirement by technology type and year."""
    df = pd.read_json(json)
    
    # --- Grab the columns we need ---
    keep_cols = [c for c in list(df.columns) if 'Need' in c]
    dfout = df[keep_cols]

    # ---Clean and cumulative ---
    dfout = dfout.fillna(0)
    dfout = dfout.cumsum()
    dfout = dfout.round(0)
    dfout = add_commas(dfout)

    # --- Add years column ---
    dfout['Year'] = dfout.index

    # --- Grab column names from dummy_requirements_df ---
    out_columns = ['Year'] + keep_cols
    dfout = dfout[out_columns]
    clean_cols = list(resources.dummy_requirements_df.columns)
    dfout.columns = clean_cols

    dictout = dfout.to_dict('records')

    return dictout

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~ Text Outputs ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ----- SECTION 1 ------

@app.callback(
    Output('energy_mix_error_text', 'children'),
    [
        Input('energy_mix_table', 'data'),
        Input('energy_mix_table', 'columns')
    ]
)
def energy_mix_text(rows, columns):
    """Create text for existing energy mix, warn if sums are over 100%"""
    energy_mix = pd.DataFrame(rows, columns=[c['name'] for c in columns])
    cols = ['Percent of Utility Energy Mix']
    energy_mix[cols] = energy_mix[cols].apply(pd.to_numeric, errors='coerce')

    energy_sum = energy_mix['Percent of Utility Energy Mix'].sum().round(1)
    renewable_sum = energy_mix.loc[energy_mix['Generation Source'].isin(resources.re_tech), 'Percent of Utility Energy Mix'].sum().round(1)

    if energy_sum != 100:
        output = f"""
        Please edit the Percent of Utility Energy Mix column so that the values sum to 100%. Currently they sum to **{energy_sum}%**.
        """.replace('  ', '') #test
    elif energy_sum == 100:
        output = f"""
        Your utility currently uses **{renewable_sum}%** renewables, although this likely does not count towards the RPS.
        """.replace('  ', '')
    return output

# ----- SECTION 2 ------

@app.callback(
    Output("capacity_text","children"),
    [
        Input('intermediate_df_capacity','data'),
        Input('solar_cf', 'value'),
        Input('geothermal_cf', 'value')
    ]
)                     
def capacity_text_maker(json, solar_cf, geothermal_cf):
    """Text for capacity need."""
    df = pd.read_json(json)
    first_year_of_Need = df.loc[df['rec_shortfall'] > 0].index.min()
    last_year = max(df.index)
    total_recs = df['rec_shortfall'].sum()
    first_year_recs = round(df.loc[first_year_of_Need, 'rec_shortfall'],0)
    last_year_recs = round(df.loc[last_year, 'rec_shortfall'],0)

    if first_year_recs != 0: #make sure that any recs will be needed
        first_year_recs = abs(first_year_recs)
        out = f"""
        Based on the input data, your utility will require additional RECs by {first_year_of_Need}. RECs can be created by procuring additional renewable capacity, 
        incentivizing customers to adopt net-metering or Green Energy Option Program (GEOP) systems, 
        or by making spot purchases through the REM/WESM.
        Because contracting and construction both take time, you should consider building renewables before {first_year_of_Need}. 
        By {last_year}, your utility needs to procure a cumulative total of **{int(total_recs):,}** RECs, starting with **{int(first_year_recs):,}** RECs in {first_year_of_Need}.
        It is important to plan for *when* and *how much* capacity to procure. 
        
        One option is to purchase renewables incrementally to meet the marginal RPS requirement in each year. This strategy involves spreading
        procurement over multiple years, which can hedge risk against the falling costs of renewables. Additionally, this strategy allows
        for growth in distributed energy resources, such as rooftop PV under the net-metering and Green Energy Option Program (GEOP), to count towards your
        RPS capacity needs. 
                
        In reality, a utility will likely need a balance incremental purchases along with larger single-year purchases and other options such as REC purchases through the WESM, 
        but this section of the calculator aims to convey the scale of new capacity needed.
        """.replace('  ', '')
    else:
        out="""
        Your utility will not need any Renewable Energy Certificates (RECs) to meet the RPS under this scenario, 
        but you should still consider installing additional renewable energy. Additional renewables can
        reduce your reliance on expensive imported fossil fuels, which will reduce your generation costs and rate volatility. 
        Customers will also be more likely to choose your service knowing that the power is clean.
        It is important for your utility to plan for *when* and *how much* capacity to procure.

        One option is to purchase renewables incrementally to meet the marginal RPS requirement in each year. This strategy involves spreading
        procurement over multiple years, which can hedge risk against the falling costs of renewables. Additionally, this strategy allows
        for growth in distributed energy resources, such as rooftop PV under the net-metering and Green Energy Option Program (GEOP), to count towards your
        RPS capacity needs. 
                
        In reality, a utility will likely need a balance incremental purchases along with larger single-year purchases and other options such as REC purchases through the WESM, 
        but this section of the calculator aims to convey the scale of new capacity needed.
        """.replace('  ','')

    return out

# ----- SECTION 4 -----

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
    The Levelized Cost of Energy (PhP / kWh) data used in this calculator can be changed in the 'Energy Mix and Cost Input' tab of User Inputs. You can edit this to reflect prices that are specific to your utility. 
    Based on the current entries, the cost of utility-scale solar for your utility is **Php {round(solar_cost - coal_cost, 1)} / kWh** compared with the cost of coal generation,
    and the cost of biomass has a difference of **Php {round(biomass_cost - coal_cost, 1)} / kWh**.
   """.replace('  ', '')

    return out

@app.callback(
    Output("savings_text","children"),
    [Input('intermediate_dict_scenario','data')]
)
def savings_text_maker(json):
    input_dict = json_func.loads(json)

    currency_exchange = 50 #pesos in usd

    start_cost = int(input_dict['start_expense'])
    start_cost_usd = int(start_cost / currency_exchange)
    start_demand = input_dict['start_demand']
    start_cost_kwh = round(start_cost / start_demand / 1000,3)
    start_cost_kwh_usd = round(start_cost_kwh / currency_exchange,3)

    end_re_pct = input_dict['end_re_pct']

    end_cost = int(input_dict['end_expense'])
    end_cost_usd = int(end_cost / currency_exchange)
    end_demand = input_dict['end_demand']
    end_cost_kwh = round(end_cost / end_demand / 1000,3)
    end_cost_kwh_usd = round(end_cost_kwh / currency_exchange,3)

    out = f"""
    ###### Your current generation costs are ${start_cost_usd:,} (Php {start_cost:,}), or **${start_cost_kwh_usd} (Php {start_cost_kwh} / kWh)**. By switching to **{int(end_re_pct * 100)}% renewables** by {input_dict['end_year']}, your estimated generation costs would be ${end_cost_usd:,} (Php {end_cost:,}), or **${end_cost_kwh_usd} (Php {end_cost_kwh} / kWh)**. Currently you are creating {input_dict['start_recs']:,} RECs, and in 2030 you would be creating {int(input_dict['end_recs']):,} RECs per year. Future generation costs are estimates that may change as market conditions evolve.
        """.replace('  ', '')

    return out

@app.callback(
    Output("goal_text","children"),
    [Input('intermediate_dict_scenario','data')]
)
def goal_text_maker(json):
    
    input_dict = json_func.loads(json)

    rps_min_increase = input_dict['rps_min_increase'] * 100


    out = f"""
    While the RPS will require your utility to increase your renewable energy supply by **{round(rps_min_increase,0)}%**,
    it may be cost-effective to go beyond this amount. Additional renewable procurement can provide price stability and may increase customer satisfaction with your utility. 
    Additional renewables also allow you to bank RECs, which can be sold through the WESM as a secondary revenue stream, or held for future compliance years.

    First, you should ensure that the LCOE and Energy Mix data in the 'Energy Mix and Cost Input' tab available at the top of the tool is correct. 
    Once this data has been input, this section will allow you to visualize and compare generation costs between various renewable growth scenarios.

    Using the slider below, you can change the desired percentage of renewables for your utility. This has been preset at the minimum RPS requirement. 
    Below the slider, you can also select the mix of renewables that will be installed. As you change the desired renewable percentage and the mix of new renewables, the price per kWh will be updated.
    These prices are derived from the LCOE values specified in the 'Energy Mix and Cost Input.' Next, you can select an optimization factor, cost or emissions, that will determine the type of fossil
    fuels added to your growing overall capacity. Emissions calculations are based on 2017 EIA and US EPA data on heat content and heat rates for thermal fuels. 
   """.replace('  ', '')

    return out

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~ Cosmetics ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.callback(
    Output('future_procurement_table', 'data'),
    [Input('editing-rows-button', 'n_clicks')],
    [State('future_procurement_table', 'data'),
     State('future_procurement_table', 'columns')])
def add_row(n_clicks, rows, columns):
    """Add row to future procurement."""
    if n_clicks > 0:
        rows.append({c['id']: '' for c in columns})
    return rows


@app.callback(
    Output('energy_mix_error_text','style'),
    [Input('energy_mix_error_text','children')]
)
def color_text(energy_mix_error_text):
    """Color energy_mix_text() red."""
    output = energy_mix_error_text
    if 'Please' in output:
        color = {'color':'red'}
    else: 
        color = {'color':'black'} 
    return color

