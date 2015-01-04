from flask import Flask, request, make_response, render_template
from datetime import date, datetime, timedelta
import pytz
import json
import requests
import re
import os

app = Flask(__name__)

# ROUTES
@app.route('/plow-tracker-is-on/')
def plow_tracker_is_on():
    plow_page = requests.get('https://gisapps.cityofchicago.org/PlowTrackerWeb/PlowTrackerAccess')
 
    if plow_page.status_code is 200:
        plow_resp = {"date": str(datetime.now(pytz.timezone('US/Central')))}
        plow_resp["plow_tracker_is_on"] = len(re.findall('images/PlowTracker-Activated1.gif', plow_page.content)) == 0
 
        resp = make_response(json.dumps(plow_resp))
    else: 
        resp = make_response(json.dumps({'status': 'error', 'message': 'Failed to load plow tracker page.'}), 500)
 
    resp.headers['Content-Type'] = 'application/json'
    return resp

@app.route('/snow-plow-data/')
def snow_plow_data():

    # The feed for City Of Chicago's Plow Data
    gps_data_url = "https://gisapps.cityofchicago.org/PlowTrackerWeb/services/plowtrackerservice/getTrackingData"
    payload = {"TrackingDataInput":{"envelope":{"minX":0,"minY":0,"maxX":0,"maxY":0}}}
    response = requests.post(gps_data_url, data=json.dumps(payload))
    
    if response.status_code is 200:
        data_resp = {"date": str(datetime.now(pytz.timezone('US/Central')))}
        data_resp['data_present'] = False
        data_resp['assets'] = {}

        try:
          read_data = response.json()['TrackingDataResponse']['locationList']
          print read_data
          asset_types = set([a['assetType'] for a in read_data])
          
          for asset in asset_types:
            data_resp['assets'][asset] = {'type': asset, 'count': 0, 'vehicles': []}
            for vehicle in read_data:
                if vehicle['assetType'] == asset:
                    data_resp['assets'][asset]['vehicles'].append(vehicle)
                    data_resp['assets'][asset]['count'] += 1

          data_resp['asset_count'] = len(read_data)
          if len(read_data) > 0:
            data_resp['data_present'] = True
        except:
          print "Failed to read data."

        resp = make_response(json.dumps(data_resp))
    else: 
        resp = make_response(json.dumps({'status': 'error', 'message': 'Failed to load plow data page.'}), 500)
 
    resp.headers['Content-Type'] = 'application/json'
    return resp

@app.route('/')
def index():
    return render_app_template('index.html')

# UTILITY
def render_app_template(template, **kwargs):
    '''Add some goodies to all templates.'''

    if 'config' not in kwargs:
        kwargs['config'] = app.config
    return render_template(template, **kwargs)

# INIT
if __name__ == "__main__":
    app.run(debug=True, port=9999)
