import json
import urllib3
import math

def lambda_handler(event, context):
    event_body = json.loads(event["body"])
    # Parse the input coordinates and convert to float
    lat = float(event_body['latitude'])
    lon = float(event_body['longitude'])
    search_point = (lon, lat)

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
    print(relevant_incidents)
    return {
        'statusCode': 200,
        "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "true"
            },
        'body': json.dumps(relevant_incidents)
    }

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def is_relevant(geometry, search_point):
    if geometry['type'] == 'Point':
        point_lon, point_lat = geometry['coordinates']
        distance = haversine_distance(search_point[1], search_point[0], point_lat, point_lon)
        return distance <= 10  # 10 km
    elif geometry['type'] == 'Polygon':
        # Simplified check: if any point of the polygon is within 10 km, consider it relevant
        for coord in geometry['coordinates'][0]:
            distance = haversine_distance(search_point[1], search_point[0], coord[1], coord[0])
            if distance <= 10:
                return True
    return False
