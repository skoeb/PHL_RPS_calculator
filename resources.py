import pandas as pd

# --- Import dfs and dicts used throughout ---
dummy_df = pd.read_csv('dummy_df.csv')
dummy_df['Year'] = dummy_df.index
dummy_df_display = dummy_df[['Year','demand','rps_req','rec_req','rec_created','rec_expired','end_rec_balance','rec_shortfall']]
dummy_df_display.columns = ['Year','Energy Sales (MWh)','RPS Requirement (%)','RPS Requirement (RECs)', 'RECs Created', 'RECs Expired','Year End REC Balance','REC Purchase Requirement']

irena_lcoe_df = pd.read_csv("irena_lcoe.csv")
irena_lcoe_df = irena_lcoe_df.dropna(subset = ['Technology'])

dummy_lcoe_df = pd.read_csv("dummy_lcoe.csv")

energy_mix_df = pd.read_csv("energy_mix.csv")
energy_mix_df['Percent of Utility Energy Mix'] = energy_mix_df['Percent of Utility Energy Mix'] * 100

new_build_df = pd.DataFrame({'Generation Source':['Utility-Scale Solar', '', ''],
                            'Capacity (MW)': [0, '',''],
                            'Online Year': [2020,'','']})

dummy_desired_pct_df = pd.read_csv("dummy_desired_pct.csv")

dummy_requirements_df = pd.read_csv("dummy_requirement.csv")

utility_df = pd.read_csv("utility_data.csv", index_col='utility')
utility_dict = utility_df[~utility_df.index.duplicated(keep='first')].to_dict('index')

emissions_df = pd.read_csv('emissions.csv')
emissions_dict = dict(zip(emissions_df['Generation Source'], emissions_df['CO2']))

re_tech = ['Utility-Scale Solar','Net-Metering','GEOP','Wind','Geothermal','Biomass','Hydro']
fossil_tech = ['Coal', 'Natural Gas','Oil', 'WESM Purchases']

color_dict = {
    'Solar':('#ffc425'),
    'Other':('#f37735'),
    'Biomass':('#00b159'),
    'Geothermal':('#d11141'),
    'Hydro':('#115CBF'),
    'Wind':('#00aedb'),
    'Distributed PV':('#FFE896'),
    'GEOP':('#FFE896'),
    'Net-Metering':('#FFE896'),
    'Utility-Scale Solar':('#ffc425'),
    'Other':('#f37735'),
    'Natural Gas':('#DE8F6E'),
    'WESM Purchases':('#777777'),
    'Natural Gas':('#333333'),
    'Oil':('#555555'),
    'Coal':('#111111'),
}

scenario_pct_dict = {
    'SUN':{'Utility-Scale Solar':1},
    'NEM':{'Net-Metering':0.5, 'GEOP':0.5},
    'WND':{'Wind':1},
    'BIO':{'Biomass':1},
    'GEO':{'Geothermal':1},
    'HYDRO':{'Hydro':1},
    'BAL':{'Utility-Scale Solar':1/7, 'Net-Metering':1/7, 'GEOP':1/7, 'Wind':1/7, 'Biomass':1/7, 'Geothermal':1/7, 'Hydro':1/7}
}