from flask import Flask, request, make_response, render_template
from flask.ext.cache import Cache
from datetime import date, datetime, timedelta
from functools import update_wrapper
import pytz
import json
import requests
import re
import os

app = Flask(__name__)
cache = Cache(config={'CACHE_TYPE': 'simple'})
cache.init_app(app)
CACHE_TIMEOUT = 10 # 10 seconds

def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True): # pragma: no cover
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator

def make_cache_key(*args, **kwargs):
    path = request.path
    args = str(hash(frozenset(request.args.items())))
    # print 'cache_key:', (path+args)
    print (path + args).encode('utf-8')
    return (path + args).encode('utf-8')

# ROUTES
@app.route('/plow-tracker-is-on/')
@cache.cached(timeout=CACHE_TIMEOUT, key_prefix=make_cache_key)
@crossdomain(origin="*")
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
@cache.cached(timeout=CACHE_TIMEOUT, key_prefix=make_cache_key)
@crossdomain(origin="*")
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
