import pandas as pd
import numpy as numpy

def parse_dnrm_data(source):
    """Parses DNRM format rainfall and streamflow data.
    
    Arguments:
        source {csv file} -- A csv file from DNRM's Water Monitoring 
        Portal, with Rainfall (mm) and Discharge (cumecs) columns.
    
    Returns:
        DataFrame -- A DataFrame with a Datetime index, and colums for
        Rainfall, Discharge, Volume and Timestep.
    """

    df = pd.read_csv(source, usecols=[0, 1, 3], skiprows=3, 
                 skipfooter=3, index_col=0, parse_dates=True,
                 dayfirst=True, engine='python')

    df.columns = ['Rainfall', 'Discharge']
    df.Discharge = df.Discharge.fillna(0)
    df['Timestep'] = (df.index.to_series().diff() / pd.Timedelta(1, 's'))
    df['Volume'] = (df.Timestep * df.Discharge.rolling(2).mean()).fillna(0)
    
    return df

def harvesting_calcs(data, demand, max_volume, start_volume, pump_flow):
    """[summary]
    
    Arguments:
        data {[type]} -- [description]
    """

    def _harvest_flow(row, pump_flow):
        if row.Discharge < pump_flow:
            return max(0.0, row.Discharge)
        else:
            return pump_flow

    df = data.copy()

    df['Harvest_Flow'] = df.apply(_harvest_flow, args=[pump_flow], axis=1)
    df['Harvest_Volume'] = (df.Timestep * df.Harvest_Flow.rolling(2).mean()).fillna(0)

    df['Demand'] = demand * ~df.Rainfall.astype(bool) # only irrigate if not raining
    df['Demand_Volume'] = (df.Timestep * df.Demand.rolling(2).mean()).fillna(0)    

    tank_volume = [start_volume]
    harvest_actual = [0]

    for i in range(1, len(df)):
        prev_volume = tank_volume[i-1]
        new_volume = prev_volume + df.Harvest_Volume.values[i] - df.Demand_Volume.values[i]
        if new_volume < 0:
            new_volume = 0
        elif new_volume > max_volume:
            new_volume = max_volume
        tank_volume.append(new_volume)
        harvest_actual.append(
            0
            # max(0, new_volume-tank_volume[i-1]+df.Demand_Volume.values[i])
        )
        
    df['Tank_Volume'] = tank_volume
    df['Harvest_Actual'] = harvest_actual

    return df

def summarise_results(data):
    """[summary]
    
    Arguments:
        data {[type]} -- [description]
    
    Returns:
        [type] -- [description]
    """
    df = data.copy()
    summary = {}

    summary['demand_total'] = df.Demand_Volume.sum()
    summary['harvest_total'] = df.Harvest_Actual.sum()
    summary['fraction_supplied'] = summary['demand_total'] / summary['harvest_total']

    return summary
