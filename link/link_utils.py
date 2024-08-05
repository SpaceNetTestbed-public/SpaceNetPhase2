import os
import numpy as np
import math
import itur
import requests
import json

import sys
sys.path.append("../")
from mobility.mobility_utils import *

api_key = "d06b0a02f8377dff811a2a6d0882a2d6"

channelFreq_isls                        = 37.0;             # in GHz
channelFreq_sat_to_ground               = 12.7;             # in GHz
channelFreq_ground_to_sat               = 14.5;             # in GH
channnel_bandwidth_downlink             = 240;               #MHz
channnel_bandwidth_uplink               = 60;               #MHz
polarization_loss                       = 3;                #dBi
misalignment_attenuation_losses         = 0.5;              #dB
starlink_merit_figure                   = 9.2;              #dB/K
###
# file:///Users/mk0052/Downloads/FCC-05-63A1.pdf
# 10 dBW/4KHz, given channel bandwidth is 50 MHz
# Max EIRP = 50.9 dBw or 80.9 dBm
###
satellite_eirp                          = 80.9;
satellite_eirp_dbW                      = 50.9;

ground_station_tx_power                 = 36.08526;         #dBm -- https://apps.fcc.gov/els/GetAtt.html?id=259301
ground_station_receive_attenna_gain     = 33.2;             #dBi -- https://apps.fcc.gov/els/GetAtt.html?id=259301
ground_station_transmit_attenna_gain    = 34.6;             #dBi -- https://apps.fcc.gov/els/GetAtt.html?id=259301

def get_weather_info(lat, lon):
    url = "https://api.openweathermap.org/data/2.5/weather?lat=%s&lon=%s&appid=%s&units=standard" % (str(lat), str(lon), api_key)
    response = requests.get(url)
    data = response.json()
    if data != "":
        da = data["weather"]
        description =  da[0]["description"]
        general = data["main"]
        temp  = general["temp"]
        humidity = general["humidity"]
        pressure = general["pressure"]

    return {"temp": temp,
            "humidity": humidity,
            "pressure": pressure,
            "description": description
            }

def calc_gsl_snr(satellite, ground_station, t, distance, direction):
    gsl_distance = distance
    # distance_between_ground_station_satellite(ground_station, satellite, t);
    fspl = 20 * math.log10(gsl_distance/1000) + 20 * math.log10(channelFreq_sat_to_ground) + 92.45;

    lat_gs = float(ground_station["latitude_degrees_str"])
    lon_gs = float(ground_station["longitude_degrees_str"])

    f_dl = channelFreq_sat_to_ground * itur.u.GHz    # Link frequency
    f_ul = channelFreq_ground_to_sat * itur.u.GHz    # Link frequency
    D = 0.58 * itur.u.m                           # Size of the receiver antenna (this is the diamter of starlink dish v.1)
    el = 70                                       # Elevation angle constant of 60 degrees
    p = 0.01                                      # Percentage of time that attenuation values are exceeded.

    weather_data = get_weather_info(lat_gs, lon_gs)
    if weather_data != "":
        if "drizzle" in str(weather_data["description"]):
            r001 = 0.25
        elif "light rain" in str(weather_data["description"]):
            r001 = 2.5
        elif "moderate rain" in str(weather_data["description"]):
            r001 = 12.5
        elif str(weather_data["description"]) == "heavy rain":
            r001 = 25
        elif str(weather_data["description"]) == "very heavy rain" or str(weather_data["description"]) == "extreme rain":
            r001 = 50
        elif str(weather_data["description"]) == "heavy intensity shower rain" or str(weather_data["description"]) == "shower rain":
            r001 = 100
        elif str(weather_data["description"]) == "ragged shower rain":
            r001 = 150
        else:
            r001 = None

        temp = float(weather_data["temp"])	#temp in Kelvin
	#temp = temp + 273.15
        humidity = float(weather_data["humidity"])
        pressure = float(weather_data["pressure"])
        # print temp, humidity, pressure

        weather_attenuation_dl = itur.atmospheric_attenuation_slant_path(lat_gs, lon_gs, f_dl, el, p, D, R001=r001, T=temp, H=humidity, P=pressure)
        weather_attenuation_dl = weather_attenuation_dl.value

        weather_attenuation_ul = itur.atmospheric_attenuation_slant_path(lat_gs, lon_gs, f_ul, el, p, D, R001=r001, T=temp, H=humidity, P=pressure)
        weather_attenuation_ul = weather_attenuation_ul.value
        # print weather_attenuation
    else:
        print("no weather data -- ")
        weather_attenuation_dl = itur.atmospheric_attenuation_slant_path(lat_gs, lon_gs, f_dl, el, p, D, return_contributions=True)
        weather_attenuation_dl = weather_attenuation_dl.value
        weather_attenuation_ul = itur.atmospheric_attenuation_slant_path(lat_gs, lon_gs, f_ul, el, p, D, return_contributions=True)
        weather_attenuation_ul = weather_attenuation_ul.value


    if direction == "downlink":
        # rss_dBm = satellite_eirp - 2 + ground_station_receive_attenna_gain - fspl - polarization_loss - misalignment_attenuation_losses - weather_attenuation - 1.0;
        # rss_watt = pow(10,((rss_dBm - 30)/10));
        snr_db = satellite_eirp_dbW - (10*(math.log(channnel_bandwidth_downlink*pow(10,6))/math.log(10))) - fspl - polarization_loss - misalignment_attenuation_losses - weather_attenuation_dl - 3 + starlink_merit_figure+228.6
        # print fspl, snr_db, weather_attenuation
        snr = pow(10,(snr_db/10))
        return snr

    if direction == "uplink":
        rss_dBm = ground_station_tx_power + ground_station_transmit_attenna_gain + 10 - 2 - fspl - polarization_loss - misalignment_attenuation_losses - weather_attenuation_ul - 1.0;
        rss_watt = pow(10,((rss_dBm - 30)/10));
        # snr = pow(10,(snr_db/10))
        # return snr

    noise_watt = 200 * 1.38064852 * pow(10, -23) * 250*pow(10, 6);        #ktB channnel_bandwidth_downlink
    # print fspl, rss_dBm, rss_watt, noise_watt
    snr = rss_watt/noise_watt;
    return snr

def calc_gsl_snr_given_distance(gsl_distance):
    fspl = 20 * math.log10(gsl_distance/1000) + 20 * math.log10(channelFreq_sat_to_ground) + 92.45;

    rss_dBm = satellite_eirp - 2 + ground_station_receive_attenna_gain - fspl - polarization_loss - misalignment_attenuation_losses - 1.0;
    rss_watt = pow(10,((rss_dBm - 30)/10));

    noise_watt = 200 * 1.38064852 * pow(10, -23) * channnel_bandwidth_downlink*pow(10, 6);        #ktB
    snr = rss_watt/noise_watt;

    return snr

def calc_isl_throughput_given_distance(isl_distance):
    return 20
