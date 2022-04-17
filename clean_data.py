#!/usr/bin/python3

"""
Usage: python3 clean_data.py -f=jfk_weather.csv -v
"""

import sys
import numpy as np
import pandas as pd
import argparse

parser = argparse.ArgumentParser(description='Cleans up NOAA weather data')
parser.add_argument('-f', '--filepath', default='jfk_weather.csv', help='Filepath to NOAA weather data')
parser.add_argument('-v', '--verbose', action='store_true', help='Print verbose')
args = parser.parse_args()

def tryconvert(value, dt=None):
    """
    value -> Value to be converted
    dt    -> data type to convert to (redundant for now)
    """
    try:
        return np.float64(value)
    except:
        return np.nan

def main():
    DATA_FILEPATH = args.filepath
    
    import_columns = [  'DATE',
                        'HOURLYVISIBILITY',
                        'HOURLYDRYBULBTEMPF',
                        'HOURLYWETBULBTEMPF',
                        'HOURLYDewPointTempF',
                        'HOURLYRelativeHumidity',
                        'HOURLYWindSpeed',
                        'HOURLYWindDirection',
                        'HOURLYStationPressure',
                        'HOURLYPressureTendency',
                        'HOURLYSeaLevelPressure',
                        'HOURLYPrecip',
                        'HOURLYAltimeterSetting']
    
    # Read data and set datetime index
    data_weather = pd.read_csv(DATA_FILEPATH, parse_dates=['DATE'], usecols=import_columns)
    data_weather = data_weather.set_index(pd.DatetimeIndex(data_weather['DATE']))
    data_weather.drop(['DATE'], axis=1, inplace=True)
    
    # Replace '*' values with np.nan
    data_weather.replace(to_replace='*', value=np.nan, inplace=True)
    # Replace trace amounts of precipitation with 0
    data_weather['HOURLYPrecip'].replace(to_replace='T', value='0.00', inplace=True) 
    # Replace rows with tow '.' with np.nan
    data_weather.loc[data_weather['HOURLYPrecip'].str.count('\.') > 1, 'HOURLYPrecip'] = np.nan 

    # Convert to float
    for i, _ in enumerate(data_weather.columns):
        data_weather.iloc[:,i] =  data_weather.iloc[:,i].apply(lambda x: tryconvert(x))

    # Replace any hourly visibility figure outside these 0-10 bounds
    data_weather.loc[(data_weather['HOURLYVISIBILITY'] > 10) | (data_weather['HOURLYVISIBILITY'] < 0), 'HOURLYVISIBILITY'] = np.nan

    # Downsample to hourly rows 
    data_weather = data_weather.resample('60min').last().shift(periods=1) 

    # Interpolate missing values
    data_weather['HOURLYPressureTendency'] = data_weather['HOURLYPressureTendency'].fillna(method='ffill') #fill with last valid observation
    data_weather = data_weather.interpolate(method='linear')
    data_weather.drop(data_weather.index[0], inplace=True) #drop first row

    # Transform HOURLYWindDirection into a cyclical variable using sin and cos transforms
    data_weather['HOURLYWindDirectionSin'] = np.sin(data_weather['HOURLYWindDirection']*(2.*np.pi/360))
    data_weather['HOURLYWindDirectionCos'] = np.cos(data_weather['HOURLYWindDirection']*(2.*np.pi/360))
    data_weather.drop(['HOURLYWindDirection'], axis=1, inplace=True)

    # Transform HOURLYPressureTendency into 3 dummy variables based on NOAA documentation
    data_weather['HOURLYPressureTendencyIncr'] = [1.0 if x in [0,1,2,3] else 0.0 for x in data_weather['HOURLYPressureTendency']] # 0 through 3 indicates an increase in pressure over previous 3 hours
    data_weather['HOURLYPressureTendencyDecr'] = [1.0 if x in [5,6,7,8] else 0.0 for x in data_weather['HOURLYPressureTendency']] # 5 through 8 indicates a decrease over the previous 3 hours
    data_weather['HOURLYPressureTendencyCons'] = [1.0 if x == 4 else 0.0 for x in data_weather['HOURLYPressureTendency']] # 4 indicates no change during the previous 3 hours
    data_weather.drop(['HOURLYPressureTendency'], axis=1, inplace=True)
    data_weather['HOURLYPressureTendencyIncr'] = data_weather['HOURLYPressureTendencyIncr'].astype(('float32'))
    data_weather['HOURLYPressureTendencyDecr'] = data_weather['HOURLYPressureTendencyDecr'].astype(('float32'))
    data_weather['HOURLYPressureTendencyCons'] = data_weather['HOURLYPressureTendencyCons'].astype(('float32'))

    # Output csv based on input filename
    file_name, extension = args.filepath.split(".")
    data_weather.to_csv(file_name +'_cleaned.csv', float_format='%g')

    if args.verbose:
        print("Data successfully cleaned, below are some stats:")
        print('# of megabytes held by dataframe: ' + str(round(sys.getsizeof(data_weather) / 1000000,2)))
        print('# of features: ' + str(data_weather.shape[1])) 
        print('# of observations: ' + str(data_weather.shape[0]))
        print('Start date: ' + str(data_weather.index[0]))
        print('End date: ' + str(data_weather.index[-1]))
        print('# of days: ' + str((data_weather.index[-1] - data_weather.index[0]).days))
        print('# of months: ' + str(round((data_weather.index[-1] - data_weather.index[0]).days/30,2)))
        print('# of years: ' + str(round((data_weather.index[-1] - data_weather.index[0]).days/365,2)))

if __name__ == "__main__":
    main()