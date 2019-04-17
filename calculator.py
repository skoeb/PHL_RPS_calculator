#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: SamKoebrich

"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import qgrid

import ipywidgets as widgets
import warnings
warnings.filterwarnings("ignore")

from IPython.core.display import display, HTML
display(HTML("<style>.container { width:85% !important; }</style>"))
display(HTML("<style>.output_wrapper, .output {height:auto !important; max-height:5000px;}.output_scroll {box-shadow:none !important; webkit-box-shadow:none !important;}</style>"))

get_ipython().run_line_magic('matplotlib', 'inline')

style = {'description_width': '300px'}
layout = {'width': '700px'}

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

def bar_plotter(demand = 100000, demand_growth = 0.045, eligible_re_2018 = 10000,
                 annual_rps_inc_2020 = 0.01, annual_rps_inc_2023 = 0.02, losses = 0.18,
                 end_year = 2030):
    
    df = rps_df_maker(demand = float(demand), demand_growth = demand_growth, eligible_re_2018 = float(eligible_re_2018),
                      annual_rps_inc_2020 = annual_rps_inc_2020, annual_rps_inc_2023 = annual_rps_inc_2023,
                      losses = losses, end_year = end_year)
    df = df.fillna(0)
    
    sns.set_style('darkgrid')
    
    fig, ax = plt.subplots(figsize = (10,4), dpi = 100)
    df[['demand','rec_req','rec_balance','rec_change']].plot.bar(rot = 45, ax = ax)
    plt.legend(labels = ['Demand','RPS Retirements','REC Balance','REC Balance Change'],
               title = 'Estimated Values', fontsize = 8)
    plt.xlabel('Year')
    plt.ylabel('MWh / REC')
    plt.title('Annual RPS Requirements and REC Balance')



    #qgrid df
    grid = df[['demand','rec_req','rec_balance','rec_change']]
    grid = grid.round(0)
    grid.columns = ['Demand','RPS Retirements','REC Balance','REC Balance Change']
    col_options = {
        'width': 30,
    }
    
    qgrid_widget = qgrid.show_grid(grid,
                                   column_options = col_options,
                                   show_toolbar = False)
    
    plt.show()
    display(qgrid_widget)

    
demandwidget = widgets.Text(
                    value='100000',
                    description='2018 Demand (MWh):',
                    disabled=False,
                    style = style,
                    layout = layout)

eligiblerewidget = widgets.Text(
                    value='10000',
                    description='Existing Eligible RE Annual Generation (MWh):',
                    disabled=False,
                    style = style,
                    layout = layout) 

demandgrowthslider = widgets.FloatSlider(
                    value = .045,
                    min=0,
                    max=0.15,
                    step = .0025,
                    description = 'Annual Demand Growth (%):',
                    disabled = False,
                    continuous_update = False,
                    orientation = 'horizontal',
                    readout = True,
                    readout_format = '.2%',
                    style = style,
                    layout = layout)

rps2020slider = widgets.FloatSlider(
                    value = .01,
                    min=0,
                    max=0.05,
                    step = .005,
                    description = 'Annual RPS Increment 2020-2023 (%):',
                    disabled = False,
                    continuous_update = False,
                    orientation = 'horizontal',
                    readout = True,
                    readout_format = '.1%',
                    style = style,
                    layout = layout)

rps2023slider = widgets.FloatSlider(
                    value = .03,
                    min=0,
                    max=0.05,
                    step = .005,
                    description = 'Annual RPS Increment 2023- (%):',
                    disabled = False,
                    continuous_update = False,
                    orientation = 'horizontal',
                    readout = True,
                    readout_format = '.1%',
                    style = style,
                    layout = layout)

linelossslider = widgets.FloatSlider(
                    value = .18,
                    min=0,
                    max=0.25,
                    step = .01,
                    description = 'Line Losses:',
                    disabled = False,
                    continuous_update = False,
                    orientation = 'horizontal',
                    readout = True,
                    readout_format = '0.0%',
                    style = style,
                    layout = layout)

endyearwidget = widgets.Text(
                    value='2030',
                    description='RPS End Year:',
                    disabled=False,
                    style = style,
                    layout = layout)
    
ui = widgets.VBox([demandwidget, eligiblerewidget,demandgrowthslider,linelossslider,
                   rps2020slider, rps2023slider, endyearwidget])
out = widgets.interactive_output(bar_plotter,{'demand':demandwidget,
                                              'demand_growth':demandgrowthslider,
                                              'eligible_re_2018':eligiblerewidget,
                                              'annual_rps_inc_2020':rps2020slider,
                                              'annual_rps_inc_2023':rps2023slider,
                                              'losses':linelossslider,
                                              'end_year':endyearwidget})
display(ui, out)