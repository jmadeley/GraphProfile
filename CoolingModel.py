import numpy as np
from scipy.interpolate import interp1d

# TimeHours array
TimeHours = [
    -3.00,
    +0.00, +0.25, +0.50, +0.75, +1.00, +1.25, +1.50, +1.75,
    +2.00, +2.25, +2.50, +2.75, +3.00, +3.25, +3.50, +3.75,
    +4.00, +4.25, +4.50, +4.75, +5.00, +5.25, +5.50, +5.75,
    +6.00, +6.25, +6.50, +6.75, +7.00, +7.25, +7.50, +7.75,
    +8.00, +8.25, +8.50, +8.75, +9.00, +9.25, +9.50, +9.75,
    +10.00, +10.25, +10.50, +10.75, +11.00, +11.25, +11.50, +11.75,
    +12.00, +12.25, +12.50, +12.75, +13.00, +13.25, +13.50, +13.75,
    +14.00, +14.25, +14.50, +14.75, +15.00, +15.25, +15.50, +15.75,
    +16.00, +16.25, +16.50, +16.75, +17.00, +17.25, +17.50, +17.75,
    +18.00, +18.25, +18.50, +18.75, +19.00, +19.25, +19.50, +19.75,
    +29.75,
]

# PassiveTemperaturesCelsius array
PassiveTemperaturesCelsius = [
    +2575.86,
    +1254.27, +1148.17, +1059.39, +990.93, +934.85, +886.91, +843.75, +804.71,
    +769.45, +737.02, +707.51, +680.11, +653.80, +628.35, +604.37, +581.58,
    +560.06, +539.63, +519.88, +501.35, +483.70, +466.90, +450.64, +434.38,
    +418.40, +403.07, +388.16, +374.16, +360.83, +347.94, +335.52, +323.63,
    +312.14, +301.10, +290.49, +280.28, +270.75, +261.12, +251.42, +242.13,
    +233.25, +224.51, +216.12, +208.35, +200.94, +193.60, +186.33, +179.81,
    +173.68, +167.37, +161.60, +154.98, +149.40, +144.00, +138.71, +133.62,
    +128.71, +123.97, +119.40, +114.99, +110.73, +106.62, +102.66, +98.84,
    +95.15, +91.59, +88.16, +84.85, +81.65, +78.57, +75.60, +72.73,
    +69.96, +67.29, +64.71, +62.23, +59.78, +57.34, +54.91, +52.47,
    -30.33,
]

# ActiveTemperaturesCelsius array
ActiveTemperaturesCelsius = [
    2324.7,
    1380.0, 1270.7, 1172.9, 1084.9, 1004.9, 931.4, 862.7, 797.1,
    733.0, 668.6, 602.3, 532.5, 457.4, 375.4, 284.9, 184.1,
    71.4, 61.2, 52.9, 46.3, 41.1, 36.9, 33.5, 30.8,
    28.6, 26.9, 25.5, 24.4, 23.5, 22.8, 22.3, 21.8,
    21.3, 20.8, 20.3, 19.8, 19.3, 18.8, 18.3, 17.8,
    17.3, 16.8, 16.3, 15.8, 15.3, 14.8, 14.3, 13.8,
    13.3, 12.8, 12.3, 11.8, 11.3, 10.8, 10.3, 9.8,
    9.3, 8.8, 8.3, 7.8, 7.3, 6.8, 6.3, 5.8,
    5.3, 4.8, 4.3, 3.8, 3.3, 2.8, 2.3, 1.8,
    1.3, 0.8, 0.3, -0.2, -0.7, -1.2, -1.7, -2.2,
    -22.2
]
TimeHours_r = np.flip(TimeHours)
PassiveTemperaturesCelsius_r = np.flip(PassiveTemperaturesCelsius)
ActiveTemperaturesCelsius_r = np.flip(ActiveTemperaturesCelsius)
ActiveGetTimeInterpolator = interp1d(ActiveTemperaturesCelsius_r, TimeHours_r, kind='linear')
PassiveGetTimeInterpolator = interp1d(PassiveTemperaturesCelsius_r, TimeHours_r, kind='linear')
ActiveGetTemperatureInterpolator = interp1d(TimeHours, ActiveTemperaturesCelsius, kind='linear')
PassiveGetTemperatureInterpolator = interp1d(TimeHours, PassiveTemperaturesCelsius, kind='linear')

def get_cooling_curves( start_temperature, end_temperature, starting_time, maximum_activeCooling_temperature ):
    if maximum_activeCooling_temperature < start_temperature:
        passive_cooling_times, passive_cooling_temperatures = get_cooling_curve( start_temperature, maximum_activeCooling_temperature, starting_time, False )
        start_cooling_time = passive_cooling_times[-1]
        start_cooling_temperatures = passive_cooling_temperatures[-1]
        active_cooling_times, active_cooling_temperatures = get_cooling_curve( start_cooling_temperatures, end_temperature, start_cooling_time, True )
        return passive_cooling_times + active_cooling_times, passive_cooling_temperatures + active_cooling_temperatures
    else:
        return get_cooling_curve( start_temperature, end_temperature, starting_time, True )

def get_cooling_curve( start_temperature, end_temperature, starting_time, is_active = True ):
    start_hours = get_time(start_temperature, is_active)
    end_hours = get_time(end_temperature, is_active)
    sample_times = np.linspace(start_hours, end_hours, 20)
    sampled_temperatures = get_temperatures(sample_times, is_active)
    adjusted_times = sample_times - start_hours + starting_time
    return adjusted_times.tolist(), sampled_temperatures.tolist()

def get_time( temperature, is_active = True ):
    if is_active:
        return ActiveGetTimeInterpolator(temperature)
    else:
        return PassiveGetTimeInterpolator(temperature)

def get_temperatures( temperature, is_active = True ):
    if is_active:
        return ActiveGetTemperatureInterpolator(temperature)
    else:
        return PassiveGetTemperatureInterpolator(temperature)

def get_monotonic_curve(x_list, y_list,is_increasing_y):
    if is_increasing_y:
        x_out = []
        y_out = []
        y_last = y_list[0]
        for x,y in zip(x_list, y_list):
            if y >= y_last:
                x_out.append(x)
                y_out.append(y)
                y_last = x
            else:
                break
        return x_out, y_out
    else:
        x_list_r = np.flip(x_list)
        y_list_r = np.flip(y_list)
        return get_monotonic_curve(x_list_r, y_list_r, False)

def get_reverse_interpolator(x_list, y_list, is_increasing_y):
    # return an interpolator which given y (temperature) returns x (time)
    # y values must be monotonic increasing or decreasing
    x, y = get_monotonic_curve(x_list, y_list, is_increasing_y)
    return interp1d(y, x, kind='linear')
