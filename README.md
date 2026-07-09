import datetime
import numpy as np
from fitparse import FitFile
import gpxpy
from meteostat import Point, Hourly, Daily #pip install meteostat
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def import_gpx_file(file):
    gpx_file = open(file, 'r')
    gpx = gpxpy.parse(gpx_file)
    lat = []
    lon = []
    ele =[]
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                lat.append(point.latitude)
                lon.append(point.longitude)                   
                ele.append(point.elevation)
    print('Mittelwert der Koordinaten (latitude, longitude, elevation) der Aktivität ',round(np.average(lat),4),round(np.average(lon),4),round(np.average(ele),2))
    return np.average(lat),np.average(lon),np.average(ele),-1

def import_fit_file(file):
    fitfile = FitFile(file)
    date_and_time=[]
    lat=[]
    lon=[]
    ele =[]
    for record in fitfile.get_messages('record'):
        check_sum=0
        for record_data in record:
            if(record_data.name=='timestamp'):
                if isinstance(record_data.value, datetime.datetime):
                    da_ti=record_data.value
                    check_sum+=1                
            if(record_data.name=='position_lat'):
                if isinstance(record_data.value, float) or isinstance(record_data.value, int):                  
                    la=record_data.value *180/(2**31 ) #semicercles to deg
                    check_sum+=1
            if(record_data.name=='position_long'):
                if isinstance(record_data.value, float) or isinstance(record_data.value, int): 
                    lo=record_data.value *180/(2**31 ) #semicercles to deg
                    check_sum+=1
            if(record_data.name=='enhanced_altitude'):
                if isinstance(record_data.value, float) or isinstance(record_data.value, int): 
                    el=record_data.value
#                    print(record_data.name,record_data.value,record_data.units)
                    check_sum+=1                    
        if check_sum==4:
            date_and_time.append(da_ti)  
            lat.append(la)
            lon.append(lo)  
            ele.append(el)
    print('Mittelwert der Koordinaten (latitude, longitude, elevation) der Aktivität ',round(np.average(lat),4),round(np.average(lon),4),round(np.average(ele),2))
    print('Datum und Uhrzeit bei Aktivitätsbeginn',date_and_time[0])
    date=date_and_time[0].date()
    return np.average(lat),np.average(lon),np.average(ele),date

def import_gpx_or_fit_file(file):
    i=file.rfind('.')
    ext=file[i+1:]
    if ext=='gpx':
        lat_mean,lon_mean,ele_mean,date=import_gpx_file(file)
    else:
        lat_mean,lon_mean,ele_mean,date=import_fit_file(file)
    return lat_mean,lon_mean,ele_mean,date
    
def import_gpx_or_fit_file_and_OpenWebsite(file,date_entry,window):
    lat_mean,lon_mean,ele_mean,date_from_fit=import_gpx_or_fit_file(file)
    date_from_entry=date_entry.get()
    if date_from_entry!='':
        date=datetime.datetime.strptime(date_from_entry, '%Y-%m-%d')
        call_meteostat=True
#        print('date_from_entry eingetragen',date_from_entry)
    else:
        if isinstance(date_from_fit, int): #es handelt sich um eine GPX Datei; Es gibt also kein Datum in der Datei
            print('Bei einer GPX-Datei bitte immer ein Datum angeben.')
            date=0
            call_meteostat=False
        else:
            date=date_from_fit
            call_meteostat=True
    if call_meteostat: metostat_sub(lat_mean,lon_mean,ele_mean,date)
#    if call_website: webbrowser.open(website)
    window.destroy()

def metostat_sub(lat_mean,lon_mean,ele_mean,date):
    start = datetime.datetime(date.year,date.month,date.day)
    end = datetime.datetime(date.year,date.month,date.day,23,59) 
    location = Point(lat_mean,lon_mean,int(ele_mean))
    data = Hourly(location, start, end)
    data = data.fetch()
    data[['wdir']] = (data[['wdir']]+180) % 360
    print(data[['temp','wspd','wdir','rhum','pres']])
    data.plot(y=['temp', 'wspd'])
    plt.show()
    start = start-datetime.timedelta(days=7)
    end = end+datetime.timedelta(days=7)
    data = Daily(location, start, end)
    data = data.fetch()
    data.plot(y=['tavg', 'tmin', 'tmax'])
    plt.show()    

def main(file):
    bg_window='white'
    bg_Label1=bg_window
    window = tk.Tk()
    window.geometry('680x130')
    window['background'] = bg_window
    window.title('Tool to open historic weather on meteostat.net')    
    tk.Label(window,text='Show historical weahther data',bg=bg_window,fg='orange',font='Helvetica 26 bold').pack() #place(x=0, y=0)   
    tk.Label(window,text='Datum [YYYY-MM-DD] eingeben und <OK> drücken. Bei FIT Datei nichts eintragen, um Datum aus Datei zu verwenden',bg=bg_Label1).pack()
    date_entry=tk.Entry(window)
    date_entry.pack()    
    tk.Button(window,text='OK',command=lambda: import_gpx_or_fit_file_and_OpenWebsite(file,date_entry,window)).pack() #grid(row=2, column=1)
    tk.mainloop()
    
#main('C:/Users/broschb/Documents/PythonScripts/Eigene/Bike_Power/2023_06_25_Geplant_Ironman_70.3_Elsinore/IM 70.3 Elsinore Bike.gpx')
#main('C:/Users/broschb/Documents/PythonScripts/Eigene/Bike_Power/2022_08_28_Gemacht_Ironman_70.3_Duisburg/9495079099_ACTIVITY.fit')