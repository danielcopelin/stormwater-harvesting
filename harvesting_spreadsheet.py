import collections
import pandas as pd
import numpy as np

def daily_irrigation_demand_mm(df):

    df = df.copy()

    df['Daily_Irrigation_Demand_mm'] = 0.0
    diff_days = pd.Series(df.index.date).diff()
    new_days = diff_days[diff_days == pd.Timedelta(1, 'd')].index
    
    weekly_irrigation = collections.deque(maxlen=7)

    for i in new_days:
        weekly_irrigation_demand = df.Weekly_Irrigation_Demand.iloc[i]
        rolling_weekly_rainfall = df.Weekly_Rainfall.iloc[i]
        rolling_weekly_irrigation_total_prev = sum(weekly_irrigation)

        if weekly_irrigation_demand \
            > (rolling_weekly_rainfall + rolling_weekly_irrigation_total_prev):
            daily_irrigation = (weekly_irrigation_demand - rolling_weekly_rainfall) / 7.0
        else:
            daily_irrigation =  0.0
        
        weekly_irrigation.append(daily_irrigation)

        df.Daily_Irrigation_Demand_mm.iloc[i] = daily_irrigation

    return df.Daily_Irrigation_Demand_mm

def daily_irrigation_demand_m3(daily_irrigation_demand_mm, irrigation_area):
    return daily_irrigation_demand_mm / 1000.0 * irrigation_area

def hourly_runoff_harvested(
    tank_max, tank_prev, runoff_cur, det_prev, overflow_cur, pump
    ):
    if (tank_max - tank_prev) == 0.0:
        return 0.0
    if (runoff_cur + det_prev - overflow_cur) > (tank_max - tank_prev):
        if pump > (runoff_cur + det_prev - overflow_cur):
            return (det_prev + runoff_cur)
        else:
            return pump
    else:
        if (runoff_cur + det_prev - overflow_cur) > pump:
            return pump
        else:
            return (runoff_cur + det_prev - overflow_cur)

def detention_basin_volume(
    runoff_cur, det_prev, hourly_runoff_harvested_cur, det, overflow_cur
    ):
    if (runoff_cur + det_prev - hourly_runoff_harvested_cur) > det:
        return det
    else:
        if (runoff_cur + det_prev - hourly_runoff_harvested_cur - overflow_cur) < 0.0:
            return 0.0
        else:
            return (runoff_cur + det_prev - hourly_runoff_harvested_cur - overflow_cur)

def detention_basin_overflow(
    tank_max, tank_prev, det_max, det_prev, runoff_cur, pump
    ):
    if (tank_max - tank_prev == 0.0) and (det_max - det_prev == 0.0):
        return runoff_cur
    else:
        if runoff_cur - pump - (det_max - det_prev) < 0.0:
            return max(runoff_cur - (det_max - det_prev), 0)
        else:
            if tank_max - tank_prev == 0.0:
                return runoff_cur - (det_max - det_prev)
            else:
                return runoff_cur - pump - (det_max - det_prev)

def harvesting_tank_volume(
    hourly_runoff_harvested_cur, tank_prev, daily_irrigation_demand_m3_cur,
    tank_max):
    new_tank_volume = (
                        hourly_runoff_harvested_cur
                        + tank_prev 
                        - daily_irrigation_demand_m3_cur
                    )
    if new_tank_volume > tank_max:
        return tank_max
    else:
        if new_tank_volume > 0.0:
            return new_tank_volume
        else:
            return 0.0

def harvesting_tank_overflow(
    tank_prev, tank_cur, hourly_runoff_harvested_cur, tank_max, daily_irrigation_demand_m3_cur):
    if (tank_prev + hourly_runoff_harvested_cur - daily_irrigation_demand_m3_cur) > tank_max:
        return hourly_runoff_harvested_cur - (tank_cur - tank_prev)
    else:
        return 0.0

def percent_daily_irrigation_demand_met(daily_irrigation_demand_m3_cur, tank_prev, harv_cur):
    if daily_irrigation_demand_m3_cur > 0:
        try:
            if (tank_prev + harv_cur) / daily_irrigation_demand_m3_cur > 1.0:
                return 1.0
            else:
                return (tank_prev + harv_cur) / daily_irrigation_demand_m3_cur
        except:
            return 1.0
    else:
        return None

def cumulative_mass_balance_error(
    runoff_cur, overflow_cur, tank_cur, tank_prev, det_cur, det_prev, 
    tank_overflow_cur, dem_met, daily_irrigation_demand_m3_cur, mass_bal_prev):

    if dem_met is None:
        dem_met = 0.0

    sum_inflows = runoff_cur
    sum_outflows = (dem_met*daily_irrigation_demand_m3_cur
                    + overflow_cur 
                    + tank_overflow_cur)
    end_minus_start = (tank_cur - tank_prev) + (det_cur - det_prev)

    mass_bal_error = sum_inflows - (sum_outflows + end_minus_start)

    return mass_bal_error + mass_bal_prev

def water_balance(df, tank_max, pump, det_max, tank_start=0.0):

    harv = [0.0]
    tank = [tank_start]
    det = [0.0]
    overflow = [0.0]
    tank_overflow = [0.0]
    demand_met = [np.nan]
    mass_bal = [0.0]

    for i in range(1, len(df)):
        runoff_cur = df.Runoff.iloc[i]
        daily_irrigation_demand_m3_cur = df.Daily_Irrigation_Demand_m3.iloc[i]

        overflow.append(detention_basin_overflow(tank_max, tank[i-1], det_max, det[i-1], runoff_cur, pump))
        harv.append(hourly_runoff_harvested(tank_max, tank[i-1], runoff_cur, det[i-1], overflow[i], pump))
        tank.append(harvesting_tank_volume(harv[i], tank[i-1], daily_irrigation_demand_m3_cur, tank_max))
        det.append(detention_basin_volume(runoff_cur, det[i-1], harv[i], det_max, overflow[i]))
        tank_overflow.append(harvesting_tank_overflow(tank[i-1], tank[i], harv[i], tank_max, daily_irrigation_demand_m3_cur))
        demand_met.append(percent_daily_irrigation_demand_met(daily_irrigation_demand_m3_cur, tank[i-1], harv[i]))
        mass_bal.append(
            cumulative_mass_balance_error(
                runoff_cur, overflow[i], tank[i], tank[i-1], det[i], det[i-1], 
                tank_overflow[i], demand_met[i], daily_irrigation_demand_m3_cur, mass_bal[i-1])
        )

    df['Overflow'] = overflow
    df['Hourly_Runoff_Harvested'] = harv
    df['Tank_Volume'] = tank
    df['Detention_Basin_Volume'] = det
    df['Tank_Overflow'] = tank_overflow
    df['Fraction_Demand_Met'] = demand_met
    df['Bool_Demand_Met'] = pd.notnull(df.Fraction_Demand_Met) & (df.Fraction_Demand_Met == 1)
    df['Actual_Demand_Met_m3'] = df.Fraction_Demand_Met * df.Daily_Irrigation_Demand_m3
    df['Cumulative_Mass_Balance_Error_m3'] = mass_bal

    return df

def mass_balance_check(df):
    total_runoff = df.Runoff.sum()
    total_irrigation = df.Actual_Demand_Met_m3.sum()
    total_det_overflow = df.Overflow.sum()
    total_tank_overflow = df.Tank_Overflow.sum()
    change_in_detention = df.Detention_Basin_Volume[-1] - df.Detention_Basin_Volume[0]
    change_in_tank = df.Tank_Volume[-1] - df.Tank_Volume[0]

    sum_inflows = total_runoff
    sum_outflows = total_irrigation + total_det_overflow + total_tank_overflow
    end_minus_start = change_in_detention + change_in_tank

    mass_balance = sum_inflows - (sum_outflows + end_minus_start)

    return mass_balance

def simulate_harvesting(
    df, tank_max, pump, det_max, irrigation_series,
    irrigation_area, tank_start):

    # pre-compute the independent columns
    df['Weekly_Rainfall'] = df.Rainfall.rolling('7d').sum()
    df['Weekly_Irrigation_Demand'] = df.index.month.map(irrigation_series)
    df['Daily_Irrigation_Demand_mm'] = daily_irrigation_demand_mm(df)
    df['Daily_Irrigation_Demand_m3'] = daily_irrigation_demand_m3(
        df.Daily_Irrigation_Demand_mm, irrigation_area)
    df['Weekly_Irrigation_Total'] = df.Daily_Irrigation_Demand_mm.rolling('7d').sum()
    df['Weekly_Rainfall_Irrigation_Total'] = (df.Weekly_Rainfall 
                                             + df.Weekly_Irrigation_Total)

    # run the water balance simulation (requires looping)
    df = water_balance(df, tank_max, pump, det_max, tank_start)

    return df

if __name__ == '__main__':

    from ConfigParser import SafeConfigParser

    config = SafeConfigParser()
    config.read('config.ini')
    params = dict([item for sublist in [config.items(section) for section in config.sections()] for item in sublist])

    rainfall_runoff_source = params['rainfall_runoff_source']
    irrigation_source = params['irrigation_source']

    tank_max = float(params['tank_max'])
    tank_start = float(params['tank_start'])
    det_max = float(params['det_max'])
    pump = float(params['pump'])
    irrigation_area = float(params['irrigation_area'])

    df = pd.read_csv(rainfall_runoff_source, parse_dates=True, dayfirst=True, index_col=0)
    irrigation_series = pd.read_csv(irrigation_source, parse_dates=True, dayfirst=True, index_col=0).Irrigation

    results = simulate_harvesting(
        df, tank_max, pump, det_max, irrigation_series, irrigation_area, tank_start)

    print("Mass volume error (m3): {0:.2f}".format(mass_balance_check(results)))
    print("Mass volume error (%): {0:.2f}".format(mass_balance_check(results) / df.Runoff.sum() * 100.0))

    results.to_csv('results.csv')