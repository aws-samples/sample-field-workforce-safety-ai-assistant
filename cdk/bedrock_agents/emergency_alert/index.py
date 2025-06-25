import json
import urllib3
import math
import logging
import os
from datetime import datetime, timedelta

log_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
logging.basicConfig(
    format="[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

FUNCTION_NAMES = []

try:
    # Get API key from environment variable
    FUNCTION_NAMES.append("emvalert")
except Exception as e:
    print("Exception")


def emvalert(lat, long):
    search_point = (long, lat)

    # Download the GeoJSON data
    http = urllib3.PoolManager()
    response = http.request('GET', 'https://emergency.vic.gov.au/public/events-geojson.json')
    geojson_data = json.loads(response.data.decode('utf-8'))
    
    relevant_incidents = []
    
    for feature in geojson_data['features']:
        geometry = feature['geometry']
        
        if geometry['type'] == 'GeometryCollection':
            for geom in geometry['geometries']:
                if is_relevant(geom, search_point):
                    relevant_incidents.append(feature)
                    break
        else:
            if is_relevant(geometry, search_point):
                relevant_incidents.append(feature)
    
    return {
        'statusCode': 200,
        'body': json.dumps(relevant_incidents)
    }

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers

    # Convert inputs to float
    lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])

    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c
# Simplified check: if any point of the polygon is within 20 km, consider it relevant
def is_relevant(geometry, search_point):
    if geometry['type'] == 'Point':
        point_lon, point_lat = geometry['coordinates']
        distance = haversine_distance(float(search_point[1]), float(search_point[0]), float(point_lat), float(point_lon))
        return distance <= 20  # 5 km
    elif geometry['type'] == 'Polygon':
        
        for coord in geometry['coordinates'][0]:
            distance = haversine_distance(float(search_point[1]), float(search_point[0]), float(coord[1]), float(coord[0]))
            if distance <= 20:
                return True
    return False


def lambda_handler(event, context):
    logging.info(f"{event=}")

    agent = event["agent"]
    actionGroup = event["actionGroup"]
    function = event["function"]
    parameters = event.get("parameters", [])
    responseBody = {"TEXT": {"body": "Error, no function was called"}}

    logger.info(f"{actionGroup=}, {function=}, {parameters=}")

    if function in FUNCTION_NAMES:
        if function == "emvalert":
            lat = None
            long = None

            for param in parameters:
                if param["name"] == "lat":
                    lat = param["value"]
                if param["name"] == "long":
                    long = param["value"]

            if not lat or not long:
                missing_params = []
                if not lat:
                    missing_params.append("lat")
                if not long:
                    missing_params.append("long")
                responseBody = {
                    "TEXT": {"body": f"Missing mandatory parameter(s): {', '.join(missing_params)}"}
                }
            else:
                print(f"'{lat}','{long}'")
                forecast = emvalert(lat, long)
                logger.debug(f"EV Alerts {forecast=}")
                responseBody = {
                    "TEXT": {
                        "body": f"Here are the emergency alerts at : {forecast} "
                    }
                }

    action_response = {
        "actionGroup": actionGroup,
        "function": function,
        "functionResponse": {"responseBody": responseBody},
    }

    function_response = {
        "response": action_response,
        "messageVersion": event["messageVersion"],
    }

    logger.debug(f"lambda_handler: {function_response=}")

    return function_response