"""
HSNW Dashboard - Spring 2024
Features:
Interaction between map and time series chart; allow multiple sensor selections.
Map with color schema based on average temperature over selected date range.
Calendar interaction works with all parameters.
Aggregate features includes weekly, daily, 12-hr, 6-hr, 3-hr, houly averages as well as 5-min readings.
Assigned a different line color to each location. Reading latest sensor readings data (iu_temp_data.csv).
Fixed rolling average plotting issue.
If you run this script locally, enter http://127.0.0.1:8050/ into browser to view viz in local machine.
"""
import numpy as np
import pandas as pd
import plotly.express as px
import math
from datetime import datetime, timedelta
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

ROLLING_AVERAGE_WINDOW = 4
monroe_county = dict(lat=39.1690, lon=-86.5200)
heat_index_bands = [
        dict(type='rect', y0=-20, y1=-10, fillcolor='#05014a', opacity=0.2, 
             name="Extreme Cold: Risk of frostbite and hypothermia. Dangerously cold conditions", layer='below'),
        dict(type='rect', y0=-10, y1=20, fillcolor='#00008B', opacity=0.2, 
             name="Very Cold: Risk of frostbite. Prolonged exposure may lead to hypothermia", layer='below'),
        dict(type='rect', y0=20, y1=40, fillcolor='#0000CD', opacity=0.2, 
             name="Cold: Risk of frostbite with prolonged exposure", layer='below'),
        dict(type='rect', y0=40, y1=60, fillcolor='#ADD8E6', opacity=0.2, 
             name="Cool: Generally comfortable, but dress warmly in cool conditions", layer='below'),
        dict(type='rect', y0=60, y1=80, fillcolor='#00FF00', opacity=0.2, 
             name="Comfortable: No discomfort expected", layer='below'),
        dict(type='rect', y0=80, y1=90, fillcolor='#FFFF00', opacity=0.2, 
             name="Caution: Fatigue possible with prolonged exposure and physical activity", layer='below'),
        dict(type='rect', y0=90, y1=105, fillcolor='#FFA500', opacity=0.2, 
             name="Extreme Caution: Heat cramps and heat exhaustion possible with prolonged exposure and physical activity", 
             layer='below'),
        dict(type='rect', y0=105, y1=130, fillcolor='#FF0000', opacity=0.2, 
             name="Danger: Heat stroke, heat cramps, and heat exhaustion likely with prolonged exposure and physical activity", 
             layer='below'),
        dict(type='rect', y0=130, y1=1000, fillcolor='#8b0000', opacity=0.2, 
             name="Extreme Danger: Heat stroke highly likely. Dangerously hot conditions", layer='below'),
    ]

readings = pd.read_csv("Data/iu_temp_data_truncated.csv", header=None, usecols=[1, 2, 3, 4, 6], skiprows=1, 
                       names = ["Date", "Temperature", "Rel Humidity", "Dew Point", "Sensor Id"])
sensors = pd.read_csv("Data/sensors.csv")
sensors = sensors[["sensorid", "name", "location", "latitude", "longitude"]]
sensors = sensors.rename(columns = {"sensorid": "Sensor Id", "name": "Name", "location": "Location", 
                                    "latitude": "Latitude", "longitude": "Longitude"})
sensor_locations_df = sensors[["Sensor Id", "Location"]]
sensor_locations = dict(zip(sensors["Sensor Id"], sensors["Location"]))
    
readings["Date"] = pd.to_datetime(readings["Date"])
readings = pd.merge(left = readings, right = sensor_locations_df, on = "Sensor Id", how = "inner")

readings_day = readings.groupby([readings['Date'].dt.date, readings["Location"]]).agg({"Temperature":["mean", "max", "min"],
                                    "Rel Humidity":["mean", "max", "min"],
                                    "Dew Point":["mean", "max", "min"]}).droplevel(axis=1, level=[1]).reset_index()
readings_day.columns = ["Date", "Location", "Temperature_mean", "Temperature_max", "Temperature_min", 
                        "Rel Humidity_mean", "Rel Humidity_max", "Rel Humidity_min", "Dew Point_mean", 
                        "Dew Point_max", "Dew Point_min"]

# Get the sensor subset
sensor_subset = pd.merge(
    readings.groupby(["Sensor Id"]).agg({"Date": ["min", "max"]}).droplevel(level=[0], axis=1).reset_index().sort_values(by = ["max"], ascending=[False]),
    sensors, on = "Sensor Id").drop_duplicates(subset=["Latitude", "Longitude"]).sort_values(by = "Location")[["Sensor Id", "Location"]]
sensor_subset.columns = ["value", "label"]
sensor_subset_as_options = sensor_subset.to_dict('records')


app = dash.Dash(__name__)
# app = app.server


@app.callback(
    Output('map-sensors', 'selectedData'),
    Input('map-sensors', 'figure'), 
)

def get_spatial_view(figure):
    start_date = readings_day["Date"].min()
    end_date = readings_day["Date"].max()
    readings_slice = readings_day.loc[(readings_day["Date"] >= start_date)
                                        & (readings_day["Date"] <= end_date)]
    
    sensors_geo = readings_slice.groupby("Location").agg({"Date": ["max"], "Temperature_mean": ["mean"]})\
        .droplevel(axis=1,level=[1]).reset_index()
    sensors_geo = pd.merge(sensors_geo, sensors[sensors["Location"].isin(sensors_geo["Location"])], on="Location")
    sensors_geo.sort_values(by="Date", ascending=False, inplace=True)
    sensors_geo = sensors_geo[~sensors_geo.duplicated(subset=['Latitude', 'Longitude'])]
    sensors_geo["Size"] = 80
    sensors_geo.columns = ['Location', 'Date', 'Temperature', 'Sensor Id', 'Name', 'Latitude', 'Longitude', 'Size']
    fig = px.scatter_mapbox(
        sensors_geo,
        lat='Latitude',
        lon='Longitude',
        text='Location',
        size='Size', #Fixed Size
        color='Temperature', 
        color_continuous_scale=px.colors.sequential.Bluered, 
        zoom=15,
        center={'lat': 39.1688, 'lon': -86.5210}, 
        size_max=9,
        hover_name="Location",
        hover_data=dict(Temperature=False,
                        Date=False,
                        Size = False,
                        Location = False,
                        Latitude = False,
                        Longitude = False)
    )
    fig.update_layout(title={'text': 'Spatial View Colored by Average Temperature Over Selected Dates', 
                            'font': {'size': 16}}, 
                      mapbox_style="open-street-map", height = 750, width = 725)
    fig.update_layout(clickmode='event+select')
    return fig



@app.callback(
    Output('map-sensors', 'figure', allow_duplicate=True), 
    Output('Temperature-Chart', 'figure'),
    Input('map-sensors', 'selectedData'), 
    Input('sel-temperature-metric-1', 'value'),
    Input('sel-duration-temperature-2', 'value'),
    Input('sel-smoothen-temperature-1', 'value'),
    Input('date-picker-temperature-1', 'start_date'),
    Input('date-picker-temperature-1', 'end_date'), 
    prevent_initial_call=True
)

def update_spatial_view_get_time_series(selectedData, metric, duration, smoothen, start_date, end_date):
    readings_slice = readings_day.loc[(readings_day["Date"] >= datetime.strptime(start_date, '%Y-%m-%d').date())
                                      & (readings_day["Date"] <= datetime.strptime(end_date, '%Y-%m-%d').date())]    
    sensors_geo = readings_slice.groupby("Location").agg({"Date": ["max"], "Temperature_mean": ["mean"]})\
        .droplevel(axis=1,level=[1]).reset_index()
    sensors_geo = pd.merge(sensors_geo, sensors[sensors["Location"].isin(sensors_geo["Location"])], on="Location")
    sensors_geo.sort_values(by="Date", ascending=False, inplace=True)
    sensors_geo = sensors_geo[~sensors_geo.duplicated(subset=['Latitude', 'Longitude'])]
    sensors_geo["Size"] = 80
    sensors_geo.columns = ['Location', 'Date', 'Temperature', 'Sensor Id', 'Name', 'Latitude', 'Longitude', 'Size']
    sv = px.scatter_mapbox(
        sensors_geo,
        lat='Latitude',
        lon='Longitude',
        text='Location',
        size='Size', #Fixed Size
        color='Temperature', 
        color_continuous_scale=px.colors.sequential.Bluered, 
        zoom=15,
        center={'lat': 39.1688, 'lon': -86.5210}, 
        size_max=9,
        hover_name="Location",
        hover_data=dict(Temperature=False,
                        Date=False,
                        Size = False,
                        Location = False,
                        Latitude = False,
                        Longitude = False)
    )
    sv.update_layout(title={'text': 'Spatial View Colored by Average Temperature Over Selected Dates', 
                            'font': {'size': 16}}, 
                     mapbox_style="open-street-map", height = 750, width = 725)
    sv.update_layout(clickmode='event+select')
    if selectedData is not None:
        if duration is None: duration = '2'
        if metric is None: metric = '1'
        if smoothen is None: smoothen = '1'
        field_mean, field_name, label_name, label_value = get_metric_field_names(metric)
        readings_slice = get_readings_slice(metric, duration, smoothen, start_date, end_date, field_mean, field_name)
        locations = []
        try:
            for i in range(len(selectedData['points'])):
                locations.append(selectedData['points'][i]['customdata'][3])
        except:
            for i in range(len(selectedData['data'][0]['customdata'])):
                locations.append(selectedData['data'][0]['customdata'][i][3])
        
        loc_colors = {'Cravens Hall Bus Stop': 'maroon', 
                      'Hodge Hall Bus Stop': 'red', 
                      'Biology Building': 'purple', 
                      'Campus River': 'fuchsia', 
                      'Fee Ln': 'green', 
                      'Merrill Hall': 'lime', 
                      'Myles Brand Parking Lot': 'darkorange', 
                      'Wells Library Parking Lot': 'navy', 
                      'Woodlawn': 'blue', 
                      'Dunn Meadow': 'teal', 
                      'Dunn Woods': 'aqua', 
                      'Luddy Hall Parking Lot': 'goldenrod', 
                      'Woodlawn Field': 'coral', 
                      'Bloomington Community Orchard': 'burlywood', 
                      'Willie Streeter Community Garden': 'cadetblue', 
                      'Jordan River Auditorium': 'sienna', 
                      'Opposite Teter Quad': 'darkgray'}
        
        ts = px.line()
        for loc in locations:
            df = readings_slice[readings_slice["Location"] == loc]
            if smoothen == '2':
                ts.add_scatter(x=df["Date"], y=df[field_name].rolling(window=ROLLING_AVERAGE_WINDOW).mean(), 
                               mode='lines', name=loc, line_color=loc_colors[loc])
            else:
                ts.add_scatter(x=df["Date"], y=df[field_name], mode='lines', name=loc, line_color=loc_colors[loc])
        
        ts.update_layout(
            title=label_value,
            yaxis=dict(showline=True, linewidth=2, linecolor='darkgray'),
            xaxis=dict(
                showline=True,
                linewidth=2,
                linecolor='darkgray',
                rangeslider=dict(visible=True),
                type="date",
            ),
        )
    else:
        if duration is None: duration = '2'
        if metric is None: metric = '1'
        if smoothen is None: smoothen = '1'
        field_mean, field_name, label_name, label_value = get_metric_field_names(metric)

        readings_slice = get_readings_slice(metric, duration, smoothen, start_date, end_date, field_mean, field_name)

        locations = list(np.sort(readings_day["Location"].unique()))
        
        loc_colors = {'Cravens Hall Bus Stop': 'maroon', 
                      'Hodge Hall Bus Stop': 'red', 
                      'Biology Building': 'purple', 
                      'Campus River': 'fuchsia', 
                      'Fee Ln': 'green', 
                      'Merrill Hall': 'lime', 
                      'Myles Brand Parking Lot': 'darkorange', 
                      'Wells Library Parking Lot': 'navy', 
                      'Woodlawn': 'blue', 
                      'Dunn Meadow': 'teal', 
                      'Dunn Woods': 'aqua', 
                      'Luddy Hall Parking Lot': 'goldenrod', 
                      'Woodlawn Field': 'coral', 
                      'Bloomington Community Orchard': 'burlywood', 
                      'Willie Streeter Community Garden': 'cadetblue', 
                      'Jordan River Auditorium': 'sienna', 
                      'Opposite Teter Quad': 'darkgray'}
        
        ts = px.line()
        for loc in locations:
            df = readings_slice[readings_slice["Location"] == loc]
            if smoothen == '2':
                ts.add_scatter(x=df["Date"], y=df[field_name].rolling(window=ROLLING_AVERAGE_WINDOW).mean(), 
                               mode='lines', name=loc, line_color=loc_colors[loc])
            else:
                ts.add_scatter(x=df["Date"], y=df[field_name], mode='lines', name=loc, line_color=loc_colors[loc])
        
        ts.update_layout(
            title=label_value,
            yaxis=dict(showline=True, linewidth=2, linecolor='darkgray'),
            xaxis=dict(
                showline=True,
                linewidth=2,
                linecolor='darkgray',
                rangeslider=dict(visible=True),
                type="date",
            ),
        )

    
    show_bands = True
    if show_bands and metric == '4':
        min_date = readings_slice["Date"].min()
        max_date = readings_slice["Date"].max()
        min_heat_index = readings_slice[field_name].min()
        max_heat_index = readings_slice[field_name].max()

        bands = [
            dict(type='rect', x0 = min_date, x1 = max_date, y0=40, y1=60, fillcolor='#ADD8E6', opacity=0.2, 
                 name="Cool: Generally comfortable, but dress warmly in cool conditions", layer='below'),
            dict(type='rect', x0 = min_date, x1 = max_date, y0=60, y1=80, fillcolor='#00FF00', opacity=0.2, 
                 name="Comfortable: No discomfort expected", layer='below'),
            dict(type='rect', x0 = min_date, x1 = max_date, y0=80, y1=90, fillcolor='#FFFF00', opacity=0.2, 
                 name="Caution: Fatigue possible with prolonged exposure and physical activity", layer='below'),
            dict(type='rect', x0 = min_date, x1 = max_date, y0=90, y1=105, fillcolor='#FFA500', opacity=0.2, 
                 name="Extreme Caution: Heat cramps and heat exhaustion possible with prolonged exposure and physical activity", 
                 layer='below'),
            dict(type='rect', x0 = min_date, x1 = max_date, y0=105, y1=130, fillcolor='#FF0000', opacity=0.2, 
                 name="Danger: Heat stroke, heat cramps, and heat exhaustion likely with prolonged exposure and physical activity", 
                 layer='below'),
            dict(type='rect', x0 = min_date, x1 = max_date, y0=130, y1=max_heat_index, fillcolor='#8b0000', opacity=0.2, 
                 name="Extreme Danger: Heat stroke highly likely. Dangerously hot conditions", layer='below'),
        ]

        for band in bands:
            ts.add_shape(band)

    ts.update_layout(showlegend=True, yaxis=dict(autorange=True, fixedrange=False), height = 750)
    return sv, ts


def get_readings_slice(metric, duration, smoothen, start_date, end_date, field_mean, field_name):
    if duration == '1': # weekly avg
        readings_slice = readings_day.loc[(readings_day["Date"] >= datetime.strptime(start_date, '%Y-%m-%d').date())
                                           & (readings_day["Date"] <= datetime.strptime(end_date, '%Y-%m-%d').date())].copy()
        readings_slice['Week'] = pd.to_datetime(readings_slice['Date']).dt.to_period('W')
        readings_slice['Week'] = readings_slice['Week'].apply(lambda x: x.start_time.date())
        readings_slice = readings_slice.groupby([readings_slice['Week'], readings_slice["Location"]]).agg(
            {"Temperature_mean": ["mean"], "Temperature_max": ["max"], "Temperature_min": ["min"], 
             "Rel Humidity_mean": ["mean"], "Rel Humidity_max": ["max"], "Rel Humidity_min": ["min"],
             "Dew Point_mean": ["mean"], "Dew Point_max": ["max"], "Dew Point_min": ["min"]}).droplevel(axis=1, 
                                                                                                        level=[1]).reset_index()
        readings_slice.columns = ["Date", "Location", "Temperature_mean", "Temperature_max", "Temperature_min",
                                  "Rel Humidity_mean", "Rel Humidity_max", "Rel Humidity_min", "Dew Point_mean",
                                  "Dew Point_max", "Dew Point_min"]
    
    elif duration == '2': # daily avg
        readings_slice = readings_day.loc[(readings_day["Date"] >= datetime.strptime(start_date, '%Y-%m-%d').date())
                                           & (readings_day["Date"] <= datetime.strptime(end_date, '%Y-%m-%d').date())]
        
    elif duration == '3': # 12-hr avg
        readings_slice = readings.loc[(readings["Date"] >= datetime.strptime(start_date + " 00:00:00", '%Y-%m-%d %H:%M:%S'))
                                      & (readings["Date"] <= datetime.strptime(end_date + " 23:59:59", '%Y-%m-%d %H:%M:%S'))].copy()
        readings_slice["Date"] = readings_slice["Date"].dt.round('12H')
        readings_slice["Date"] = readings_slice["Date"].dt.strftime('%Y-%m-%d %H:00:00')
    
    elif duration == '4': # 6-hr avg
        readings_slice = readings.loc[(readings["Date"] >= datetime.strptime(start_date + " 00:00:00", '%Y-%m-%d %H:%M:%S'))
                                      & (readings["Date"] <= datetime.strptime(end_date + " 23:59:59", '%Y-%m-%d %H:%M:%S'))].copy()
        readings_slice["Date"] = readings_slice["Date"].dt.round('6H')
        readings_slice["Date"] = readings_slice["Date"].dt.strftime('%Y-%m-%d %H:00:00')
    
    elif duration == '5': # 3-hr avg
        readings_slice = readings.loc[(readings["Date"] >= datetime.strptime(start_date + " 00:00:00", '%Y-%m-%d %H:%M:%S'))
                                      & (readings["Date"] <= datetime.strptime(end_date + " 23:59:59", '%Y-%m-%d %H:%M:%S'))].copy()
        readings_slice["Date"] = readings_slice["Date"].dt.round('3H')
        readings_slice["Date"] = readings_slice["Date"].dt.strftime('%Y-%m-%d %H:00:00')
    
    elif duration == '6': # hourly avg
        readings_slice = readings.loc[(readings["Date"] >= datetime.strptime(start_date + " 00:00:00", '%Y-%m-%d %H:%M:%S'))
                                      & (readings["Date"] <= datetime.strptime(end_date + " 23:59:59", '%Y-%m-%d %H:%M:%S'))].copy()
        readings_slice["Date"] = readings_slice["Date"].dt.strftime('%Y-%m-%d %H:00:00')

    elif duration == '7': # 5-min readings
        readings_slice = readings.loc[(readings["Date"] >= datetime.strptime(start_date + " 00:00:00", '%Y-%m-%d %H:%M:%S'))
            & (readings["Date"] <= datetime.strptime(end_date + " 23:59:59", '%Y-%m-%d %H:%M:%S'))]

    if duration in ('3', '4', '5', '6', '7'):
        readings_slice = readings_slice.groupby([readings_slice['Date'], readings_slice["Location"]]).agg(
            {"Temperature": ["mean", "max", "min"],
             "Rel Humidity": ["mean", "max", "min"],
             "Dew Point": ["mean", "max", "min"]}).droplevel(axis=1, level=[1]).reset_index()
        readings_slice.columns = ["Date", "Location", "Temperature_mean", "Temperature_max", "Temperature_min",
                                  "Rel Humidity_mean", "Rel Humidity_max", "Rel Humidity_min", "Dew Point_mean",
                                  "Dew Point_max", "Dew Point_min"]

    if metric == '4':
        readings_slice["Heat Index_mean"] = readings_slice.apply(lambda row: get_heat_index(row), axis=1)

    if metric == '5':
        readings_slice["Humidex_mean"] = readings_slice.apply(lambda row: get_humidex(row), axis=1)

    readings_slice = readings_slice[["Date", "Location", field_mean]]
    readings_slice.columns = ["Date", "Location", field_name]
    
    return readings_slice
    

def get_heat_index(row):
    temperature, humidity = row["Temperature_mean"], row["Rel Humidity_mean"]
    c = [-42.379, 2.04901523, 10.14333127, -0.22475541, -6.83783e-3,
         -5.481717e-2, 1.22874e-3, 8.5282e-4, -1.99e-6]
    t2 = temperature ** 2
    r2 = humidity ** 2
    heat_index = c[0] + c[1]*temperature + c[2]*humidity + c[3]*temperature*humidity + c[4]*t2 + c[5]*r2 + \
                    c[6]*t2*humidity + c[7]*temperature*r2 + c[8]*t2*r2
    return heat_index


def get_humidex(row):
    temperature, dewpoint = row["Temperature_mean"], row["Dew Point_mean"]
    temp_celsius = (temperature - 32) * 5/9
    dewpoint_celsius = (dewpoint - 32) * 5/9
    e = 6.11 * math.exp(5417.7530 * (1 / 273.15 - 1 / (273.15 + dewpoint_celsius)))
    h = 0.5555 * (e - 10.0)
    humidex = temp_celsius + h 
    return humidex


def get_metric_field_names(metric):
    field_mean, field_name = "Temperature_mean", "Temperature"
    label_name, label_value = "Temperature", "Temperature"
    if metric == '2':
        field_mean, field_name = "Rel Humidity_mean", "Rel Humidity"
        label_name, label_value = "Rel Humidity", "Relative Humidity"
    elif metric == '3':
        field_mean, field_name = "Dew Point_mean", "Dew Point"
        label_name, label_value = "Dew Point", "Dew Point"
    elif metric == '4':
        field_mean, field_name = "Heat Index_mean", "Heat Index"
        label_name, label_value = "Heat Index", "Heat Index"
    elif metric == '5':
        field_mean, field_name = "Humidex_mean", "Humidex"
        label_name, label_value = "Humidex", "Humidex"
    return field_mean, field_name, label_name, label_value



app.layout = html.Div([
    html.H1("Heat Sensor Network Data", style = {'font-family':'Arial','color':'blue', 'text-align':'center'}),
    html.Div([
        html.Div([
            html.H2("Sensor Locations", style={'font-family': 'Arial', 'color': 'darkred', 'padding-left': '20px'}),
            html.H4("Hold shift to select multiple locations", 
                    style={'font-family': 'Arial', 'color': 'darkred', 'padding-left': '20px'}), 
            html.H4("Triple-click a selected point or double-click an unselected one to revert to showing all lines", 
                    style={'font-family': 'Arial', 'color': 'darkred', 'padding-left': '20px'}),
            dcc.Graph(id='map-sensors',  
                       figure=get_spatial_view(None)), 
        ], 
        style={
                'backgroundColor': 'white',
                'border': '1px solid darkgray', 
                'flex': 'auto', 
                'box-shadow': '3px 3px 3px rgba(0, 0, 0, 0.2)'
        }), 
        html.Div([
            html.H2("Sensors Readings", style = {'font-family':'Arial', 'color':'darkred', 'padding-left':'20px'}), 
            html.Div([
                dcc.Dropdown(
                    id='sel-temperature-metric-1',
                    options=[{'label': 'Temperature', 'value': '1'},
                             {'label': 'Relative Humidity', 'value': '2'},
                             {'label': 'Dew Point', 'value': '3'},
                             {'label': 'Heat Index', 'value': '4'},
                             {'label': 'Humidex', 'value': '5'}],
                    value='1',
                    style={'font-family':'Arial', 'font-size':'11pt', 'width': '300px'},
                ),
                dcc.Dropdown(
                    id='sel-duration-temperature-2',
                    options=[{'label': 'Weekly Average', 'value': '1'}, 
                             {'label': 'Daily Average', 'value': '2'}, 
                              {'label': '12-hour Average', 'value': '3'}, 
                              {'label': '6-hour Average', 'value': '4'}, 
                              {'label': '3-hour Average', 'value': '5'}, 
                             {'label': 'Hourly Average', 'value': '6'},
                             {'label': 'Every 5 Mins. Readings', 'value': '7'}],
                    value='2',
                    style={'font-family':'Arial', 'font-size':'11pt', 'width': '300px'},
                ),
                dcc.Dropdown(
                    id='sel-smoothen-temperature-1',
                    options=[{'label': 'Raw', 'value': '1'},
                             {'label': 'Rolling Average', 'value': '2'}],
                    value='1',
                    style={'font-family':'Arial', 'font-size':'11pt', 'width': '300px'},
                ),
                dcc.DatePickerRange(
                    id='date-picker-temperature-1',
                    min_date_allowed=readings_day['Date'].min(),
                    max_date_allowed=readings_day['Date'].max(),
                    start_date=readings_day['Date'].min(),
                    end_date=readings_day['Date'].max(),
                    display_format='DD-MMM-YYYY',
                    minimum_nights=0,
                    style={'font-family':'Arial', 'font-size':'10pt'},
                )
            ], style={'padding': '10px', 'display': 'flex', 'justify-content': 'space-between'} 
            ), 
            html.Div([
                dcc.Graph(id='Temperature-Chart'),  
           
            ]), 
        ], style={
                  'backgroundColor': 'white', 
                  'border': '1px solid darkgray', 
                  'box-shadow': '3px 3px 3px rgba(0, 0, 0, 0.2)', 
                  'flex': 'auto'}
        )
    ], style={'display': 'flex', 
              'flex-direction': 'row', 
              'justify-contest': 'center'}
    )
])


if __name__ == '__main__':
    app.run_server(debug=False)

