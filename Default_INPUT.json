from fitparse import FitFile #conda install -c conda-forge python-fitparse 
import gpxpy #conda install -c conda-forge gpxpy 
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from math import pi,acos,sin,cos,atan2,nan,atan,exp,sqrt,fabs,copysign,isnan
from scipy.ndimage import gaussian_filter1d
import datetime
import folium #conda install -c conda-forge folium
import webbrowser
from scipy import fftpack
#from IPython import get_ipython
#from matplotlib.widgets import Slider
from bokeh.io import curdoc #conda install -c bokeh bokeh
from bokeh.layouts import row, column
from bokeh.models import ColumnDataSource
from bokeh.models.widgets import Slider, Button, TextInput
from bokeh.plotting import figure
#from tabulate import tabulate #pip install tabulate
from matplotlib.backends.backend_pdf import PdfPages
import os
import csv
from pathlib import Path
import json
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap, BoundaryNorm
import matplotlib.dates as mdates
# from openmeteo_py import Hourly,Daily,Options,OWmanager #pip install openmeteo-py==0.0.1
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
#import sys

#Konstnten und Sonstiges
g = 9.81
deg2rad = pi/180
#v_ave_liste=[]

def calc_rho_advanced(time):
    global time_new_Weather,AdvWeather_TempC,AdvWeather_AirSpeed,AdvWeather_AirDir,AdvWeather_AirMoisture,AdvWeather_AirPressure,AdvWeather_AirDensity,AdvWeather_ApparentT,AdvWeather_WindGusts,AdvWeather_Precipitation
    if time[-1]==0:
        time_new_Weather=0
        if not API_Weather: read_CSV_Weather_data(Wetterdatei)
        AdvWeather_TempC=[]
        AdvWeather_AirSpeed=[]
        AdvWeather_AirDir=[]
        AdvWeather_AirMoisture=[]
        AdvWeather_AirPressure=[]
        AdvWeather_AirDensity=[]
        AdvWeather_ApparentT=[]
        AdvWeather_WindGusts=[]
        AdvWeather_Precipitation=[]
    if not API_Weather:
        interpolate_CSV_Weather_data(time)     
    if API_Weather:
        if time[-1]>=time_new_Weather:
            i=len(time)-1
            Get_API_Data(lat2[i],lon2[i],API_StratTime)
            time_new_Weather+=1800
        interpolate_API_Weather_data(time,API_StratTime) 
    rho=AdvWeather_roh(AdvWeather_AirPressure[-1]*100,AdvWeather_TempC[-1]+273.15,AdvWeather_AirMoisture[-1]/100)
    AdvWeather_AirDensity.append(rho)
    return rho

# def Get_API_Data(latitude,longitude,StratTime):
#     global API_Data
#     hourly = Hourly()
#     daily = Daily()
# #    options = Options(latitude,longitude)
#     delta=datetime.datetime.today()-datetime.datetime.strptime(StratTime, '%Y-%m-%dT%H:%M')
#     Past_Days=max(min(delta.days+1,92),0)
#     options = Options(latitude, longitude,'iso8601', 'UTC', 'kmh' ,  'mm', False, Past_Days)
#     mgr = OWmanager(options,hourly.all(),daily.all())
#     API_Data = mgr.get_data() # Download data
# #    print(API_Data)

def Get_API_Data(latitude,longitude,StratTime):
    global hourly_data
    # print('START Get_API_Data')
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = 1)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)
    
    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    forecast_max=(datetime.datetime.today()+datetime.timedelta(days=15)).date()
    history_max=(datetime.datetime.today()-datetime.timedelta(days=92)).date()
    if datetime.datetime.strptime(StratTime, '%Y-%m-%dT%H:%M').date()>=history_max:
        API_Time=min(datetime.datetime.strptime(StratTime, '%Y-%m-%dT%H:%M').date(),forecast_max)
        url = "https://api.open-meteo.com/v1/forecast"
    else:
        API_Time= datetime.datetime.strptime(StratTime, '%Y-%m-%dT%H:%M').date() 
        url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
    params = {
    	"latitude": latitude,
    	"longitude": longitude,
    	"hourly": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation", "surface_pressure", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"],
    	# "past_days": 92,
    	# "forecast_days": 16
    	"start_date": str(API_Time),
    	"end_date": str(API_Time)     
    }
    responses = openmeteo.weather_api(url, params=params)
    
    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    
    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
    hourly_apparent_temperature = hourly.Variables(2).ValuesAsNumpy()
    hourly_precipitation = hourly.Variables(3).ValuesAsNumpy()
    hourly_surface_pressure = hourly.Variables(4).ValuesAsNumpy()
    hourly_wind_speed_10m = hourly.Variables(5).ValuesAsNumpy()
    hourly_wind_direction_10m = hourly.Variables(6).ValuesAsNumpy()
    hourly_wind_gusts_10m = hourly.Variables(7).ValuesAsNumpy()
    
    hourly_data = {"date": pd.date_range(
    	start = pd.to_datetime(hourly.Time()+response.UtcOffsetSeconds(), unit = "s", utc = False),
    	end = pd.to_datetime(hourly.TimeEnd()+response.UtcOffsetSeconds(), unit = "s", utc = False),
    	freq = pd.Timedelta(seconds = hourly.Interval()),
    	inclusive = "left"
    )}
    
    hourly_data["temperature_2m"] = hourly_temperature_2m
    hourly_data["relative_humidity_2m"] = hourly_relative_humidity_2m
    hourly_data["apparent_temperature"] = hourly_apparent_temperature
    hourly_data["precipitation"] = hourly_precipitation
    hourly_data["surface_pressure"] = hourly_surface_pressure
    hourly_data["wind_speed_10m"] = hourly_wind_speed_10m
    hourly_data["wind_direction_10m"] = hourly_wind_direction_10m
    hourly_data["wind_gusts_10m"] = hourly_wind_gusts_10m
    # print('END Get_API_Data')


def interpolate_API_Weather_data(time,StratTime): 
    global datetime_StartTime, i_API_Start
    t=time[-1]
    n=len(hourly_data['date'])
    if t==0:
        if datetime.datetime.strptime(StratTime, '%Y-%m-%dT%H:%M')<=hourly_data['date'][0]:
            datetime_StartTime=hourly_data['date'][12]
        elif datetime.datetime.strptime(StratTime, '%Y-%m-%dT%H:%M')>=hourly_data['date'][n-1]:
            datetime_StartTime=hourly_data['date'][n-12]
        else:
            datetime_StartTime=datetime.datetime.strptime(StratTime, '%Y-%m-%dT%H:%M')   
        i_API_Start=0
    datetime_CurrentTime = datetime_StartTime+datetime.timedelta(seconds=t)
    ii=-1
    tt=0
    for i in range(i_API_Start,n):
        datetime_API_Time=hourly_data['date'][i]
        if(ii==-1 and datetime_API_Time>datetime_CurrentTime):
            ii=i-1
            tt=datetime_API_Time-datetime_CurrentTime
            tt=3600-tt.total_seconds()
            # print('i,ii,i_API_Start,tt',i,ii,i_API_Start,tt)
            i_API_Start=ii
            break
    if(ii<0): 
        ii=n-2
        tt=3600
    AdvWeather_TempC_tmp=lin_interpolate(tt,0,3600,float(hourly_data['temperature_2m'][ii]),float(hourly_data['temperature_2m'][ii+1]))
    AdvWeather_AirSpeed_tmp=lin_interpolate(tt,0,3600,float(hourly_data['wind_speed_10m'][ii]),float(hourly_data['wind_speed_10m'][ii+1]))
    AdvWeather_AirDir_tmp=lin_interpolate(tt,0,3600,float(hourly_data['wind_direction_10m'][ii])+180,float(hourly_data['wind_direction_10m'][ii+1])+180)
    AdvWeather_AirMoisture_tmp=lin_interpolate(tt,0,3600,float(hourly_data['relative_humidity_2m'][ii]),float(hourly_data['relative_humidity_2m'][ii+1]))
    AdvWeather_AirPressure_tmp=lin_interpolate(tt,0,3600,float(hourly_data['surface_pressure'][ii]),float(hourly_data['surface_pressure'][ii+1]))
    #Zusätzliche Daten nur für API Wetter
    AdvWeather_ApparentT_tmp=lin_interpolate(tt,0,3600,float(hourly_data['apparent_temperature'][ii]),float(hourly_data['apparent_temperature'][ii+1]))    
    AdvWeather_WindGusts_tmp=lin_interpolate(tt,0,3600,float(hourly_data['wind_gusts_10m'][ii]),float(hourly_data['wind_gusts_10m'][ii+1]))    
    AdvWeather_Precipitation_tmp=lin_interpolate(tt,0,3600,float(hourly_data['precipitation'][ii]),float(hourly_data['precipitation'][ii+1]))    

    
    AdvWeather_TempC.append(AdvWeather_TempC_tmp)
    AdvWeather_AirSpeed.append(AdvWeather_AirSpeed_tmp)
    AdvWeather_AirDir.append(AdvWeather_AirDir_tmp)
    AdvWeather_AirMoisture.append(AdvWeather_AirMoisture_tmp)
    AdvWeather_AirPressure.append(AdvWeather_AirPressure_tmp)
    #Zusätzliche Daten nur für API Wetter
    AdvWeather_ApparentT.append(AdvWeather_ApparentT_tmp)
    AdvWeather_WindGusts.append(AdvWeather_WindGusts_tmp)
    AdvWeather_Precipitation.append(AdvWeather_Precipitation_tmp)
    
            
def interpolate_CSV_Weather_data(time):
    t=time[-1]
    n=len(AdvWeather_CSV_Data[:])
    for i in range(n):
        ti=60*float(AdvWeather_CSV_Data[i][0])
        if t>= ti:
            if i+1<n:
                ti1=60*float(AdvWeather_CSV_Data[i+1][0])           
                AdvWeather_TempC_tmp=lin_interpolate(t,ti,ti1,float(AdvWeather_CSV_Data[i][1]),float(AdvWeather_CSV_Data[i+1][1]))
                AdvWeather_AirSpeed_tmp=lin_interpolate(t,ti,ti1,float(AdvWeather_CSV_Data[i][2]),float(AdvWeather_CSV_Data[i+1][2]))
                AdvWeather_AirDir_tmp=lin_interpolate_degree(t,ti,ti1,float(AdvWeather_CSV_Data[i][3]),float(AdvWeather_CSV_Data[i+1][3]))
                AdvWeather_AirMoisture_tmp=lin_interpolate(t,ti,ti1,float(AdvWeather_CSV_Data[i][4]),float(AdvWeather_CSV_Data[i+1][4]))
                AdvWeather_AirPressure_tmp=lin_interpolate(t,ti,ti1,float(AdvWeather_CSV_Data[i][5]),float(AdvWeather_CSV_Data[i+1][5]))
            else:
                AdvWeather_TempC_tmp=float(AdvWeather_CSV_Data[i][1])
                AdvWeather_AirSpeed_tmp=float(AdvWeather_CSV_Data[i][2])
                AdvWeather_AirDir_tmp=float(AdvWeather_CSV_Data[i][3])
                AdvWeather_AirMoisture_tmp=float(AdvWeather_CSV_Data[i][4])
                AdvWeather_AirPressure_tmp=float(AdvWeather_CSV_Data[i][5])
    AdvWeather_TempC.append(AdvWeather_TempC_tmp)
    AdvWeather_AirSpeed.append(AdvWeather_AirSpeed_tmp)
    AdvWeather_AirDir.append(AdvWeather_AirDir_tmp)
    AdvWeather_AirMoisture.append(AdvWeather_AirMoisture_tmp)
    AdvWeather_AirPressure.append(AdvWeather_AirPressure_tmp)
            
    
def lin_interpolate(x,x0,x1,y0,y1):
    if x1 == x0:
        return y0
    y=y0+(y1-y0)/(x1-x0)*(x-x0)
    return y
 
def lin_interpolate_degree(x,x0,x1,y0,y1):
    dy=y1-y0
    if dy>180:dy=dy-360
    if dy<-180:dy=dy+360
    y=y0+dy/(x1-x0)*(x-x0)
    if y<0:y=y+360
    if y>=360: y=y-360
    return y

def read_CSV_Weather_data(Wetterdatei):
    global AdvWeather_CSV_Data
#    print('read_weather_data')
    AdvWeather_CSV_Data=[]
    i=0
    with open(Wetterdatei) as csvdatei:
        csv_reader_object = csv.reader(csvdatei)
        for row_csv in csv_reader_object:            
            i+=1
            if i>1:
                AdvWeather_CSV_Data.append(row_csv)

def AdvWeather_roh(p,T,phi):
    Rt=287.058
    Rd=461.523  
    psat = 611.2*np.exp((17.62)*(T-273.15)/(243.12+(T-273.15)))      
    Rf=Rt/(1-phi*psat/p*(1-Rt/Rd))
    rho= p/(Rf*T)
    return rho

def pdf_save(fig_list, file_name, path_name='./'):
    output_path = os.path.join(path_name, file_name)
    pp = PdfPages(output_path)
    for fig in fig_list:
        if fig != 0:
            pp.savefig(figure=fig, bbox_inches='tight', orientation='landscape')
    pp.close()
    print('PDF saved to %s' % output_path)
    return output_path

def dir_from_lat_lon(lat0,lat1,lon0,lon1):
        arg1=cos(lat0*deg2rad)*sin(lat1*deg2rad)-sin(lat0*deg2rad)*cos(lat1*deg2rad)*cos(lon1*deg2rad-lon0*deg2rad)
        arg2=sin(lon1*deg2rad-lon0*deg2rad)*cos(lat1*deg2rad)
        direction=atan2(arg2,arg1)       
        if direction<0:
            direction+=2*pi    
        return direction

def grade_from_height(height,position):
    grade=[nan]
    for i in range(1,len(height)):
        dh=height[i]-height[i-1]
        dp=(position[i]-position[i-1])*1000
        if dp!=0:
            gr=dh/dp*100
        else:
            gr=0
        grade.append(gr)
    return grade

def height_from_grade(grade,position,height0):
    height=[height0]
    for i in range(1,len(grade)):        
        gr=grade[i]/100
        dp=(position[i]-position[i-1])*1000
        dh=gr*dp
        h=height[i-1]+dh
        height.append(h)
    return height
    
def el_gain_from_height(height):
    ele_gain=0
    for i in range(1,len(height)):
        dh=height[i]-height[i-1]
        if dh>0:
            ele_gain+=dh
    return ele_gain

def moving_ave(array,n):
    if n>=1:
        array_ave=[]
        imax=len(array)
        nbefore=int(round(n/2,0))
        nafter=n-nbefore 
        for i in range(imax):
            i1=max(0,i-nbefore)
            i2=min(i+nafter,imax)
            val=np.average(array[i1:i2])
            array_ave.append(val)
    else:
        array_ave=np.array(array)
    return array_ave

def moving_ave2(array1,array2,n):
    array_ave=[]
    imax=len(array1)
    nbefore=int(round(n/2,0))
    nafter=n-nbefore
    for i in range(imax):
        i1=max(0,i-nbefore)
        i2=min(i+nafter,imax-1)
        denom = (array2[i2]-array2[i1])
        if denom == 0:
            val = 0
        else:
            val=(array1[i2]-array1[i1])/denom
        array_ave.append(val)
    return array_ave

def calc_cdA(grade,cdA_Hill_Grade,cdA_Hill,cdA_Flat,Draft_Save_Grade,Draft_Save):
    if grade > cdA_Hill_Grade:
        cdA = cdA_Hill
    else:
        cdA = cdA_Flat
        if grade > Draft_Save_Grade: cdA = cdA * (1 - Draft_Save/100)
#    if grade > Draft_Save_Grade and grade < cdA_Hill_Grade:
#        cdA = cdA * (1 - Draft_Save/100)
    return cdA

def calc_rho(T,h):
    p0 = 101325
    rho0 = 1.293
    rho=rho0 * 273.15 / (273.15 + T) * exp(-rho0 * g * h / p0)
    return rho

def FFT_Filter(x,y,cut_freq):
    n=len(x)
    dx=x[n-1]-x[0]
    delta=dx/(n-1)
    y_freq = fftpack.fftfreq(y.size, d=delta) 
    high_freq_fft = fftpack.fft(y)
    high_freq_fft[np.abs(y_freq) > cut_freq] = 0
    filtered_y = fftpack.ifft(high_freq_fft)
    return filtered_y.real

def Find_Index_Close(a,v): #Find the position p, where the value v has the closest distance to a value of array a
    p=0
    d2=(a[0]-v)**2
    for i in range(1,len(a)):
        if d2>(a[i]-v)**2:
            d2=(a[i]-v)**2
            p=i
    return p
    
#-----------------------------------------------------------------------------------------------------------------------------------------
def Run(Title,m_r_,m_b_,cdA_Hill_Grade_,cdA_Flat_,Draft_Save_Grade_,Draft_Save_,eta_,cr_dyn_,cr_,cdA_Hill_,FTP_,power_max_liste_,NP_Soll_,pol_a0_,pol_grade_max_,power_min_,pol_grade_min_,dir_w_,v_w0_,T_Luft_,GPX_File_,Hoehengewinn_Soll_,Steigung_max_min_,sigma_filter_,x_Achse_,Histogram_Anz_Teilungen_,Gaus_Filter_,moving_ave_filter_,Open_HTML_Map_,Show_km_Markers_,Show_Plots_in_Run_,Use_AdvWeather_,API_Weather_,API_StratTime_,Wetterdatei_,Winddamping_,Anmerkungen,Speed_Soll,Start_Distance_,End_Distance_):
    global power_max,m_sys,m_r,m_b
    global cdA_Hill_Grade,cdA_Flat,Draft_Save_Grade,Draft_Save,eta,cr_dyn,cr,cdA_Hill,FTP
    global power_max_liste,NP_Soll,pol_a0,pol_grade_max,power_min,pol_grade_min
    global dir_w,v_w0,T_Luft
    global GPX_File,Hoehendaten_Glaetten,Hoehengewinn_Soll,Steigung_max_min,Start_Distance,End_Distance
    global sigma_filter,x_Achse,Histogram_Anz_Teilungen,Gaus_Filter,moving_ave_filter,Open_HTML_Map,Show_km_Markers,Show_Plots_in_Run
    global Winddamping,Wetterdatei,Use_AdvWeather,API_Weather,API_StratTime
    global v_ave_liste,pol_a0_init,lat2,lon2
    #get_ipython().run_line_magic('matplotlib', 'inline')
    v_ave_liste=[]
    m_r = m_r_
    m_b = m_b_
    m_sys = m_r_ + m_b_
    cdA_Hill_Grade=cdA_Hill_Grade_
    cdA_Flat=cdA_Flat_
    Draft_Save_Grade=Draft_Save_Grade_
    Draft_Save=Draft_Save_
    eta=eta_
    cr_dyn=cr_dyn_
    cr=cr_
    cdA_Hill=cdA_Hill_
    FTP=FTP_    
    power_max_liste=power_max_liste_
    NP_Soll=NP_Soll_
    pol_a0=pol_a0_
    pol_grade_max=pol_grade_max_
    power_min=power_min_
    pol_grade_min=pol_grade_min_
    dir_w=dir_w_
    v_w0=v_w0_
    T_Luft=T_Luft_
    GPX_File=GPX_File_
    Hoehengewinn_Soll=Hoehengewinn_Soll_
    Start_Distance=Start_Distance_
    End_Distance=End_Distance_
    Steigung_max_min=Steigung_max_min_
    sigma_filter=sigma_filter_
    x_Achse=x_Achse_
    Histogram_Anz_Teilungen=Histogram_Anz_Teilungen_
    Gaus_Filter=Gaus_Filter_
    moving_ave_filter=moving_ave_filter_
    Open_HTML_Map=Open_HTML_Map_
    Show_km_Markers=Show_km_Markers_  
    Show_Plots_in_Run=Show_Plots_in_Run_
    Winddamping=Winddamping_
    Use_AdvWeather=Use_AdvWeather_
    API_Weather=API_Weather_
    API_StratTime=API_StratTime_
    Wetterdatei=Wetterdatei_
    pol_a0_init=pol_a0
    Title_Page(Title,Anmerkungen)
    plot_pre_sets(Speed_Soll)
    lat2,lon2=import_gpx_or_fit_file()
    smooth_height_data()
    if Use_GPX_Input:
        for i in range(len(power_max_liste)):
            power_max=power_max_liste[i]
            bike_power_calc(NP_Soll)
            print_statistics(i,True,False)
        i=np.argmax(v_ave_liste)    
        power_max=power_max_liste[i]
    else:
        i=0
        power_max=pol_a0+(pol_a0-power_min)
    bike_power_calc(NP_Soll)
    if not Use_GPX_Input and Speed_Soll>0:
        print('cdA entsprechend Soll Speed anpassen',Speed_Soll)
        n=len(pos)
        residuum_Speed=(pos[n-1]/t_cumm[n-1]*3600)-Speed_Soll
        while abs(residuum_Speed) > 0.01:
            f_cdA=((pos[n-1]/t_cumm[n-1]*3600)/Speed_Soll)**3
            cdA_Flat=f_cdA*cdA_Flat
            print('Start Iteration mit Speed = ',pos[n-1]/t_cumm[n-1]*3600,' und f_cdA = ',f_cdA)
            bike_power_calc(0)
            residuum_Speed=(pos[n-1]/t_cumm[n-1]*3600)-Speed_Soll
            print('Ende Iteration mit Speed = ',pos[n-1]/t_cumm[n-1]*3600,' und f_cdA = ',f_cdA)
    print_maps()
    print_statistics(i,False,True)
    time_in_power_zones()
    plot_diagrams(sigma_filter,x_Achse,Histogram_Anz_Teilungen)
    v_vs_P_var_grade()
    v_vs_grade_var_P()
    #time_in_power_zones()      
    print_statistics(i,False,True) 
    pdf_path = pdf_save([txt0,tab0,tab1,fig0,fig1,tab2,tab3,fig2,fig3,tab5,tab6,tab4,fig4,fig5,fig6,fig7,fig8,fig9,fig10,fig11,fig12,fig20,fig15,fig17,fig16,fig16b,fig13,fig14,fig18,fig19,fig21,fig22], Title+'.pdf')
    map_path = None
    try:
        map_path = GPX_File[0:GPX_File.rfind(".")] + '__GPS_Track.html'
    except Exception:
        map_path = None
    return {
        'pdf_path': pdf_path,
        'map_path': map_path,
        'title': Title,
        'distance_km': pos[-1] if 'pos' in globals() and len(pos) > 0 else None,
        'duration_s': t_cumm[-1] if 't_cumm' in globals() and len(t_cumm) > 0 else None,
        'average_speed_kmh': (pos[-1] / t_cumm[-1] * 3600) if 'pos' in globals() and 't_cumm' in globals() and len(pos) > 0 and len(t_cumm) > 0 and t_cumm[-1] not in (0, None) else None,
    }
    
def Title_Page(Title,Anmerkungen):
    global txt0
    txt0, ax = plt.subplots()
    ax.set_axis_off()
    plt.text(0.5, 1, 'Bike Power-Speed Calculator', ha='center', va='center', fontsize=14)
    plt.text(0.5, 0.5, Title, ha='center', va='center', fontsize=22, color='C1')   
    e = datetime.datetime.now()
    String='Berechnung vom %s/%s/%s %s:%s:%s'  % (str(e.day).zfill(2),str(e.month).zfill(2),str(e.year).zfill(4),str(e.hour).zfill(2),str(e.minute).zfill(2),str(e.second).zfill(2))
    plt.text(0.5, 0.4, String, ha='center', va='center', fontsize=10)  
    String='Anmerkungen: '+Anmerkungen
    max_Zeichen=120
    Leerzeichen_Liste=[i for i, char in enumerate(String) if char == ' ']
    i0=0
    j=0
    for i in range(1,len(Leerzeichen_Liste)):
        if Leerzeichen_Liste[i]-i0>max_Zeichen:
            i1=Leerzeichen_Liste[i-1]
            plt.text(0.5, 0.25-j*0.04,String[i0:i1], ha='center', va='center', fontsize=8)
            i0=i1+1
            j+=1
    plt.text(0.5, 0.25-j*0.04,String[i0:], ha='center', va='center', fontsize=8)      
    if Show_Plots_in_Run:
        plt.show()   
    else:
        plt.close()   
        
def plot_pre_sets(Speed_Soll):
    global tab0
    tab0, ax =plt.subplots()
    data=[['FTP',FTP],
          ['m_r',m_r],
          ['m_b',m_b],
          ['cr',cr],
          ['cdA_Flat,Speed_Soll',str(cdA_Flat)+','+str(Speed_Soll)],
          ['cdA_Hill',cdA_Hill],
          ['eta',eta],
          ['cdA_Hill_Grade',cdA_Hill_Grade],
          ['Draft_Save_Grade',Draft_Save_Grade],
          ['Draft_Save',Draft_Save],
          ['pol_a0',pol_a0],
          ['pol_grade_max',pol_grade_max],
          ['pol_grade_min',pol_grade_min],
          ['power_min',power_min],
          ['power_max_liste',power_max_liste],
          ['NP_Soll',NP_Soll],
          ['T_Luft',T_Luft],
          ['v_w0',v_w0],
          ['dir_w',dir_w],
          ['Winddamping',Winddamping],
          ['Use_AdvWeather,API_Weather,API_StratTime',str(Use_AdvWeather)+','+str(API_Weather)+','+str(API_StratTime)],
          ['Wetterdatei',Wetterdatei],
          ['GPX_File',GPX_File],
          ['Hoehengewinn_Soll,Start_Distance,End_Distance',str(Hoehengewinn_Soll)+','+str(Start_Distance)+','+str(End_Distance)],
          ['Steigung_max_min',Steigung_max_min],
          ['x_Achse',x_Achse],
          ['Gaus_Filter',Gaus_Filter],
          ['sigma_filter',sigma_filter],
          ['moving_ave_filter',moving_ave_filter],
          ['Histogram_Anz_Teilungen',Histogram_Anz_Teilungen],
          ['Open_HTML_Map',Open_HTML_Map],
          ['Show_km_Markers',Show_km_Markers],
          ['Show_Plots_in_Run',Show_Plots_in_Run]]    
    ax.axis('off')
    ax.set_title('Benutzervorgaben')
    the_table = ax.table(cellText=data,cellLoc='center',loc='upper left',colWidths=[0.25,0.75])
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(5)
    if Show_Plots_in_Run:
        plt.show()    
    else:
        plt.close()        
    

def v_vs_P_var_grade(): 
#    global cdA_Hill_Grade,Draft_Save_Grade,Draft_Save
    global fig13,fig14
#    cdA_Hill_Grade = 1
#    Draft_Save_Grade = -10
#    Draft_Save = 0    
#    print()
#    print('Geschwindigkeit als Funktion der Leistung für verschiedene Steigungen')
    v_list = [[] for i in range(21)]
    P_list = range(160,310,10)
    for i in range (21):
        grade_inp = i - 10
        #print(i,grade_inp)
        for P_inp in P_list:   
            h_inp = 50
            dir_inp = 0
            dir_w_inp = 0
            v_w0_inp = 0
            v_b = calc_v(P_inp,grade_inp,h_inp,dir_inp,dir_w_inp,v_w0_inp,True)*3.6 #/m/s --> km/h
            v_list[i].append(v_b)
    fig13, ax = plt.subplots()
    ax.set_title('Geschwindigkeit als Funktion der Leistung für verschiedene Steigungen')
    ax.set_xlabel('Leistung [W]')
    ax.set_ylabel('Geschwindigkeit [km/h]')
    ax.plot(P_list, v_list[10],'black',label='0%')    
    i1,i2 = 11,9
    color = 'blue'
    gr = '1'
    ax.plot(P_list, v_list[i1],color,label='+'+gr+'%')
    ax.plot(P_list, v_list[i2],color,linestyle='--',label='-'+gr+'%')
    v_mix=[(2*v1*v2)/(v1+v2) for v1,v2 in zip(v_list[i1],v_list[i2])]
    ax.plot(P_list, v_mix,color,linestyle='-.',label='+-'+gr+'%')    
    i1,i2 = 12,8
    color = 'red'
    gr = '2'
    ax.plot(P_list, v_list[i1],color,label='+'+gr+'%')
    ax.plot(P_list, v_list[i2],color,linestyle='--',label='-'+gr+'%')
    v_mix=[(2*v1*v2)/(v1+v2) for v1,v2 in zip(v_list[i1],v_list[i2])]
    ax.plot(P_list, v_mix,color,linestyle='-.',label='+-'+gr+'%')    
    i1,i2 = 14,6
    color = 'orange'
    gr = '4'
    ax.plot(P_list, v_list[i1],color,label='+'+gr+'%')
    ax.plot(P_list, v_list[i2],color,linestyle='--',label='-'+gr+'%')
    v_mix=[(2*v1*v2)/(v1+v2) for v1,v2 in zip(v_list[i1],v_list[i2])]
    ax.plot(P_list, v_mix,color,linestyle='-.',label='+-'+gr+'%')    
    i1,i2 = 16,4
    color = 'green'
    gr = '6'
    ax.plot(P_list, v_list[i1],color,label='+'+gr+'%')
    ax.plot(P_list, v_list[i2],color,linestyle='--',label='-'+gr+'%')
    v_mix=[(2*v1*v2)/(v1+v2) for v1,v2 in zip(v_list[i1],v_list[i2])]
    ax.plot(P_list, v_mix,color,linestyle='-.',label='+-'+gr+'%')    
    i1,i2 = 18,2
    color = 'purple'
    gr = '8'
    ax.plot(P_list, v_list[i1],color,label='+'+gr+'%')
    ax.plot(P_list, v_list[i2],color,linestyle='--',label='-'+gr+'%')
    v_mix=[(2*v1*v2)/(v1+v2) for v1,v2 in zip(v_list[i1],v_list[i2])]
    ax.plot(P_list, v_mix,color,linestyle='-.',label='+-'+gr+'%')    
    i1,i2 = 20,0
    color = 'pink'
    gr = '10'
    ax.plot(P_list, v_list[i1],color,label='+'+gr+'%')
    ax.plot(P_list, v_list[i2],color,linestyle='--',label='-'+gr+'%')
    v_mix=[(2*v1*v2)/(v1+v2) for v1,v2 in zip(v_list[i1],v_list[i2])]
    ax.plot(P_list, v_mix,color,linestyle='-.',label='+-'+gr+'%')
    ax.grid()
    ax.legend(loc='upper left')
    if Show_Plots_in_Run:
        plt.show()      
    else:
        plt.close()          

#    print()
#    print('Geschwindigkeit bei Steigung bergauf und bergab bezogen auf 0% Steigung als Funktion der Leistung')
    fig14, ax = plt.subplots()
    ax.set_title('Geschwindigkeit bei Steigung bergauf und bergab bezogen auf 0% Steigung als Funktion der Leistung')
    ax.set_xlabel('Leistung [W]')
    ax.set_ylabel('Relative Geschwindigkeit [%]')    
    i1,i2 = 11,9
    color = 'blue'
    gr = '1'
    v_mix=[100*((2*v1*v2)/(v1+v2))/v0 for v1,v2,v0 in zip(v_list[i1],v_list[i2],v_list[10])]
    ax.plot(P_list, v_mix,color,linestyle='-.',label=gr+'%')
    i1,i2 = 12,8
    color = 'red'
    gr = '2'
    v_mix=[100*((2*v1*v2)/(v1+v2))/v0 for v1,v2,v0 in zip(v_list[i1],v_list[i2],v_list[10])]
    ax.plot(P_list, v_mix,color,linestyle='-.',label=gr+'%')
    i1,i2 = 14,6
    color = 'orange'
    gr = '4'
    v_mix=[100*((2*v1*v2)/(v1+v2))/v0 for v1,v2,v0 in zip(v_list[i1],v_list[i2],v_list[10])]
    ax.plot(P_list, v_mix,color,linestyle='-.',label=gr+'%') 
    i1,i2 = 16,4
    color = 'green'
    gr = '6'
    v_mix=[100*((2*v1*v2)/(v1+v2))/v0 for v1,v2,v0 in zip(v_list[i1],v_list[i2],v_list[10])]
    ax.plot(P_list, v_mix,color,linestyle='-.',label=gr+'%')
    i1,i2 = 18,2
    color = 'purple'
    gr = '8'
    v_mix=[100*((2*v1*v2)/(v1+v2))/v0 for v1,v2,v0 in zip(v_list[i1],v_list[i2],v_list[10])]
    ax.plot(P_list, v_mix,color,linestyle='-.',label=gr+'%')
    i1,i2 = 20,0
    color = 'pink'
    gr = '10'
    v_mix=[100*((2*v1*v2)/(v1+v2))/v0 for v1,v2,v0 in zip(v_list[i1],v_list[i2],v_list[10])]
    ax.plot(P_list, v_mix,color,linestyle='-.',label=gr+'%')
    ax.grid()
    ax.legend(loc='upper left')
    if Show_Plots_in_Run:
        plt.show()        
    else:
        plt.close()  

def v_vs_grade_var_P(): 
    global fig18,fig19
    fig18, ax = plt.subplots()
    ax.set_title('Geschwindigkeit als Funktion der Steigung für verschiedene Leisungen')
    ax.set_xlabel('Steigung [%]')
    ax.set_ylabel('Geschwindigkeit [km/h]')
    fig19, ax2 = plt.subplots()
    ax2.set_title('Relative Geschwindigkeit als Funktion der Steigung für verschiedene Leisungen')
    ax2.set_xlabel('Steigung [%]')
    ax2.set_ylabel('Geschwindigkeit/Geschw.(Steig.=0) [%]')
    grade_list = range(-30,31,1)
    for i in range (5):
        v_list=[]
        P_inp = 200+i*25
        grade_inp=0
        h_inp = 50
        dir_inp = 0
        dir_w_inp = 0
        v_w0_inp = 0
        v_b0 = calc_v(P_inp,grade_inp,h_inp,dir_inp,dir_w_inp,v_w0_inp,True)*3.6 #/m/s --> km/h
        #print(i,grade_inp)
        for grade_inp in grade_list:  
            v_b = calc_v(P_inp,grade_inp,h_inp,dir_inp,dir_w_inp,v_w0_inp,True)*3.6 #/m/s --> km/h
            v_list.append(v_b)
        ax.plot(grade_list, v_list,label='P= '+str(P_inp)+' W')
        ax2.plot(grade_list, np.array(v_list)/v_b0*100,label='P= '+str(P_inp)+' W')
    ax.grid()
    ax.legend(loc='upper center',bbox_to_anchor=(0.5, -0.1),ncol=5)
    ax2.grid()
    ax2.legend(loc='upper center',bbox_to_anchor=(0.5, -0.1),ncol=5)
    if Show_Plots_in_Run:
        plt.show()
        plt.show()            
    else:
        plt.close()
        plt.close()        

def print_maps():
    global fig0
    #Karte plotten    
    fig0, ax = plt.subplots()
    ax.set_title('Strecke erstellt aus den eingelesenen GPS Daten')
    ax.set_aspect('equal')
    ax.set_axis_off()
#    ax.plot(lon2, lat2,color='blue')
    points = np.array([lon2, lat2]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    n_val = 40
    min_val=np.min(h)
    max_val=np.max(h)
    val_list=[min_val+i/n_val*(max_val-min_val) for i in range(n_val+1)]
    colors = plt.cm.jet(np.linspace(0,1,n_val))
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(val_list, cmap.N)
    lc = LineCollection(segments, cmap=cmap, norm=norm)
    lc.set_array(np.array(h))
    lc.set_linewidth(2)
    line = ax.add_collection(lc)
    fig0.colorbar(line, shrink=0.5, label='Höhe [m]')
    if Show_km_Markers>0:
        ax.quiver(lon2[1],lat2[1],sin(direction[1]*deg2rad),cos(direction[1]*deg2rad),color='green',pivot='mid')      
        ax.quiver(lon2[-1],lat2[-1],sin(direction[-1]*deg2rad),cos(direction[-1]*deg2rad),color='red',pivot='mid')    
        km_value=Show_km_Markers
        km_value2=0.5*Show_km_Markers
        FirstCall1=FirstCall2=True
        for i in range(len(pos)-1):
            if pos[i]-km_value>0:
                ax.annotate(str(round(pos[i],2)),xy=(lon2[i],lat2[i]),xycoords='data',color='blue')
                if FirstCall1:
                    ax.quiver(lon2[i],lat2[i],sin(direction[i]*deg2rad),cos(direction[i]*deg2rad),color='blue',pivot='mid',label='Fahrtrichtung und km')
                    FirstCall1=False
                else:
                    ax.quiver(lon2[i],lat2[i],sin(direction[i]*deg2rad),cos(direction[i]*deg2rad),color='blue',pivot='mid')
                km_value+=Show_km_Markers
            if pos[i]-km_value2>0 and Use_AdvWeather:
                ax.annotate(str(round(Winddamping*AdvWeather_AirSpeed[i],2)),xy=(lon2[i],lat2[i]),xycoords='data',color='orange')
                if FirstCall2:
                    ax.quiver(lon2[i],lat2[i],sin(AdvWeather_AirDir[i]*deg2rad),cos(AdvWeather_AirDir[i]*deg2rad),color='orange',pivot='mid',label='Windrichtung und -geschwindigkeit')
                    FirstCall2=False
                else:
                    ax.quiver(lon2[i],lat2[i],sin(AdvWeather_AirDir[i]*deg2rad),cos(AdvWeather_AirDir[i]*deg2rad),color='orange',pivot='mid')
                km_value2+=Show_km_Markers
    ax.legend(loc='upper center',bbox_to_anchor=(0.5, -0.01),ncol=2,fontsize=6)
    if Show_Plots_in_Run:
        plt.show()       
    else:
        plt.close()     
    
    #Karte plotten 2 
    lat_lon=[]
    for i in range(len(lat2)):
        lat_lon.append(tuple([lat2[i], lon2[i]]))
    mymap = folium.Map( location=[np.mean(lat2), np.mean(lon2)], zoom_start=14)
    folium.PolyLine(lat_lon, color="red", weight=3.5, opacity=1).add_to(mymap)
    if Show_km_Markers>0:
        folium.Marker(location=[lat2[0],lon2[0]],icon=folium.DivIcon(html=f"""<div style="font-size:20pt;font-weight: bold;">{0}</div>""")).add_to(mymap)
        folium.Marker(location=[lat2[0],lon2[0]]).add_to(mymap)
        km_value=Show_km_Markers
        for i in range(len(pos)):
            if pos[i]-km_value>0:
                folium.Marker(location=[lat2[i],lon2[i]],icon=folium.DivIcon(html=f"""<div style="font-size:20pt;font-weight: bold;">{round(pos[i],1)}</div>""")).add_to(mymap)
                folium.Marker(location=[lat2[i],lon2[i]]).add_to(mymap)
                km_value+=Show_km_Markers
    Map_Name=GPX_File[0:GPX_File.rfind(".")] + '__GPS_Track.html'
    mymap.save(Map_Name)
    if Open_HTML_Map:
        print('HTML map saved to %s' % Map_Name)

def import_gpx_or_fit_file():
    global Use_GPX_Input
    i=GPX_File.rfind('.')
    ext=GPX_File[i+1:]
    if ext=='gpx':
        Use_GPX_Input=True
        lat2,lon2=import_gpx_file()
    else:
        Use_GPX_Input=False
        lat2,lon2=import_fit_file()
    return lat2,lon2
        
def import_fit_file():
    global h_raw,pos,direction,Power_fit
    
    #TMP Einschränkung der Distanz
    d_start=1000*Start_Distance
    d_end=1000*End_Distance
    
    fitfile = FitFile(GPX_File)
    elevation=[]
    distance=[]
    power=[]
    lat=[]
    lon=[]
    
#Beispiel für einen Eintrag in record_data     
#accumulated_power: 1741325 [watts]
#altitude: 3026
#cadence: 0 [rpm]
#distance: 83531.68 [m]
#enhanced_altitude: 105.20000000000005 [m]
#enhanced_speed: 6.252 [m/s]
#fractional_cadence: 0.0 [rpm]
#heart_rate: 131 [bpm]
#left_pedal_smoothness: None [percent]
#left_right_balance: 228
#left_torque_effectiveness: None [percent]
#position_lat: 613721705 [semicircles]
#position_long: 84022794 [semicircles]
#power: 0 [watts]
#right_pedal_smoothness: None [percent]
#right_torque_effectiveness: None [percent]
#speed: 6252
#temperature: 10 [C]
#timestamp: 2022-02-27 13:54:28
#unknown_61: 3015
#unknown_66: 2420
#unknown_90: -2
    
    for record in fitfile.get_messages('record'):
        check_sum=0
        for record_data in record:
            if(record_data.name=='enhanced_altitude'):
                if isinstance(record_data.value, float) or isinstance(record_data.value, int):
                    ele=record_data.value #m
                    check_sum+=1
            if(record_data.name=='distance'):
                if isinstance(record_data.value, float) or isinstance(record_data.value, int):
                    d=record_data.value #m
                    if (d>=d_start): check_sum+=1
            if(record_data.name=='power'):
                if isinstance(record_data.value, float) or isinstance(record_data.value, int): 
                    p=float(record_data.value)     #W
                    check_sum+=1
            if(record_data.name=='position_lat'):
                if isinstance(record_data.value, float) or isinstance(record_data.value, int):                  
                    la=record_data.value *180/(2**31 ) #semicercles to deg
                    check_sum+=1
            if(record_data.name=='position_long'):
                if isinstance(record_data.value, float) or isinstance(record_data.value, int): 
                    lo=record_data.value *180/(2**31 ) #semicercles to deg
                    check_sum+=1
        if check_sum==5:
            distance.append(d)  
            elevation.append(ele)
            power.append(p)
            lat.append(la)
            lon.append(lo)   
    
    d0=distance[0]
    pos=[0]
    h_raw=[elevation[0]]
    Power_fit=[max(10,power[0])]
    lat2=[lat[0]]
    lon2=[lon[0]]
    for i in range(1,len(distance)):
        #Verhindert, dass Abstand zwischen zwei Punkten sehr klein wird und somit sehr große Gradienten auftreten können
        if ((distance[i]-distance[i-1])>5) and (distance[i]<=d_end):
            pos.append((distance[i]-d0)/1000)
            h_raw.append(elevation[i])
            Power_fit.append(max(10,power[i]))
            lat2.append(lat[i])
            lon2.append(lon[i])
    
    direction = [nan]
    n=len(lat2)-1
    for i in range(1,n):
        direction.append(dir_from_lat_lon(lat2[i],lat2[i+1],lon2[i],lon2[i+1])/deg2rad)
    direction.append(dir_from_lat_lon(lat2[n-1],lat2[n],lon2[n-1],lon2[n])/deg2rad)
    # print_maps()
    return lat2,lon2

def import_gpx_file():
    global h_raw,pos,direction
    #GPX Datei importieren
    gpx_file = open(GPX_File, 'r')
    gpx = gpxpy.parse(gpx_file)
    lat = []
    lon = []
    ele = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                lat.append(point.latitude)
                lon.append(point.longitude)
                ele.append(point.elevation)                     

    #Daten aufbereiten
    pos = [0]
    direction = [nan]
    h_raw =[ele[0]]
    lat0=lat[0]
    lon0=lon[0]
    pos0=pos[0]
    lat2=[lat0]
    lon2=[lon0]
    for i in range(1,len(lat)):
        d = acos(min(sin(lat[i]*deg2rad) * sin(lat0*deg2rad) + cos(lat[i]*deg2rad) * cos(lat0*deg2rad) * cos(lon[i]*deg2rad - lon0*deg2rad),1))*6371000
        if d>=5:
            pos0=pos0+d/1000
            pos.append(pos0)
            lat2.append(lat[i])
            lon2.append(lon[i])
            h_raw.append(ele[i])       
            lat0=lat[i]
            lon0=lon[i]
    n=len(lat2)-1
    for i in range(1,n):
        direction.append(dir_from_lat_lon(lat2[i],lat2[i+1],lon2[i],lon2[i+1])/deg2rad)
    direction.append(dir_from_lat_lon(lat2[n-1],lat2[n],lon2[n-1],lon2[n])/deg2rad)
    # print_maps()
    return lat2,lon2
    
def liear_interpolate_between(x,y):
    n=len(x)-1
    if n <= 0 or x[n] == x[0]:
        return 0, list(y)
    gradient=(y[n]-y[0])/((x[n]-x[0]))
    y_new=[y[0]]
    for i in range(1,n+1):
        y_new.append(y_new[i-1]+gradient*(x[i]-x[i-1]))
    return gradient*100,y_new

def smooth_height_data():
    global h,fig1
    ele_gain_raw=el_gain_from_height(h_raw)
    grade_raw=grade_from_height(h_raw,pos)
    grade=grade_from_height(h_raw,pos)
    h=np.array(h_raw)
    ele_gain=el_gain_from_height(h)
                    
    n_smooth=0
    if Hoehengewinn_Soll > 0 and ele_gain > Hoehengewinn_Soll:
        residuum=ele_gain_raw-Hoehengewinn_Soll   
        print('n_smooth, ele_gain',n_smooth, ele_gain)         
        while residuum>0:
            n_smooth+=1
            h=moving_ave(h_raw,n_smooth)
            ele_gain=el_gain_from_height(h)
            grade=grade_from_height(h,pos)
            residuum_prev=residuum
            residuum=ele_gain-Hoehengewinn_Soll
            print('n_smooth, ele_gain',n_smooth, ele_gain)
        if abs(residuum)>abs(residuum_prev): n_smooth-=1
        h=moving_ave(h_raw,n_smooth)
        ele_gain=el_gain_from_height(h)
        grade=grade_from_height(h,pos)
        print('FINAL: n_smooth, ele_gain',n_smooth, ele_gain)
        
    if Hoehengewinn_Soll > 0 and Hoehengewinn_Soll > ele_gain:
        h0=h[0]
        fh=Hoehengewinn_Soll/ele_gain
        n=len(h)
        for i in range(1,n):
            h_new=h0+fh*(h[i]-h0)
            h[i]=h_new
        ele_gain=el_gain_from_height(h)
        grade=grade_from_height(h,pos)                 

    n=len(grade)
    for i in range(1,n-1):
        gr=grade[i]
        if abs(gr)>Steigung_max_min:
            gr_iter=gr
            iter=1
            while abs(gr_iter) > Steigung_max_min:
                i0=max(0,i-iter)
                i1=min(n,i+iter)
                gr_iter,h_new=liear_interpolate_between(np.array(pos[i0:i1])*1000,h[i0:i1])
                h[i0:i1]=np.array(h_new)
                iter+=1
    grade=grade_from_height(h,pos)  

    n=len(grade_raw)
    dydx=np.array(grade)
    dydx[0]=0
    fig1, ax = plt.subplots()       
    ax.set_title('Höhenprofil, ungefiltert (schwarz) und gefiltert')
    ax.plot(pos,h_raw,'black')
#    ax.plot(pos,h,'red')
    points = np.array([pos, h]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    n_val = 40
    min_val=np.min(dydx)
    max_val=np.max(dydx)
    val_list=[min_val+i/n_val*(max_val-min_val) for i in range(n_val+1)]
    colors = plt.cm.jet(np.linspace(0,1,n_val))
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(val_list, cmap.N)
    lc = LineCollection(segments, cmap=cmap, norm=norm)
    lc.set_array(np.array(dydx))
    lc.set_linewidth(6)
    line = ax.add_collection(lc)
    fig1.colorbar(line, shrink=0.5, label='Steigung [%]')
    ax.set_xlabel('Distanz [km]')
    ax.set_ylabel('Höhe [m]')
    ax.grid()
    data=[['Höhengewinn [m]',round(ele_gain_raw,2),round(ele_gain,2)],
          ['max. Steigung [m]',round(np.max(grade_raw[1:n]),2),round(np.max(grade[1:n]),2)],
          ['min. Steigung [m]',round(np.min(grade_raw[1:n]),2),round(np.min(grade[1:n]),2)]]
    column_labels=['', 'ungefiltert', 'gefiltert']
    ax.table(cellText=data,colLabels=column_labels,cellLoc='center',loc='bottom',bbox=[0, -0.33, 0.9, 0.2])
    if Show_Plots_in_Run:
        plt.show()     
    else:
        plt.close()        
        
def bike_power_main_calc(Power_fit_Input):
    global t,power,tP4,t_cumm,grade,v,P_r_rel,P_g_rel,P_l_rel,NP,AP,P_ges,P_Save,cdA_List
    #Berechnungen durchführen
    grade = [nan]
    power = [nan]
    v = [nan]
    t = [nan]
    t_cumm = [0]
    tP4 = [nan]
    tP = [nan]
    P_r_rel =[nan]      
    P_g_rel =[nan]      
    P_l_rel =[nan]      
    P_ges = [nan]
    P_Save =[nan] 
    cdA_List=[nan] 
    for i in range(1,len(pos)):     
        grade_tmp=h[i]-h[i-1]
        if grade_tmp!=0:
            grade_tmp=grade_tmp/((pos[i]-pos[i-1])*1000)*100    
        if grade_tmp>0:
            pol_a1=pol_a1p
        else:
            pol_a1=pol_a1m    
        power_tmp=pol_a0+pol_a1*grade_tmp        
        power_tmp=min(max(power_tmp,power_min),power_max)    
        if not Use_GPX_Input: power_tmp=Power_fit_Input[i]
        h_mean=0.5*(h[i]+h[i-1])
        v_b = calc_v(power_tmp,grade_tmp,h_mean,direction[i],dir_w,v_w0,False) #/m/s
        t_tmp = ((pos[i]-pos[i-1])*1000) / v_b
        t_cumm.append(t_cumm[i-1]+t_tmp) 
        #vmean_cumm = pos[i] / (t_cumm[i]/3600)
        P_r_dyn = f_r_dyn*v_b**2
        P_r = f_r * v_b
        P_g = max(0, (f_g * v_b))
        P_l = 100/eta * 0.5 * cdA * rho * (v_b + v_w)**2 * v_b
        P_ges_tmp = P_r_dyn + P_r + P_g + P_l
        tP4_tmp = t_tmp * power_tmp**4
        tP_tmp = t_tmp * power_tmp
        if grade_tmp > cdA_Hill_Grade:
            P_Save_tmp = (cdA_Hill - cdA) * (100/eta * 0.5 * rho * (v_b + v_w)**2 * v_b)
        else:
            P_Save_tmp = (cdA_Flat - cdA) * (100/eta * 0.5 * rho * (v_b + v_w)**2 * v_b)
        #übrige Arrays erstellen
        grade.append(grade_tmp)
        power.append(power_tmp)
        v.append(v_b* 3.6) #km/h   
        t.append(t_tmp)
        tP4.append(tP4_tmp)
        tP.append(tP_tmp)
        P_r_rel.append(P_r/P_ges_tmp*100)
        P_g_rel.append(P_g/P_ges_tmp*100) 
        P_l_rel.append(P_l/P_ges_tmp*100) 
        P_ges.append(P_ges_tmp)
        P_Save.append(P_Save_tmp) 
        n=len(t)
        NP=(np.sum(tP4[1:n])/np.sum(t[1:n]))**0.25
        AP=(np.sum(tP[1:n])/np.sum(t[1:n]))

def bike_power_calc(NP_Soll):
    if Use_GPX_Input:
        bike_power_calc_GPX(NP_Soll)
    else:
        bike_power_calc_FIT(NP_Soll)

def Get_Init_Parameter_File_gpx(file):
    with open(file, 'r') as f:
        input_dict = json.load(f)
    f_NP_Soll_=input_dict['f_NP_Soll_gpx']
    return f_NP_Soll_
    
def Create_Init_Parameter_File_gpx(file,f_NP_Soll_):
    data = {}
    data['f_NP_Soll_gpx'] = f_NP_Soll_
    with open(file, 'w') as f:
        json.dump(data, f)   
        
def bike_power_calc_GPX(NP_Soll):
    global pol_a1p,pol_a1m,pol_a0
    if NP_Soll<0:
        pol_a1p = (power_max-pol_a0)/pol_grade_max
        pol_a1m = (power_min-pol_a0)/pol_grade_min
        bike_power_main_calc([])
    else:
        Init_Parameter_File_gpx=GPX_File[0:GPX_File.rfind("/")]+'/Initial_Parameter_gpx.j'
        if Path(Init_Parameter_File_gpx).is_file():
            f_NP_Soll=Get_Init_Parameter_File_gpx(Init_Parameter_File_gpx)     
            # print('NP Iteration mit Strartwerten f_NP_Soll = ',f_NP_Soll)
        else:            
            f_NP_Soll=1    
        pol_a0 = pol_a0_init*f_NP_Soll
        pol_a1p = (power_max-pol_a0)/pol_grade_max
        pol_a1m = (power_min-pol_a0)/pol_grade_min            
        bike_power_main_calc([])
        residuum=NP-NP_Soll        
        while abs(residuum)>0.05:    
            f_NP_Soll=f_NP_Soll*NP_Soll/NP
            print('Start NP Iteration mit NP = ',NP,' und f_NP_Soll = ',f_NP_Soll)
            pol_a0 = pol_a0_init*f_NP_Soll
            pol_a1p = (power_max-pol_a0)/pol_grade_max
            pol_a1m = (power_min-pol_a0)/pol_grade_min            
            bike_power_main_calc([])
            print('Ende NP Iteration mit NP = ',NP,' und f_NP_Soll = ',f_NP_Soll)
            residuum=NP-NP_Soll
        Create_Init_Parameter_File_gpx(Init_Parameter_File_gpx,f_NP_Soll)
        
def Get_Init_Parameter_File_fit(file):
    with open(file, 'r') as f:
        input_dict = json.load(f)
    n_moving_ave_AP_fit_=input_dict['n_moving_ave_AP_fit']
    f_NP_Soll_=input_dict['f_NP_Soll_fit']
    return n_moving_ave_AP_fit_,f_NP_Soll_
    
def Create_Init_Parameter_File_fit(file,n_moving_ave_AP_fit_,f_NP_Soll_):
    data = {}
    data['n_moving_ave_AP_fit'] = n_moving_ave_AP_fit_
    data['f_NP_Soll_fit'] = f_NP_Soll_
    with open(file, 'w') as f:
        json.dump(data, f)        

def bike_power_calc_FIT(NP_Soll):
    global pol_a1p,pol_a1m,pol_a0,n_moving_ave_AP_fit,f_NP_Soll
    pol_a1p = (power_max-pol_a0)/pol_grade_max
    pol_a1m = (power_min-pol_a0)/pol_grade_min
    if NP_Soll<0:
        Power_fit_Input=Power_fit
        bike_power_main_calc(Power_fit_Input)        
    elif NP_Soll==0:
#        print('Erneuter Aufruf ohne NP & AP Iteration mit n_moving_ave_AP_fit =',n_moving_ave_AP_fit,' und f_NP_Soll = ',f_NP_Soll)
        Power_fit_Input=np.array(moving_ave(Power_fit,n_moving_ave_AP_fit))*f_NP_Soll
        bike_power_main_calc(Power_fit_Input)
    else:
        Init_Parameter_File_fit=GPX_File[0:GPX_File.rfind("/")]+'/Initial_Parameter_fit.j'
        if Path(Init_Parameter_File_fit).is_file():
            n_moving_ave_AP_fit,f_NP_Soll=Get_Init_Parameter_File_fit(Init_Parameter_File_fit)
        else:
            Power_fit_Input=Power_fit
            n_moving_ave_AP_fit=0
            AP_approx=0
            NP_approx=0
            for i in range(1,len(Power_fit_Input)):
                Pi=Power_fit_Input[i]
                AP_approx+=Pi
                NP_approx+=Pi**4
            AP_approx=AP_approx/i
            NP_approx=(NP_approx/i)**0.25
            err2_min=(AP_approx/NP_approx-pol_a0/NP_Soll)**2
            n_moving_ave_AP_fit_err2_min=n_moving_ave_AP_fit
        #    print(AP_approx,NP_approx,AP_approx/NP_approx,pol_a0/NP_Soll,err2_min,n_moving_ave_AP_fit)
            while n_moving_ave_AP_fit<80:
                n_moving_ave_AP_fit+=1
                Power_fit_Input=moving_ave(Power_fit,n_moving_ave_AP_fit)    
                AP_approx=0
                NP_approx=0
                for i in range(1,len(Power_fit_Input)):
                    Pi=Power_fit_Input[i]
                    AP_approx+=Pi
                    NP_approx+=Pi**4
                AP_approx=AP_approx/i
                NP_approx=(NP_approx/i)**0.25  
                err2=(AP_approx/NP_approx-pol_a0/NP_Soll)**2
                if err2<err2_min:
                    err2_min=err2
                    n_moving_ave_AP_fit_err2_min=n_moving_ave_AP_fit
        #        print(AP_approx,NP_approx,AP_approx/NP_approx,pol_a0/NP_Soll,err2,n_moving_ave_AP_fit)
            n_moving_ave_AP_fit=max(0,n_moving_ave_AP_fit_err2_min-1)
            f_NP_Soll=1
        print('Start NP & AP Iteration mit n_moving_ave_AP_fit = ',n_moving_ave_AP_fit,' und f_NP_Soll = ',f_NP_Soll)
        Power_fit_Input=np.array(moving_ave(Power_fit,n_moving_ave_AP_fit))*f_NP_Soll
        bike_power_main_calc(Power_fit_Input)
        residuum=NP-NP_Soll
        residuumAP=AP-pol_a0
        while abs(residuum)>0.1 or abs(residuumAP)>0.5:
            f_NP_Soll=f_NP_Soll*NP_Soll/NP
            Power_fit_Input=np.array(moving_ave(Power_fit,n_moving_ave_AP_fit))*f_NP_Soll
            print('vor Iteration Anpassen NP & AP',NP,AP,n_moving_ave_AP_fit)
            bike_power_main_calc(Power_fit_Input)
            print('nach Iteration Anpassen NP & AP',NP,AP,n_moving_ave_AP_fit)
            residuum=NP-NP_Soll
            if abs(residuum)<=0.1:
                residuumAP=AP-pol_a0
                if abs(residuumAP)>0.5:
                    if residuumAP>0:
                        n_moving_ave_AP_fit=max(0,n_moving_ave_AP_fit-1)
                        if n_moving_ave_AP_fit==0: residuumAP=0
                    else:
                        n_moving_ave_AP_fit+=4
        print('Ende NP & AP Iteration mit n_moving_ave_AP_fit =',n_moving_ave_AP_fit,' und f_NP_Soll = ',f_NP_Soll)
        Create_Init_Parameter_File_fit(Init_Parameter_File_fit,n_moving_ave_AP_fit,f_NP_Soll)  
            
def calc_v(power_tmp,grade_tmp,h_mean,direction_tmp,dir_w,v_w0,ResetStandardWeather):
    global f_r_dyn,f_r,f_g,cdA,rho,v_w
    v_w0_0=v_w0
    dir_w_0=dir_w    
    beta = atan(grade_tmp/100)
    cdA=calc_cdA(grade_tmp,cdA_Hill_Grade,cdA_Hill,cdA_Flat,Draft_Save_Grade,Draft_Save)
    if not ResetStandardWeather: cdA_List.append(cdA) #cdA Liste wird nur gefüllt wenn der Aufruf aus dem Hauptprogramm erfolgt ist
    if Use_AdvWeather:
        rho = calc_rho_advanced(t_cumm)
        v_w0=AdvWeather_AirSpeed[-1]
        dir_w=AdvWeather_AirDir[-1]
    else:
        rho = calc_rho(T_Luft,h_mean)
    if ResetStandardWeather:
        v_w0=v_w0_0
        dir_w=dir_w_0        
    v_w=-cos((dir_w-direction_tmp)*deg2rad)*v_w0*Winddamping /3.6 #m/s
    f_r_dyn = 100/eta * cr_dyn * cos(beta)
    f_r = 100/eta * cr * m_sys * g * cos(beta)
    f_g = 100/eta * m_sys * g * sin(beta)
    f_l_0 = 100/eta * 0.5 * cdA * rho * v_w**2
    f_l_1 = 100/eta * cdA * rho * v_w
    f_l_2 = 100/eta * 0.5 * cdA * rho
    aa = f_l_2
    bb = f_l_1 + f_r_dyn
    cc = f_l_0 + f_g + f_r
    dd = -power_tmp
    a = bb / aa
    b = cc / aa
    c = dd / aa
    p = b - a**2 / 3
    q = 2*a**3/27 - a*b/3+c
    DELTA = (q / 2)**2 + (p / 3)**3
    if DELTA >= 0:
        uu = copysign(1,(-q / 2 + sqrt(DELTA))) * fabs(-q / 2 + sqrt(DELTA))**(1/3)
        vv = copysign(1,(-q / 2 - sqrt(DELTA))) * fabs(-q / 2 - sqrt(DELTA))**(1/3)
        v_b = (uu + vv - (bb / (3*aa)))
    else:
        v_b = sqrt(-4/3*p)*cos(1/3*acos(-q/2*sqrt(-27/(p**3))))-bb/(3*aa)
    return v_b    

def print_statistics(i,New_v_ave,output):
    global tab1,cal_consumption
    #Statistiken ausgeben
    n=len(t)
    AveP=np.average(power[1:n], weights=t[1:n])
    NP=(np.sum(tP4[1:n])/np.sum(t[1:n]))**0.25
    AveP_r_rel=np.average(P_r_rel[1:n], weights=t[1:n])    
    AveP_g_rel=np.average(P_g_rel[1:n], weights=t[1:n])
    AveP_l_rel=np.average(P_l_rel[1:n], weights=t[1:n])       
    AveP_r=np.average(np.array(P_r_rel[1:n])*np.array(power[1:n]), weights=t[1:n])/100
    AveP_g=np.average(np.array(P_g_rel[1:n])*np.array(power[1:n]), weights=t[1:n])/100
    AveP_l=np.average(np.array(P_l_rel[1:n])*np.array(power[1:n]), weights=t[1:n])/100    
    d_total=pos[n-1]
    t_total=t_cumm[n-1]
    v_ave=d_total/t_total*3600
    IF=NP/FTP
    TSS=100*t_total/3600*IF**2
    ele_gain=el_gain_from_height(h)
    grade_max=np.max(grade[1:n])
    grade_min=np.min(grade[1:n])
    power_max2=np.max(power[1:n])
    power_min2=np.min(power[1:n])
    h_mean=np.average(h)
    v_flat_AveP = calc_v(AveP,0,h_mean,0,0,0,True)*3.6
    v_flat_NP = calc_v(NP,0,h_mean,0,0,0,True)*3.6
    t_cdA_Flat=0
    t_cdA_Hill=0
    t_cdA_Draft=0
    cdA_Draft=0
    if Draft_Save>0: cdA_Draft= cdA_Flat * (1 - Draft_Save/100)
    for i in range(1,len(cdA_List)):
        if abs(cdA_Flat-cdA_List[i])<0.001:
            t_cdA_Flat+=t[i]
        if abs(cdA_Hill-cdA_List[i])<0.001:
            t_cdA_Hill+=t[i]    
        if abs(cdA_Draft-cdA_List[i])<0.001 and Draft_Save>0:
            t_cdA_Draft+=t[i] 
    tmp1=0
    tmp2=0
    for i in range(1,n):
        tmp1+=t[i]*P_Save[i]
        tmp2+=t[i]*P_ges[i]
    P_Save_total=tmp1/(tmp1+tmp2)*100
    
    mech_work=AveP*t_total/1000
    metab_efficiency=0.21 #beim Radfahren etwa 0.21 und beim Laufen etwa 0.26 (mit Stryd)
    metab_work=mech_work/metab_efficiency
    cal_consumption=metab_work/4.184    
    
    if New_v_ave:
        v_ave_liste.append(v_ave)
    if output:               
        tab1, ax =plt.subplots()
        data=[['Mittlere Geschwindigkit [km/h]',round(v_ave,2)],
              ['Maximale Leistung [W]',round(power_max2,1)],
              ['Minimale Leistung [W]',round(power_min2,1)],
              ['Average Power [W]',round(AveP,1)],
              ['Normalized Power [W]',round(NP,1)],
              ['Averaged Power rolling [% / W]',str(round(AveP_r_rel,1))+' / '+str(round(AveP_r,1))],
              ['Averaged Power grade [% / W]',str(round(AveP_g_rel,1))+' / '+str(round(AveP_g,1))],
              ['Averaged Power air [% / W]',str(round(AveP_l_rel,1))+' / '+str(round(AveP_l,1))],
              ['Mech. Work/ Metab. Work [kJ]',str(round(mech_work,1))+' / '+str(round(metab_work,1))],
              ['Calories [kcal]',round(cal_consumption,1)],
              ['Gesamtzeit [hh:mm:ss]',datetime.timedelta(seconds=round(t_total,0))],
              ['Gesamtstrecke [km]',round(d_total,2)],
              ['Intensity Factor [%]',round((IF*100),2)],
              ['TSS',round(TSS,1)],
              ['Höhengewinn [m]',round(ele_gain,2)],
              ['Maximale Steigung [%]',round(grade_max,2)],
              ['Minimale Steigung [%]',round(grade_min,2)],
              ['Leistung bei 0%   [W]',round(pol_a0,1)],
              ['Mehrleistung pro +1% [W]',round(pol_a1p,1)],
              ['Minderleistung pro -1% [W]',round(pol_a1m,1)],
              ['Kraftersarniss. Windschatten',round(P_Save_total,1)],
              ['Geschw./Geschw. bei AveP, Flach & Windstill [%]/[km/h]',str(round(v_ave/v_flat_AveP*100,2))+' / '+str(round(v_flat_AveP,2))],
              ['Geschw./Geschw. bei NP, Flach & Windstill [%]/[km/h]',str(round(v_ave/v_flat_NP*100,2))+' / '+str(round(v_flat_NP,2))],
              ['Zeit innerhalb cdA Flat [%]',round(t_cdA_Flat/t_total*100,2)],
              ['Zeit innerhalb cdA Hill [%]',round(t_cdA_Hill/t_total*100,2)],
              ['Zeit innerhalb cdA Draft [%]',round(t_cdA_Draft/t_total*100,2)],
              ['cdA Flat [m^2]',round(cdA_Flat,4)],
              ['cdA Hill [m^2]',round(cdA_Hill,4)],
              ['cdA Draft [m^2]',round(cdA_Draft,4)]]  
        ax.axis('off')
        ax.set_title('Statistiken')
        ax.table(cellText=data,cellLoc='center',loc='upper left')
        if Show_Plots_in_Run:
            plt.show()   
        else:
            plt.close()              

def time_in_power_zones():
    global tab2,tab3
    table1=[]
    table2=[]
    t_in_p=[t_cumm[-1]]
    n_in_p=[1]
    t_in_p_total=[t_cumm[-1]]
    power_list = [0,100,150,180,200]
    add = 210
    jmax=len(power)
    while add <= np.max(power[1:jmax])+10:
        power_list.append(add)
        add+=10
#    power_list[-1]+=1
    
    for i in range(1,len(power_list)):
        t_in_p_total_tmp=0
        t_in_p_tmp1=0
        t_in_p_tmp2=0
        n_in_p_tmp=0
        j2=0
        new_series=True
        for j in range(jmax): 
            if power[j] > power_list[i]:
                t_in_p_total_tmp+=t[j]   
            if power[j] > power_list[i] and (j-j2==1 or new_series):   
                new_series=False
                j2=j
                t_in_p_tmp1+=t[j]
            if (j-j2==2 and not new_series) or (j==jmax-1 and n_in_p_tmp==0):
                new_series=True
                t_in_p_tmp2 = max(t_in_p_tmp1,t_in_p_tmp2)
                t_in_p_tmp1=0
                if t_in_p_total_tmp>0:
                    n_in_p_tmp+=1
                   
        t_in_p_total.append(t_in_p_total_tmp)
        t_in_p.append(t_in_p_tmp2)
        n_in_p.append(n_in_p_tmp)
                


    table1.append([power_list[0],datetime.timedelta(seconds=round(t_in_p_total[0],0)),datetime.timedelta(seconds=round(t_in_p[0],0)),n_in_p[0]])
    for i in range(1,len(power_list)):
        table1.append([power_list[i],datetime.timedelta(seconds=round(t_in_p_total[i],0)),datetime.timedelta(seconds=round(t_in_p[i],0)),n_in_p[i]])
        c1=str(power_list[i-1])+' to '+str(power_list[i])
        table2.append([c1,datetime.timedelta(seconds=round(t_in_p_total[i-1]-t_in_p_total[i],0))])
#    print()   
#    print()   
#    print('Tabelle mit Zeiten oberhalb definierter Leistungswerte')
    header=['Leistung [W]', 'Gesamtzeit > Leistung', 'Zeit am Stück > Leistung', 'Anzahl >= Leisung']
#    print(tabulate(table1, headers=header, tablefmt='pipe', stralign='center')) 
    tab2, ax =plt.subplots() 
    ax.axis('off')
    ax.set_title('Zeiten oberhalb definierter Leistungswerte')
    ax.table(cellText=table1,colLabels=header,cellLoc='center',loc='upper left')
    if Show_Plots_in_Run:
        plt.show()    
    else:
        plt.close()          
#    print()   
#    print()   
#    print('Tabelle mit Zeiten innerhalb Leistungsbereiche')
    header=['Leistungsbereich [W]', 'Gesamtzeit in Bereich']    
#    print(tabulate(table2, headers=header, tablefmt='pipe', stralign='center'))
    tab3, ax =plt.subplots() 
    ax.axis('off')
    ax.set_title('Zeiten innerhalb Leistungsbereiche')
    ax.table(cellText=table2,colLabels=header,cellLoc='center',loc='upper left')
    if Show_Plots_in_Run:
        plt.show()        
    else:
        plt.close()          


def Substratverlauf():
    global fig21,Fett_Ratio,KH_Ratio,tot_cal_sum,Fett_sum,KH_sum
    a_tot_cal=3.6
    PFatMax=0.675*FTP
    fFatMax=0.655*a_tot_cal*PFatMax
  
    P_Substat=[]
    y_tot_cal=[]
    y_Fett=[]  
    y_KH=[]
    for i in range(int(1.3*FTP)):
        P_Substat.append(i)
        y_tot_cal.append(function_y_tot_cal(i,a_tot_cal))
        y_Fett.append(function_y_Fett(i,a_tot_cal,fFatMax,PFatMax,FTP))
        y_KH.append(function_y_KH(i,a_tot_cal,fFatMax,PFatMax,FTP))     
    
    Fett_Ratio=[]
    KH_Ratio=[]
    tot_cal_sum_pre=[]
    Fett_sum_pre=[]
    KH_sum_pre=[]
    Fett_Ratio.append(0)
    KH_Ratio.append(0)
    tot_cal_sum_pre.append(0)
    Fett_sum_pre.append(0)
    KH_sum_pre.append(0)
    # for Pow in power:
    for i in range(1,len(t_cumm)):
        Pow=power[i]
        Fett_Ratio_tmp=function_y_Fett(Pow,a_tot_cal,fFatMax,PFatMax,FTP)/function_y_tot_cal(Pow,a_tot_cal)*100
        Fett_Ratio.append(Fett_Ratio_tmp)
        KH_Ratio.append(100-Fett_Ratio_tmp)
        tot_cal_sum_pre.append(tot_cal_sum_pre[i-1]+function_y_tot_cal(Pow,a_tot_cal)*(t_cumm[i]-t_cumm[i-1]))
        Fett_sum_pre.append(Fett_sum_pre[i-1]+function_y_Fett(Pow,a_tot_cal,fFatMax,PFatMax,FTP)*(t_cumm[i]-t_cumm[i-1]))
        KH_sum_pre.append(KH_sum_pre[i-1]+function_y_KH(Pow,a_tot_cal,fFatMax,PFatMax,FTP)*(t_cumm[i]-t_cumm[i-1]))
    tot_cal_sum=[]
    Fett_sum=[]
    KH_sum=[]
    corr_fac=cal_consumption/tot_cal_sum_pre[-1]
    for i in range(len(tot_cal_sum_pre)):        
        tot_cal_sum.append(tot_cal_sum_pre[i]*corr_fac)
        Fett_sum.append(Fett_sum_pre[i]*corr_fac)
        KH_sum.append(KH_sum_pre[i]*corr_fac)
    fig21 = plt.figure() 
    ax = fig21.add_subplot(111) 
    lns1=ax.plot(P_Substat, y_tot_cal,'blue',label='Gesamt')
    lns2=ax.plot(P_Substat, y_Fett,'red',label='Fett')
    lns3=ax.plot(P_Substat, y_KH,'black',label='KH')   
    lns=lns1+lns2+lns3
    labs = [l.get_label() for l in lns]
    ax.legend(lns, labs, loc='upper center',bbox_to_anchor=(0.5, -0.15),ncol=3) 
    textstr = '\n'.join((
        r'FTP: %.0f W' % (FTP),
        r'FettMax: %.0f kcal/h (%.1f %% / %.0f g/h) @ %.0f W (%.1f %% of FTP)' % (fFatMax,fFatMax/function_y_tot_cal(PFatMax,a_tot_cal)*100,fFatMax/9,PFatMax,PFatMax/FTP*100),
        r'KH @ FettMax: %.0f kcal/h (%.1f %% / %.0f g/h)' % (function_y_KH(PFatMax,a_tot_cal,fFatMax,PFatMax,FTP),function_y_KH(PFatMax,a_tot_cal,fFatMax,PFatMax,FTP)/function_y_tot_cal(PFatMax,a_tot_cal)*100,function_y_KH(PFatMax,a_tot_cal,fFatMax,PFatMax,FTP)/4))) 
    ax.text(-0.1, -0.4, textstr, transform=ax.transAxes, fontsize=11)     
    ax.grid()
    ax.set_title('Substratverlauf')
    ax.set_xlabel('Power [W]')
    ax.set_ylabel('Energie [kcal/h]')
    if Show_Plots_in_Run:
        plt.show()        
    else:
        plt.close()   


def function_y_tot_cal(P,a_tot_cal):
    return a_tot_cal*P

def function_y_Fett(P,a_tot_cal,fFatMax,PFatMax,FTP):
    #Fettkurve von 0 bis FatMax --> y1 = a0 + a1 P + a2 P^2 + a3 P^3
    #RB y1(0)=0, y1'(0)=a_tol_cal, y1(PFatMax)=fFatMax, y1'(PFatMax)=0
    a0 = 0
    a1 = a_tot_cal
    a2 = (3*fFatMax-2*a_tot_cal*PFatMax)/PFatMax**2
    a3 = (-2*fFatMax+a_tot_cal*PFatMax)/PFatMax**3

    #Fettkurve von FatMax bis FTP --> y2 = b0 + b1 (P-PFatMax) + b2 (P-PFatMax)^2 + b3 (P-PFatMax)^3 + b4 (P-PFatMax)^4
    #RB y2(0)=fFatMax, y2'(0)=0, y2(FTP)=0, y2'(FTP)=a_fett_FTP
    a_fett_FTP=-3*a_tot_cal
    y2ss_FatMax = 2*a2+6*a3*PFatMax
    b0 = fFatMax
    b1 = 0
    b2 = y2ss_FatMax/2
    b3 = (4*(-b0-b1*(FTP-PFatMax)-b2*(FTP-PFatMax)**2)-(a_fett_FTP-b1-2*b2*(FTP-PFatMax))*(FTP-PFatMax))/(FTP-PFatMax)**3
    b4 = ((a_fett_FTP-b1-2*b2*(FTP-PFatMax))*(FTP-PFatMax)-3*(-b0-b1*(FTP-PFatMax)-b2*(FTP-PFatMax)**2))/(FTP-PFatMax)**4 

    if (P<=PFatMax):
        y_Fett_i=a0+a1*P+a2*P**2+a3*P**3
    elif (P>PFatMax and P<=FTP):
        y_Fett_i=b0+b1*(P-PFatMax)+b2*(P-PFatMax)**2+b3*(P-PFatMax)**3+b4*(P-PFatMax)**4
    else:
        y_Fett_i=0
    return y_Fett_i

def function_y_KH(P,a_tot_cal,fFatMax,PFatMax,FTP):
    return function_y_tot_cal(P,a_tot_cal)-function_y_Fett(P,a_tot_cal,fFatMax,PFatMax,FTP)

def plot_diagrams(sigma_filter,x_Achse,Histogram_Anz_Teilungen):  
    global fig2,fig3,fig4,fig5,fig6,fig7,fig8,fig9,fig10,fig11,fig12,tab4,tab5,tab6,fig15,fig16,fig16b,fig17,fig20,fig22
    fig2=0
    fig9=0
    fig15=0
    fig16=0
    fig16b=0
    fig17=0
    tab5=0
    tab6=0
    #v_Ave abhäng der maximalen Leistung  
    if len(power_max_liste)>1 and Use_GPX_Input:
#        print()
#        print()
#        print('Durchschnittsgeschwindigkeit abhängig der maximal aufgebrachten Leistung')           
        fig2, ax = plt.subplots()
        ax.plot(power_max_liste, v_ave_liste,'blue')
        ax.set_title('Durchschnittsgeschwindigkeit abhängig der maximal aufgebrachten Leistung')
        ax.set_xlabel('Maximum Power [W]')
        ax.set_ylabel('Durchschnittsgeschwindigkeit [km/h]')
        ax.grid()
        if Show_Plots_in_Run:
            plt.show()                       
        else:
            plt.close()              
    
    #Herausschreiben der Rohdaten
    filename = "rawdata.csv"
    header = ['time [s]', 'distance [m]', 'speed [km/h]', 'elevation [m]', 'power [W]','Latitude','Longitude']
    with open(filename, 'w') as csvfile:  
        csvwriter = csv.writer(csvfile, lineterminator='\r')  
        csvwriter.writerow(header)
        for i in range(1,len(t_cumm)):
            row = [t_cumm[i],pos[i],pos[i]/t_cumm[i]*3600,h[i],power[i],lat2[i],lon2[i]]
            csvwriter.writerow(row)     
    
    #Plot-Achsen definieren für alle Folgeplots
    if x_Achse=='Zeit':
        x=[]
        for i in range(len(t_cumm)):
            x.append(t_cumm[i]/60)
        x_label='Zeit [min]'
    else:
        x=pos
        x_label='Distanz [km]'
    
    #Durchschnittsgeschwindigkeit
#    print()
#    print()
#    print('Durchschnittsgeschwindigkeit und Höhe')    
    x1=[]
    y1=[]
    y2=[]
    for i in range(1,len(t_cumm)):
        x1.append(x[i])
        y1.append(pos[i]/t_cumm[i]*3600)
        y2.append(h[i])
    n=len(x1)
    vminges=np.min(y1)
    ii=Find_Index_Close(y1,vminges)
    xminges=x1[ii] 
    vmaxges=np.max(y1)
    ii=Find_Index_Close(y1,vmaxges) 
    xmaxges=x1[ii]  
    i=Find_Index_Close(x1,0.1*x1[-1])   
    vmin10=np.min(y1[i:n])
    ii=Find_Index_Close(y1,vmin10)
    xmin10=x1[ii]
    vmax10=np.max(y1[i:n])
    ii=Find_Index_Close(y1,vmax10)
    xmax10=x1[ii]    
    i=Find_Index_Close(x1,0.5*x1[-1])   
    vmin50=np.min(y1[i:n])
    ii=Find_Index_Close(y1,vmin50)
    xmin50=x1[ii]
    vmax50=np.max(y1[i:n])
    ii=Find_Index_Close(y1,vmax50)
    xmax50=x1[ii]    
    tab4, ax =plt.subplots()
    column_labels=['Geschw. min/max', 'Durchschnittsgeschw. [km/h]', 'Position [km]','Streckentyp']
    data=[['Minimum',round(vminges,2),round(xminges,2),'gesamte Strecke'],
          ['Maximum',round(vmaxges,2),round(xmaxges,2),'gesamte Strecke'],
          ['Minimum',round(vmin10,2),round(xmin10,2),'10%-100% der Strecke'],
          ['Maximum',round(vmax10,2),round(xmax10,2),'10%-100% der Strecke'],
          ['Minimum',round(vmin50,2),round(xmin50,2),'50%-100% der Strecke'],
          ['Maximum',round(vmax50,2),round(xmax50,2),'50%-100% der Strecke']]  
    ax.axis('off')
    ax.set_title('Durchschnittsgeschwindigkeiten an verschiedenen Positionen')
    ax.table(cellText=data,colLabels=column_labels,cellLoc='center',loc='upper left')
    if Show_Plots_in_Run:
        plt.show()   
    else:
        plt.close()          

    if Show_km_Markers>0: 
        km_value=Show_km_Markers
        data=[]
        data_weather_lookup=[]
        for i in range(len(pos)-1):
            if pos[i]-km_value>0:
                data.append([round(pos[i],2),datetime.timedelta(seconds=round(t_cumm[i],0)),round(pos[i]/t_cumm[i]*3600,2)])
                data_weather_lookup.append([round(pos[i],2),round(t_cumm[i]/60,0),lat2[i],lon2[i]])
                km_value+=Show_km_Markers   
        data.append([round(pos[-1],2),datetime.timedelta(seconds=round(t_cumm[-1],0)),round(pos[-1]/t_cumm[-1]*3600,2)])
        data_weather_lookup.append([round(pos[-1],2),round(t_cumm[-1]/60,0),lat2[-1],lon2[-1]])
        tab5, ax =plt.subplots()
        column_labels=['Strecke [km]', 'Zeit [hh:mm:ss]', 'Durchschnittsgeschw. [km/h]']
        ax.axis('off')
        ax.set_title('Durchfahrtszeiten und Durchschnittsgeschwindigkeiten')
        ax.table(cellText=data,colLabels=column_labels,cellLoc='center',loc='upper left')
        if Show_Plots_in_Run:
            plt.show()   
        else:
            plt.close()        
        tab6, ax =plt.subplots()
        column_labels=['Strecke [km]', 'Zeit [min]', 'latitude', 'longitude']
        ax.axis('off')
        ax.set_title('Strecke, Zeit und GPS-Koordinate')
        ax.table(cellText=data_weather_lookup,colLabels=column_labels,cellLoc='center',loc='upper left')
        if Show_Plots_in_Run:
            plt.show()   
        else:
            plt.close()              


    fig3, ax = plt.subplots() 
    ax2 = ax.twinx()
    ax.plot(x1, y1,'blue')
    ax2.plot(x1, y2,'red')
    ax.set_title('Durchschnittsgeschwindigkeit und Höhe')
    ax.set_xlabel(x_label)
    ax.set_ylabel('Durchschnittsgeschwindigkeit [km/h]', color='b')
    ax2.set_ylabel('Höhe [m]', color='r')
    ax.grid()
    if Show_Plots_in_Run:
        plt.show()   
    else:
        plt.close()          
        
    #Geschwindigkeit und Höhe; Leisungsanteile
#    print()
#    print()
#    print('Geschwindigkeit und Höhenprofil sowie Leistungsanteile')
    fig4 = plt.figure() 
    ax = fig4.add_subplot(111) 
    if Gaus_Filter:
        print('Gauss Filter: ',sigma_filter)
        y1=h
        y2=gaussian_filter1d(v, sigma=sigma_filter)
        y3=gaussian_filter1d(P_r_rel, sigma=sigma_filter)
        y4=gaussian_filter1d(P_g_rel, sigma=sigma_filter)
        y5=gaussian_filter1d(P_l_rel, sigma=sigma_filter)
    else:   
#        print('Moving Ave Filter: ',moving_ave_filter)
        y1=h
        y2=np.array(moving_ave2(pos,t_cumm,moving_ave_filter))*3600
        y3=moving_ave(P_r_rel,moving_ave_filter)
        y4=moving_ave(P_g_rel,moving_ave_filter)
        y5=moving_ave(P_l_rel,moving_ave_filter)
    lns1=ax.plot(x,y1,'blue',label='Höhe')
    ax2 = ax.twinx() 
    lns2=ax2.plot(x,y2,'red',label='Geschw.')
    lns3=ax2.plot(x,y3,'green',label='Rollwiderstand') 
    lns4=ax2.plot(x,y4,'purple',label='Steigungswiderstand') 
    lns5=ax2.plot(x,y5,'orange',label='Luftwiderstand')     
    lns=lns1+lns2+lns3+lns4+lns5
    labs = [l.get_label() for l in lns]
    ax.legend(lns, labs, loc='upper center',bbox_to_anchor=(0.5, -0.15),ncol=3) 
    ax.grid()
    ax.set_title('Geschwindigkeit und Höhenprofil sowie Leistungsanteile')
    ax.set_xlabel(x_label)
    ax.set_ylabel('Höhe [m]')
    ax2.set_ylabel('Geschwindigkeit [km/h] / Leistung [%]')   
    if Show_Plots_in_Run:
        plt.show()   
    else:
        plt.close()          
    
    #Geschwindigkeit und Höhe
#    print()
#    print()
#    print('Geschwindigkeit und Höhenprofil')
    fig5, ax = plt.subplots()
    ax2 = ax.twinx()
    if Gaus_Filter:
        print('Gauss Filter: ',sigma_filter)    
        y1=gaussian_filter1d(v, sigma=sigma_filter)
        y2=h
    else:   
#        print('Moving Ave Filter: ',moving_ave_filter)
        y1=np.array(moving_ave2(pos,t_cumm,moving_ave_filter))*3600
        y2=h        
    ax.plot(x, y1,'blue')
    ax2.plot(x, y2,'red')
    ax.set_title('Geschwindigkeit und Höhenprofil')
    ax.set_xlabel(x_label)
    ax.set_ylabel('Geschwindigkeit [km/h]', color='b')
    ax2.set_ylabel('Höhe [m]', color='r')
    ax.grid()
    if Show_Plots_in_Run:
        plt.show()   
    else:
        plt.close()          

    #Geschwindigkeit und Steigung
#    print()
#    print()
#    print('Geschwindigkeit und Steigung')    
    fig6, ax = plt.subplots()
    ax2 = ax.twinx()
    if Gaus_Filter:
        print('Gauss Filter: ',sigma_filter)    
        y1=gaussian_filter1d(v, sigma=sigma_filter)
        y2=gaussian_filter1d(grade, sigma=sigma_filter)
    else:   
#        print('Moving Ave Filter: ',moving_ave_filter)
        y1=np.array(moving_ave2(pos,t_cumm,moving_ave_filter))*3600
        y2=np.array(moving_ave2(h,pos,moving_ave_filter))*0.1
    ax.plot(x, y1,'blue')
    ax2.plot(x, y2,'red')
    ax.set_title('Geschwindigkeit und Steigung')
    ax.set_xlabel(x_label)
    ax.set_ylabel('Geschwindigkeit [km/h]', color='b')
    ax2.set_ylabel('Steigung [%]', color='r')
    ax.grid()
    if Show_Plots_in_Run:
        plt.show()      
    else:
        plt.close()          

    #Leistung und Höhe
#    print()
#    print()
#    print('Leistung und Höhenprofil')    
    fig7, ax = plt.subplots()
    ax2 = ax.twinx()
    if Gaus_Filter:
        print('Gauss Filter: ',sigma_filter)    
        y1=gaussian_filter1d(power, sigma=sigma_filter)
        y2=h
    else:   
#        print('Moving Ave Filter: ',moving_ave_filter)
        y1=moving_ave(power,moving_ave_filter)
        y2=h          
    ax.plot(x, y1,'blue')
    ax2.plot(x, y2,'red')
    ax.set_title('Leistung und Höhenprofil')    
    ax.set_xlabel(x_label)
    ax.set_ylabel('Lesitung [W]', color='b')
    ax2.set_ylabel('Höhe [m]', color='r')
    ax.grid()
    if Show_Plots_in_Run:
        plt.show()   
    else:
        plt.close()          
    
    #Leistung und Steigung
#    print()
#    print()
#    print('Leistung und Steigung')    
    fig8, ax = plt.subplots()
    ax2 = ax.twinx()
    if Gaus_Filter:
        print('Gauss Filter: ',sigma_filter)    
        y1=gaussian_filter1d(power, sigma=sigma_filter)
        y2=gaussian_filter1d(grade, sigma=sigma_filter)
    else:   
#        print('Moving Ave Filter: ',moving_ave_filter)
        y1=moving_ave(power,moving_ave_filter)
        y2=np.array(moving_ave2(h,pos,moving_ave_filter))*0.1
    ax.plot(x, y1,'blue')
    ax2.plot(x, y2,'red')
    ax.set_title('Leistung und Steigung')
    ax.set_xlabel(x_label)
    ax.set_ylabel('Lesitung [W]', color='b')
    ax2.set_ylabel('Steigung [%]', color='r')
    ax.grid()
    if Show_Plots_in_Run:
        plt.show()   
    else:
        plt.close()    
               
    Substratverlauf()
    fig22 = plt.figure() 
    ax = fig22.add_subplot(111) 
    if Gaus_Filter:
        print('Gauss Filter: ',sigma_filter)
        y1=gaussian_filter1d(Fett_Ratio, sigma=sigma_filter)
        y2=gaussian_filter1d(KH_Ratio, sigma=sigma_filter)
    else:   
#        print('Moving Ave Filter: ',moving_ave_filter)
        y1=moving_ave(Fett_Ratio,moving_ave_filter)
        y2=moving_ave(KH_Ratio,moving_ave_filter)
    lns1=ax.plot(x,y1,'red',label='Fett Anteil')
    lns2=ax.plot(x,y2,'black',label='KH Anteil')
    ax2 = ax.twinx() 
    lns3=ax2.plot(x,tot_cal_sum,'blue',label='Gesamt Kalorien (Summe)')    
    lns4=ax2.plot(x,Fett_sum,'orange',label='Fett Kalorien (Summe)')
    lns5=ax2.plot(x,KH_sum,'green',label='KH Kalorien (Summe)')
    lns=lns1+lns2+lns3+lns4+lns5
    labs = [l.get_label() for l in lns]
    ax.legend(lns, labs, loc='upper center',bbox_to_anchor=(0.5, -0.15),ncol=3) 
    textstr = '\n'.join((
        r'Fett',
        r'Anteil: %.1f %%' % (Fett_sum[-1]/tot_cal_sum[-1]*100),
        r'Energie: %.0f kcal' % (Fett_sum[-1]),
        r'Menge: %.0f g / %.0f g/h' % (Fett_sum[-1]/9,Fett_sum[-1]/9/t_cumm[-1]*3600)))  
    ax.text(-0.1, -0.5, textstr, transform=ax.transAxes, fontsize=11)
    textstr = '\n'.join((
        r'KH',
        r'Anteil: %.1f %%' % (KH_sum[-1]/tot_cal_sum[-1]*100),
        r'Energie: %.0f kcal' % (KH_sum[-1]),
        r'Menge: %.0f g / %.0f g/h' % (KH_sum[-1]/4,KH_sum[-1]/4/t_cumm[-1]*3600)))
    ax.text(0.35, -0.5, textstr, transform=ax.transAxes, fontsize=11)
    textstr = '\n'.join((
        r'KH Zuführung',
        r'mit Sicherheit (1.5):',
        r'%.0f gKH/h' % (1.5*KH_sum[-1]/4/t_cumm[-1]*3600),
        r''))       
    ax.text(0.8, -0.5, textstr, transform=ax.transAxes, fontsize=11)    
    ax.grid()
    ax.set_title('Substratverbrauch (Gesamt %.0f kcal)' % (tot_cal_sum[-1]))
    ax.set_xlabel(x_label)
    ax.set_ylabel('Energieanteil [%]')
    ax2.set_ylabel('Energie [kcal]')   
    if Show_Plots_in_Run:
        plt.show()        
    else:
        plt.close()  

    if Use_AdvWeather:
        AdvWeather_TempC.pop()
        AdvWeather_AirSpeed.pop()
        AdvWeather_AirDir.pop()
        AdvWeather_AirMoisture.pop()
        AdvWeather_AirPressure.pop()
        AdvWeather_AirDensity.pop()
        if API_Weather:
            AdvWeather_ApparentT.pop()
            AdvWeather_WindGusts.pop()
            AdvWeather_Precipitation.pop()
        fig15, ax = plt.subplots()
        y1=np.array(moving_ave2(pos,t_cumm,moving_ave_filter))*3600
        y2=np.array(moving_ave(AdvWeather_AirSpeed,moving_ave_filter))*Winddamping
        vbw=[]
        vbwx=[]
        vbwy=[]
        for i in range(len(x)):
            dirb=direction[i]
            dirw=AdvWeather_AirDir[i]
            vbw.append(y1[i]-cos((dirw-dirb)*deg2rad)*y2[i])
            vbx=y1[i]*sin((-180)*deg2rad)
            vby=y1[i]*cos((-180)*deg2rad)
            vwx=y2[i]*sin((dirw-dirb-180)*deg2rad)
            vwy=y2[i]*cos((dirw-dirb-180)*deg2rad)
            vbwx.append(vbx-vwx)
            vbwy.append(vby-vwy)
        y3=moving_ave(vbw,moving_ave_filter)
        lns1=ax.plot(x, y1,'blue',label='Bike')
        lns2=ax.plot(x, y2,'red',label='Wind')
        lns3=ax.plot(x, y3,'green',label='Bike+Wind')
        n=15
        y4=moving_ave(direction,moving_ave_filter)
        for i in range(n+1):
            j=Find_Index_Close(x,i/n*x[-1])
            dir1arrow=y4[j]*deg2rad   
            dir2arrow=AdvWeather_AirDir[j]*deg2rad   
            dx1arrow=sin(dir1arrow)
            dy1arrow=cos(dir1arrow)
            dx2arrow=sin(dir2arrow)
            dy2arrow=cos(dir2arrow)
            ax.quiver(x[j],y1[j],dx1arrow,dy1arrow,color='blue',pivot='mid')
            ax.quiver(x[j],y2[j],dx2arrow,dy2arrow,color='red',pivot='mid')
            ax.quiver(x[j],y3[j],vbwx[j],vbwy[j],color='green',pivot='mid')
        lns=lns1+lns2+lns3
        labs = [l.get_label() for l in lns]
        ax.legend(lns, labs, loc='upper center',bbox_to_anchor=(0.5, -0.15),ncol=3) 
        ax.set_title('Geschwindigkeit Bike und Wind')
        ax.set_xlabel(x_label)
        ax.set_ylabel('Geschwindigkeit [km/h]')        
        ax.annotate('Grüne Pfeile geben relative Windrichtung an; nach unten: Wind von vorne; nach oben: Wind schneller als man selbst',xy=(0.07,0.08), xycoords='figure fraction',size=5,color='green')
        ax.grid()
        if Show_Plots_in_Run:
            plt.show()   
        else:
            plt.close()      
   
        fig16, ax = plt.subplots()
        ax2 = ax.twinx()
        ax3 = ax.twinx()
        ax4 = ax.twinx()
        ax5 = ax.twinx()
        ax3.spines['right'].set_position(('axes', 1.15))
        ax4.spines['right'].set_position(('axes', 1.3))
        ax5.spines['right'].set_position(('axes', 1.45))
        y1=moving_ave(AdvWeather_TempC,moving_ave_filter)
        y2=np.array(moving_ave(AdvWeather_AirSpeed,moving_ave_filter))*Winddamping
        y3=moving_ave(AdvWeather_AirMoisture,moving_ave_filter)
        y4=moving_ave(AdvWeather_AirPressure,moving_ave_filter)
        y5=moving_ave(AdvWeather_AirDensity,moving_ave_filter)
        ax.plot(x, y1,'blue')
        ax2.plot(x, y2,'red')
        ax3.plot(x, y3,'green')
        ax4.plot(x, y4,'purple')
        ax5.plot(x, y5,'orange')
        n=15
        for i in range(n+1):
            j=Find_Index_Close(x,i/n*x[-1])
            dirarrow=AdvWeather_AirDir[j]*deg2rad    
            dxarrow=sin(dirarrow)
            dyarrow=cos(dirarrow)
            ax2.quiver(x[j],y2[j],dxarrow,dyarrow,color='red',pivot='mid')
        if API_Weather: title='Wetter (Online-API), Date: '+str(datetime_StartTime)
        else: title='Wetter (CSV-Datei)'     
        ax.set_title(title)
        ax.tick_params(axis='y', colors='blue')
        ax2.tick_params(axis='y', colors='red')
        ax3.tick_params(axis='y', colors='green')
        ax4.tick_params(axis='y', colors='purple')
        ax5.tick_params(axis='y', colors='orange')
        ax.set_xlabel(x_label)
        ax.set_ylabel('Temperatur [°C]', color='blue')
        ax2.set_ylabel('Windgeschwindigkeit [km/h]', color='red')
        ax3.set_ylabel('Luftfeuchte [%]', color='green')
        ax4.set_ylabel('Luftdruck [hPa]', color='purple') 
        ax5.set_ylabel('Luftdichte [kg/m³]', color='orange') 
        ax.grid()
        if Show_Plots_in_Run:
            plt.show()   
        else:
            plt.close()  
        
        if API_Weather:
            fig16b, ax = plt.subplots()
            ax2 = ax.twinx()
            ax3 = ax.twinx()
#            ax4 = ax.twinx()
#            ax5 = ax.twinx()
            ax3.spines['right'].set_position(('axes', 1.15))
#            ax4.spines['right'].set_position(('axes', 1.3))
#            ax5.spines['right'].set_position(('axes', 1.45))
            xClockTime=[]
            for i in range(len(t_cumm)):
                xClockTime.append(datetime_StartTime+datetime.timedelta(seconds = t_cumm[i]))
            y1=moving_ave(AdvWeather_TempC,moving_ave_filter)
            y1b=moving_ave(AdvWeather_ApparentT,moving_ave_filter)
            y2=moving_ave(AdvWeather_AirSpeed,moving_ave_filter)
            y2b=moving_ave(AdvWeather_WindGusts,moving_ave_filter)
            y3=moving_ave(AdvWeather_Precipitation,moving_ave_filter)
            ax.plot(xClockTime, y1,'blue')
            ax.plot(xClockTime, y1b,'blue',linestyle='dashed')
            ax2.plot(xClockTime, y2,'red')
            ax2.plot(xClockTime, y2b,'red',linestyle='dashed')
            ax3.plot(xClockTime, y3,'green')
            n=15
            for i in range(n+1):
                j=Find_Index_Close(x,i/n*x[-1])
                dirarrow=AdvWeather_AirDir[j]*deg2rad    
                dxarrow=sin(dirarrow)
                dyarrow=cos(dirarrow)
                ax2.quiver(xClockTime[j],y2[j],dxarrow,dyarrow,color='red',pivot='mid')            
            title='Wetterdetails (Online-API), Date: '+str(datetime_StartTime)             
            ax.set_title(title)
            ax.tick_params(axis='y', colors='blue')
            ax2.tick_params(axis='y', colors='red')
            ax3.tick_params(axis='y', colors='green')
#            ax4.tick_params(axis='y', colors='purple')
#            ax5.tick_params(axis='y', colors='orange')
            ax.set_xlabel('Uhrzeit [hh:mm]')
            ax.set_ylabel('Temperatur und gefühlte Temperatur [°C]', color='blue')
            ax2.set_ylabel('Wind und Windböen [km/h]', color='red')
            ax3.set_ylabel('Niederschlag [mm]', color='green')
#            ax4.set_ylabel('Windböen [km/h]', color='purple') 
#            ax5.set_ylabel('Luftdichte [kg/m³]', color='orange') 
            plt.gcf().autofmt_xdate()
            myFmt = mdates.DateFormatter('%H:%M')
            plt.gca().xaxis.set_major_formatter(myFmt)            
            ax.grid()
            if Show_Plots_in_Run:
                plt.show()   
            else:
                plt.close()              
 
        fig17, ax = plt.subplots()
        y1=moving_ave(direction,moving_ave_filter)
        y2=moving_ave(AdvWeather_AirDir,moving_ave_filter)
        ax.set_title('Richtung Bike und Wind')
        ax.set_xlabel(x_label)
        ax.set_ylabel('Richtung [deg]')  
        lns1=ax.plot(x, y1,'blue',label='Bike')
        lns2=ax.plot(x, y2,'red',label='Wind')
        lns=lns1+lns2
        labs = [l.get_label() for l in lns]
        ax.legend(lns, labs, loc='upper center',bbox_to_anchor=(0.5, -0.15),ncol=2)
        ax.grid()
        if Show_Plots_in_Run:
            plt.show()   
        else:
            plt.close() 
            
            
    #Leistung über Steigung
    if Use_GPX_Input:
        x=[1.5*pol_grade_min,pol_grade_min,0,pol_grade_max,1.5*pol_grade_max]
        y=[power_min,power_min,pol_a0,power_max,power_max]
        fig9, ax = plt.subplots()
        ax.plot(x, y,'blue')
        ax.set_title('Leistung als Funktion der Steigung')
        ax.set_xlabel('Steigung [%]')
        ax.set_ylabel('Lesitung [W]')
        ax.grid()
        if Show_Plots_in_Run:
            plt.show()     
        else:
            plt.close()          
    
    #Histogramm zur Leistung    
    num_bins = Histogram_Anz_Teilungen
    x=[]
    y=[]
    for i in range(len(power)):
        if isnan(power[i])==False:
            x.append(power[i])
            y.append(t[i]) 
    y=y/np.sum(y)*100
    fig10, ax = plt.subplots()
    ax.hist(x, num_bins,weights=y, facecolor='blue',edgecolor='black')
    ax.set_title('Histogramm zur Leistungsverteilung (Zeitanteile)')
    ax.set_xlabel('Leistung [W]')
    ax.set_ylabel('Anteil an Zeit [%]') 
    if Show_Plots_in_Run:
        plt.show()   
    else:
        plt.close()          
    
    #Histogramm zur Geschwindigkeit   
    x=[]
    y=[]
    for i in range(len(v)):
        if isnan(v[i])==False:
            x.append(v[i])
            y.append(t[i])
    y=y/np.sum(y)*100
    fig11, ax = plt.subplots()
    ax.hist(x, num_bins,weights=y, facecolor='blue',edgecolor='black')
    ax.set_title('Histogramm zur Geschwindigleitsverteilung (Zeitanteile)')  
    ax.set_xlabel('Geschwindigkeit [km/h]')
    ax.set_ylabel('Anteil an Zeit [%]') 
    if Show_Plots_in_Run:
        plt.show()      
    else:
        plt.close()          
    
    #Histogramm zur Steigung      
    x=[]
    y=[]
    for i in range(len(grade)):
        if isnan(grade[i])==False:
            x.append(grade[i])
            y.append(t[i])   
    y=y/np.sum(y)*100
    fig12, ax = plt.subplots()
    ax.hist(x, num_bins,weights=y, facecolor='blue',edgecolor='black')
    ax.set_title('Histogramm zur Steigungsverteilung (Zeitanteile)')
    ax.set_xlabel('Steigung [%]')
    ax.set_ylabel('Anteil an Zeit [%]') 
    if Show_Plots_in_Run:
        plt.show()            
    else:
        plt.close()      

    #Histogramm zur cdA Verteilung 
    x=[]
    y=[]
    for i in range(len(cdA_List)):
        if isnan(cdA_List[i])==False:
            x.append(cdA_List[i])
            y.append(t[i])   
    y=y/np.sum(y)*100
    fig20, ax = plt.subplots()
    ax.hist(x, num_bins,weights=y, facecolor='blue',edgecolor='black')
    ax.set_title('Histogramm zur cdA-Verteilung (Zeitanteile)')
    ax.set_xlabel('cdA [m²]')
    ax.set_ylabel('Anteil an Zeit [%]') 
    if Show_Plots_in_Run:
        plt.show()            
    else:
        plt.close()                

#-----------------------------------------------------------------------------------------------------------------------------------------
def Run_Aero_Lab_Analysis(FIT_File,File_Distance_Start,File_Distance_End,m_r,m_b,cr_dyn,cr,cdA_Flat,cdA_Hill,eta,cdA_Hill_Grade,Draft_Save_Grade,Draft_Save,T_Luft,v_w0,dir_w,Use_Bokeh,Winddamping,Use_AdvWeather,Wetterdatei_): 
    global Wetterdatei
    Wetterdatei=Wetterdatei_
    Read_Fit_File(FIT_File)        
    Plot_Elevation_and_Virtual_Elevation(File_Distance_Start,File_Distance_End,m_r,m_b,cr_dyn,cr,cdA_Flat,cdA_Hill,eta,cdA_Hill_Grade,Draft_Save_Grade,Draft_Save,T_Luft,v_w0,dir_w,Use_Bokeh,Winddamping,Use_AdvWeather)  

def Read_Fit_File(FIT_File):
    global time,elevation,distance,speed,power,lat,lon
    fitfile = FitFile(FIT_File)
    i=0
    time=[]
    elevation=[]
    distance=[]
    speed=[]
    power=[]
    lat=[]
    lon=[]
    for record in fitfile.get_messages('record'):
        # Go through all the data entries in this record
        if i==0:
            d=0
            t=0
            ele=0
            sp=0
            p=0
            la=0
            lo=0
        else:
            d=distance[i-1]
            t=time[i-1]
            ele=elevation[i-1]
            sp=speed[i-1]
            p=power[i-1]
            la=lat[i-1]
            lo=lon[i-1]
        for record_data in record:
            if(record_data.name=='timestamp'):
                tmp1 = str(record_data.value)
                tmp2 = datetime.datetime.strptime(tmp1, '%Y-%m-%d %H:%M:%S')
                h, m, s = str(tmp2.time()).split(':')
                t=int(h)*3600+int(m)*60+int(s)
                if i==0:
                    t0=t   
                    print('Date and Time of Activity Start: ',tmp1)
            if(record_data.name=='enhanced_altitude'):
                ele=record_data.value #m
            if(record_data.name=='distance'):
                d=record_data.value/1000
            if(record_data.name=='enhanced_speed'):
                sp=record_data.value   #m/s              
            if(record_data.name=='power'):
                p=record_data.value     #W
            if(record_data.name=='position_lat'):
                if str(record_data.value).isdigit():                    
                    la=record_data.value *180/(2**31 ) #semicercles to deg
                else:
                    la=lat[-1]
            if(record_data.name=='position_long'):
                if str(record_data.value).isdigit(): 
                    lo=record_data.value *180/(2**31 ) #semicercles to deg
                else:
                    lo=lon[-1]
        i+=1
        distance.append(d)  
        time.append(t-t0)
        elevation.append(ele)
        speed.append(sp) 
        power.append(p)
        lat.append(la)
        lon.append(lo)   

def Find_i_Start_End(File_Distance_Start,File_Distance_End):
    global i_Start,i_End
    i_Start=-1
    i_End=len(distance)-1
    for i in range(len(distance)):
        d=distance[i]
        if (d>=File_Distance_Start and i_Start==-1):
            i_Start=i
        if d<=File_Distance_End:
            i_End=i

def horizontal_line(xmin,xmax,y_val):
    N=2
    x = np.linspace(xmin,xmax,N)
    y = np.linspace(y_val,y_val,N)
    return x,y

def vertical_line(x_val,ymin,ymax):
    N=2
    x = np.linspace(x_val,x_val+1e-6,N)
    y = np.linspace(ymin,ymax,N)
    return x,y          
    
def Calc_Virtual_Elevation(File_Distance_Start,File_Distance_End,m_r,m_b,cr_dyn,cr,cdA_Flat,cdA_Hill,eta,cdA_Hill_Grade,Draft_Save_Grade,Draft_Save,T_Luft,v_w0,dir_w,Winddamping,Use_AdvWeather):
    global virtual_elevation,cdA_List,direction_List
    m_sys = m_r + m_b
    grade=grade_from_height(elevation,distance)
    virtual_elevation0=elevation[0]
    virtual_elevation=[virtual_elevation0]
    cdA_List=[nan]
    direction_List=[nan]
    Find_i_Start_End(File_Distance_Start,File_Distance_End)
    for i in range(1,len(distance)):  
        if i==i_Start:
            virtual_elevation0=elevation[i_Start]
        virtual_elevation_tmp=virtual_elevation0     
        if Use_AdvWeather:
            rho = calc_rho_advanced(time[0:i])
            v_w0=AdvWeather_AirSpeed[-1]
            dir_w=AdvWeather_AirDir[-1]
#            print(i,distance[i],time[i],dir_w,v_w0)
        else:
            rho = calc_rho(T_Luft,elevation[i])
        
        if speed[i]>0: #neue virtuelle Höhe berechnen, wenn nicht angehalten wurde
            cdA=calc_cdA(grade[i],cdA_Hill_Grade,cdA_Hill,cdA_Flat,Draft_Save_Grade,Draft_Save)
            cdA_List.append(cdA)    
#            rho = calc_rho(T_Luft,elevation[i])
            direction=(dir_from_lat_lon(lat[i-1],lat[i],lon[i-1],lon[i])/deg2rad) 
            direction_List.append(direction)
            v_w=cos((dir_w-direction)*deg2rad)*v_w0*Winddamping /3.6 #m/s
            Fr = cr * m_sys * g
            Fr_dyn = cr_dyn
            Fl = 0.5 * rho * cdA * (speed[i]+v_w)**2
            if i<len(distance)-1:
                a = (speed[i+1] - speed[i-1]) / (time[i+1] - time[i-1])
            else:
                a = (speed[i] - speed[i-1]) / (time[i] - time[i-1])
            Fa = m_sys * a            
            if power[i]==None:
                #print(power[i],eta,speed[i],Fr,Fr_dyn,Fl,Fa)
                power[i]=0
            s = ((power[i] * (eta/100) / speed[i]) - Fr - Fr_dyn - Fl - Fa) / (m_sys * g)
            dx=(distance[i]-distance[i-1])*1000
            virtual_elevation_tmp=virtual_elevation0+s*dx
        virtual_elevation.append(virtual_elevation_tmp)
        virtual_elevation0 = virtual_elevation_tmp     
        
def Plot_Elevation_and_Virtual_Elevation(File_Distance_Start,File_Distance_End,m_r,m_b,cr_dyn,cr,cdA_Flat,cdA_Hill,eta,cdA_Hill_Grade,Draft_Save_Grade,Draft_Save,T_Luft,v_w0,dir_w,Use_Bokeh,Winddamping,Use_AdvWeather):
    Calc_Virtual_Elevation(File_Distance_Start,File_Distance_End,m_r,m_b,cr_dyn,cr,cdA_Flat,cdA_Hill,eta,cdA_Hill_Grade,Draft_Save_Grade,Draft_Save,T_Luft,v_w0,dir_w,Winddamping,Use_AdvWeather)
    File_Distance_End=distance[i_End]
    x = np.array(distance[i_Start:i_End])
    y1 = np.array(elevation[i_Start:i_End])
    y2 = np.array(virtual_elevation[i_Start:i_End])
    dh=virtual_elevation[i_End]-elevation[i_End]  
    
    if not Use_Bokeh:
        #Info Ausgaben
        print('Höhenunterschied [m] am Streckenende: ',round(dh,2))
        print('cdA im Flachen:                       ',round(cdA_Flat,6))
    
        #Inline Pots
        #Höhe und virtuelle Höhe
        fig, ax = plt.subplots()
        ax.set_xlabel('Distanz [km]')
        ax.set_ylabel('Höhe [m]')
        lns1=ax.plot(x,y1,'blue',label='Höhe')
        lns2=ax.plot(x,y2,'red',label='virtuelle Höhe')
        lns=lns1+lns2
        labs = [l.get_label() for l in lns]
        ax.legend(lns, labs, loc='upper center',bbox_to_anchor=(0.5, -0.15),ncol=2) 
        ax.grid()
        plt.show()           
       
        #Histogramm zur cdA-Verteilung  
        print('Histogramm zur Verteilung von cdA (Zeitanteile)')       
        x=[]
        y=[]
        for i in range(i_Start,min(i_End,len(cdA_List))):
            if isnan(cdA_List[i])==False:
                x.append(cdA_List[i])
                y.append(time[i])        
        n, bins, patches = plt.hist(x,21,weights=y,density=True, facecolor='blue',edgecolor='black')
        plt.xlabel('cdA [m²]')
        plt.ylabel('Anteil an Zeit')
        plt.show()  
          

    else:
        print()
        print('Für einen Plot mit Slider zunächst Programm in Console (z.B. Annaconda Command Promt) starten:')
        print('bokeh serve Aero_Lab_Analysis.py')
        print('Dann zum anschauen des Plots in einem Webbrowser folgendes öffnen:')              
        print('http://localhost:5006/Aero_Lab_Analysis')   
        
        # Set up data
        source1 = ColumnDataSource(data=dict(x=x, y=y1))
        source2 = ColumnDataSource(data=dict(x=x, y=y2))
        source_hl=[]
        x_hl,y_hl=horizontal_line(0,1,1)
        source_hl.append(ColumnDataSource(data=dict(x=x_hl, y=y_hl)))
        x_hl,y_hl=horizontal_line(0,1,2)
        source_hl.append(ColumnDataSource(data=dict(x=x_hl, y=y_hl)))
        
        n_vl=100
        source_vl=[]
        x_vl,y_vl=vertical_line(0,-2.5, 2.5)
        for i in range(n_vl):
            source_vl.append(ColumnDataSource(data=dict(x=x_vl, y=y_vl)))
        
        # Set up plot
        plot = figure(plot_height=800, plot_width=1200, title="Aero Lab Analysis",
                      x_axis_label='Distanz [km]', y_axis_label='Höhe [m]',
                      tools="crosshair,pan,reset,save,wheel_zoom,box_zoom")
        
        plot.line('x', 'y', source=source1, line_width=3, line_alpha=0.6,line_color='blue',legend="Höhe")
        plot.line('x', 'y', source=source2, line_width=3, line_alpha=0.6,line_color='red',legend="virtuelle Höhe")    
        l_hl=[]
        l_hl.append(plot.line('x', 'y', source=source_hl[0], line_width=3, line_alpha=0.6,line_color='orange'))
        l_hl.append(plot.line('x', 'y', source=source_hl[1], line_width=3, line_alpha=0.6,line_color='orange'))
        l_vl=[]
        for i in range(n_vl):
            l_vl.append(plot.line('x', 'y', source=source_vl[i], line_width=3, line_alpha=0.6,line_color='yellow'))
        l_hl[0].visible=False
        l_hl[1].visible=False    
        for i in range(n_vl):
            l_vl[i].visible=False
       
        #Set Init data
        File_Distance_Start0=File_Distance_Start
        File_Distance_End0=File_Distance_End
        m0=m_r+m_b
        cdA_Flat0=cdA_Flat
        cdA_Hill0=cdA_Hill
        cdA_Hill_Grade0=cdA_Hill_Grade
        Draft_Save0=Draft_Save
        Draft_Save_Grade0=Draft_Save_Grade
        cr0=cr
        eta0=eta
        T_Luft0=T_Luft
        v_w00=v_w0
        dir_w0=dir_w
        Winddamping0=Winddamping
        
        # Set up widgets
        AddStr=''
        if Use_AdvWeather: AddStr=' (not in use; Adv. Weather active)'
        Distance_Start_Slider = Slider(title="Distance Start", value=File_Distance_Start0, start=0, end=File_Distance_End0, step=1)
        Distance_End_Slider = Slider(title="Distance End", value=File_Distance_End0, start=0, end=File_Distance_End0, step=1)
        m_slider = Slider(title="m (Rider+Bike)", value=m0, start=0, end=150, step=0.5)
        cdA_Flat_slider = Slider(title="cdA Flat", value=cdA_Flat0, start=0.1, end=0.5, step=0.001, format="0[.]0000")
        cdA_Hill_slider = Slider(title="cdA Hill", value=cdA_Hill0, start=0.1, end=0.5, step=0.001, format="0[.]0000")
        cdA_Hill_Grade_slider = Slider(title="cdA Hill Grade", value=cdA_Hill_Grade0, start=0, end=5, step=0.1)
        Draft_Save_slider = Slider(title="Draft Save", value=Draft_Save0, start=0, end=100, step=1)
        Draft_Save_Grade_slider = Slider(title="Draft Save Grade", value=Draft_Save_Grade0, start=-10, end=10, step=1)
        cr_slider = Slider(title="cr", value=cr0, start=0.001, end=0.005, step=0.0001, format="0[.]00000")    
        eta_slider = Slider(title="Wirkungsgrad", value=eta0, start=90, end=100, step=0.2)
        T_Luft_slider = Slider(title="T Luft"+AddStr, value=T_Luft0, start=0, end=40, step=1)
        v_w0_slider = Slider(title="v Wind"+AddStr, value=v_w00, start=0, end=50, step=1)
        dir_w_slider = Slider(title="Windrichtung"+AddStr, value=dir_w0, start=0, end=360, step=5)
        Winddamping_slider = Slider(title="Winddamping", value=Winddamping0, start=0, end=1, step=0.05)
        reset_distance_button = Button(label="Reset Distance")
        reset_values_button = Button(label="Reset Values")
        
        Distance_Start_TextInput = TextInput(title="Distance Start", value=str(File_Distance_Start0))
        Distance_End_TextInput = TextInput(title="Distance End", value=str(File_Distance_End0))
        m_TextInput = TextInput(title="m (Rider+Bike)", value=str(m0))
        cdA_Flat_TextInput = TextInput(title="cdA Flat", value=str(cdA_Flat0))
        cdA_Hill_TextInput = TextInput(title="cdA Hill", value=str(cdA_Hill0))
        cdA_Hill_Grade_TextInput = TextInput(title="cdA Hill Grade", value=str(cdA_Hill_Grade0))
        Draft_Save_TextInput = TextInput(title="Draft Save", value=str(Draft_Save0))
        Draft_Save_Grade_TextInput = TextInput(title="Draft Save Grade", value=str(Draft_Save_Grade0))
        cr_TextInput = TextInput(title="cr", value=str(cr0))
        eta_TextInput = TextInput(title="Wirkungsgrad", value=str(eta0))
        T_Luft_TextInput = TextInput(title="T Luft"+AddStr, value=str(T_Luft0))
        v_w0_TextInput = TextInput(title="v Wind"+AddStr, value=str(v_w00))
        dir_w_TextInput = TextInput(title="Windrichtung"+AddStr, value=str(dir_w0))
        Winddamping_TextInput = TextInput(title="Winddamping", value=str(Winddamping0))
        
        hor_line_TextInput = TextInput(title="horizontal Line (Anzeigen (0/1),ymin,ymax)", value="0,1,2")
        vert_line_TextInput = TextInput(title="vertical Line (Anzahl (max 100),x Linie1,dx", value="0,0,1")     
        
        # Set up callbacks   
        def update_data_slider(attrname, old, new):
            # Get the current slider values
            File_Distance_Start = Distance_Start_Slider.value
            File_Distance_End = Distance_End_Slider.value
            m = m_slider.value
            cdA_Flat = cdA_Flat_slider.value
            cdA_Hill = cdA_Hill_slider.value
            cdA_Hill_Grade = cdA_Hill_Grade_slider.value
            Draft_Save = Draft_Save_slider.value
            Draft_Save_Grade = Draft_Save_Grade_slider.value
            cr = cr_slider.value
            eta = eta_slider.value
            T_Luft = T_Luft_slider.value
            v_w0 = v_w0_slider.value
            dir_w = dir_w_slider.value
            Winddamping = Winddamping_slider.value
            
            Distance_Start_TextInput.value=str(File_Distance_Start)
            Distance_End_TextInput.value=str(File_Distance_End)
            m_TextInput.value=str(m)
            cdA_Flat_TextInput.value=str(cdA_Flat)
            cdA_Hill_TextInput.value=str(cdA_Hill)
            cdA_Hill_Grade_TextInput.value=str(cdA_Hill_Grade)
            Draft_Save_TextInput.value=str(Draft_Save)
            Draft_Save_Grade_TextInput.value=str(Draft_Save_Grade)
            cr_TextInput.value=str(cr)
            eta_TextInput.value=str(eta)
            T_Luft_TextInput.value=str(T_Luft)
            v_w0_TextInput.value=str(v_w0)
            dir_w_TextInput.value=str(dir_w)
            Winddamping_TextInput.value=str(Winddamping)
            
            # Generate the new curves
            m_r=m-m_b
            Calc_Virtual_Elevation(File_Distance_Start,File_Distance_End,m_r,m_b,cr_dyn,cr,cdA_Flat,cdA_Hill,eta,cdA_Hill_Grade,Draft_Save_Grade,Draft_Save,T_Luft,v_w0,dir_w,Winddamping,Use_AdvWeather)
            x = np.array(distance[i_Start:i_End])
            y1 = np.array(elevation[i_Start:i_End])
            source1.data = dict(x=x, y=y1)            
            y2 = np.array(virtual_elevation[i_Start:i_End])        
            source2.data = dict(x=x, y=y2)

        def update_data_TextInput(attrname, old, new):
            # Get the current slider values
            File_Distance_Start = float(Distance_Start_TextInput.value)
            File_Distance_End = float(Distance_End_TextInput.value)
            m = float(m_TextInput.value)
            cdA_Flat = float(cdA_Flat_TextInput.value)
            cdA_Hill = float(cdA_Hill_TextInput.value)
            cdA_Hill_Grade = float(cdA_Hill_Grade_TextInput.value)
            Draft_Save = float(Draft_Save_TextInput.value)
            Draft_Save_Grade = float(Draft_Save_Grade_TextInput.value)
            cr = float(cr_TextInput.value)
            eta = float(eta_TextInput.value)
            T_Luft = float(T_Luft_TextInput.value)
            v_w0 = float(v_w0_TextInput.value)
            dir_w = float(dir_w_TextInput.value)
            Winddamping= float(Winddamping_TextInput.value)

            Distance_Start_Slider.value=File_Distance_Start
            Distance_End_Slider.value=File_Distance_End
            m_slider.value=m
            cdA_Flat_slider.value=cdA_Flat
            cdA_Hill_slider.value=cdA_Hill
            cdA_Hill_Grade_slider.value=cdA_Hill_Grade
            Draft_Save_slider.value=Draft_Save
            Draft_Save_Grade_slider.value=Draft_Save_Grade
            cr_slider.value=cr
            eta_slider.value=eta
            T_Luft_slider.value=T_Luft
            v_w0_slider.value=v_w0
            dir_w_slider.value=dir_w
            Winddamping_slider.value=Winddamping
            
            # Generate the new curves
            m_r=m-m_b
            Calc_Virtual_Elevation(File_Distance_Start,File_Distance_End,m_r,m_b,cr_dyn,cr,cdA_Flat,cdA_Hill,eta,cdA_Hill_Grade,Draft_Save_Grade,Draft_Save,T_Luft,v_w0,dir_w,Winddamping,Use_AdvWeather)
            x = np.array(distance[i_Start:i_End])
            y1 = np.array(elevation[i_Start:i_End])
            source1.data = dict(x=x, y=y1)            
            y2 = np.array(virtual_elevation[i_Start:i_End])        
            source2.data = dict(x=x, y=y2)
        
        for w in [Distance_Start_Slider,Distance_End_Slider,m_slider,cdA_Flat_slider,cdA_Hill_slider,cdA_Hill_Grade_slider,Draft_Save_slider,Draft_Save_Grade_slider,cr_slider,eta_slider,T_Luft_slider,v_w0_slider,dir_w_slider,Winddamping_slider]:
            w.on_change('value', update_data_slider)

        for w in [Distance_Start_TextInput,Distance_End_TextInput,m_TextInput,cdA_Flat_TextInput,cdA_Hill_TextInput,cdA_Hill_Grade_TextInput,Draft_Save_TextInput,Draft_Save_Grade_TextInput,cr_TextInput,eta_TextInput,T_Luft_TextInput,v_w0_TextInput,dir_w_TextInput,Winddamping_TextInput]:
            w.on_change('value', update_data_TextInput)
        
        def reset_values():
            #Reset Sliders
            m_slider.value = m0
            cdA_Flat_slider.value = cdA_Flat0
            cdA_Hill_slider.value = cdA_Hill0
            cdA_Hill_Grade_slider.value = cdA_Hill_Grade0
            Draft_Save_slider.value = Draft_Save0
            Draft_Save_Grade_slider.value = Draft_Save_Grade0
            cr_slider.value = cr0
            eta_slider.value = eta0
            T_Luft_slider.value = T_Luft0
            v_w0_slider.value = v_w00
            dir_w_slider.value = dir_w0
            Winddamping_slider.value = Winddamping0

            m_TextInput.value = str(m0)
            cdA_Flat_TextInput.value = str(cdA_Flat0)
            cdA_Hill_TextInput.value = str(cdA_Hill0)
            cdA_Hill_Grade_TextInput.value = str(cdA_Hill_Grade0)
            Draft_Save_TextInput.value = str(Draft_Save0)
            Draft_Save_Grade_TextInput.value = str(Draft_Save_Grade0)
            cr_TextInput.value = str(cr0)
            eta_TextInput.value = str(eta0)
            T_Luft_TextInput.value = str(T_Luft0)
            v_w0_TextInput.value = str(v_w00)
            dir_w_TextInput.value = str(dir_w0)
            Winddamping_TextInput.value = str(Winddamping0)                
            #Set Values
            File_Distance_Start = float(Distance_Start_Slider.value)
            File_Distance_End = float(Distance_End_Slider.value)
            m = m0
            cdA_Flat = cdA_Flat0
            cdA_Hill = cdA_Hill0
            cdA_Hill_Grade =cdA_Hill_Grade0
            Draft_Save = Draft_Save0
            Draft_Save_Grade = Draft_Save_Grade0
            cr = cr0
            eta = eta0
            T_Luft = T_Luft0
            v_w0 = v_w00
            dir_w = dir_w0
            Winddamping = Winddamping0
            # Generate the new curves
            m_r=m-m_b
            Calc_Virtual_Elevation(File_Distance_Start,File_Distance_End,m_r,m_b,cr_dyn,cr,cdA_Flat,cdA_Hill,eta,cdA_Hill_Grade,Draft_Save_Grade,Draft_Save,T_Luft,v_w0,dir_w,Winddamping,Use_AdvWeather)
            x = np.array(distance[i_Start:i_End])
            y1 = np.array(elevation[i_Start:i_End])
            source1.data = dict(x=x, y=y1)            
            y2 = np.array(virtual_elevation[i_Start:i_End])        
            source2.data = dict(x=x, y=y2)      
        
        reset_values_button.on_click(reset_values)
        
        def reset_distance():
            #Reset Sliders
            Distance_Start_Slider.value = File_Distance_Start0
            Distance_End_Slider.value = File_Distance_End0
            
            Distance_Start_TextInput.value = str(File_Distance_Start0)
            Distance_End_TextInput.value = str(File_Distance_End0)
            #Set Values
            File_Distance_Start = File_Distance_Start0
            File_Distance_End = File_Distance_End0
            m = float(m_slider.value)
            cdA_Flat = float(cdA_Flat_slider.value)
            cdA_Hill = float(cdA_Hill_slider.value)
            cdA_Hill_Grade = float(cdA_Hill_Grade_slider.value)
            Draft_Save = float(Draft_Save_slider.value)
            Draft_Save_Grade = float(Draft_Save_Grade_slider.value)
            cr = float(cr_slider.value)
            eta = float(eta_slider.value)
            T_Luft = float(T_Luft_slider.value)
            v_w0 = float(v_w0_slider.value)
            dir_w = float(dir_w_slider.value)
            Winddamping = float(Winddamping_slider.value)
            # Generate the new curves
            m_r=m-m_b
            Calc_Virtual_Elevation(File_Distance_Start,File_Distance_End,m_r,m_b,cr_dyn,cr,cdA_Flat,cdA_Hill,eta,cdA_Hill_Grade,Draft_Save_Grade,Draft_Save,T_Luft,v_w0,dir_w,Winddamping,Use_AdvWeather)
            x = np.array(distance[i_Start:i_End])
            y1 = np.array(elevation[i_Start:i_End])
            source1.data = dict(x=x, y=y1)            
            y2 = np.array(virtual_elevation[i_Start:i_End])        
            source2.data = dict(x=x, y=y2)       
        
        reset_distance_button.on_click(reset_distance)     
        
        def update_hor_lines(attrname, old, new):
            l_hl[0].visible=False
            l_hl[1].visible=False
            # Get values
            string = hor_line_TextInput.value
            string_list=string.split(",")    
            
            # Generate the new curve
            show=int(string_list[0])
            if show!=0:
                l_hl[0].visible=True
                l_hl[1].visible=True 
                y_val0=float(string_list[1])
                x_hl,y_hl=horizontal_line(min(x),max(x),y_val0)    
                source_hl[0].data = dict(x=x_hl, y=y_hl)
                y_val1=float(string_list[2])
                x_hl,y_hl=horizontal_line(min(x),max(x),y_val1) 
                source_hl[1].data = dict(x=x_hl, y=y_hl)
        
        hor_line_TextInput.on_change('value', update_hor_lines)    
        
        def update_vert_lines(attrname, old, new):
            for i in range(n_vl):
                l_vl[i].visible=False
            # Get values
            string = vert_line_TextInput.value
            string_list=string.split(",")    
            
            # Generate the new curve
            n_vl_vis=int(string_list[0])
            x0=float(string_list[1])
            dx=float(string_list[2])
            
            for i in range(n_vl_vis):
                x_vl,y_vl=vertical_line(x0+i*dx,min(y1),max(y1))
                source_vl[i].data = dict(x=x_vl, y=y_vl)  
                l_vl[i].visible=True
        
        vert_line_TextInput.on_change('value', update_vert_lines)           
        
        # Set up layouts and add to document
        inputs_Slider = column(Distance_Start_Slider,Distance_End_Slider,m_slider,cdA_Flat_slider,cdA_Hill_slider,cdA_Hill_Grade_slider,Draft_Save_slider,Draft_Save_Grade_slider,cr_slider,eta_slider,T_Luft_slider,v_w0_slider,dir_w_slider,Winddamping_slider,reset_distance_button,reset_values_button)
        inputs_TextInput = column(Distance_Start_TextInput,Distance_End_TextInput,m_TextInput,cdA_Flat_TextInput,cdA_Hill_TextInput,cdA_Hill_Grade_TextInput,Draft_Save_TextInput,Draft_Save_Grade_TextInput,cr_TextInput,eta_TextInput,T_Luft_TextInput,v_w0_TextInput,dir_w_TextInput,Winddamping_TextInput)
        inputs_add_Lines = row(hor_line_TextInput,vert_line_TextInput)
            
        curdoc().add_root(row(column(row(inputs_Slider, plot),inputs_add_Lines),inputs_TextInput,width=800))
        curdoc().title = "Aero_Lab_Sliders"     
        