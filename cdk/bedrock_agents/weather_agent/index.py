import json
import urllib3
import logging
import os
from datetime import datetime, timedelta

log_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
logging.basicConfig(
    format="[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

FUNCTION_NAMES = ["weatherforecast"]  # No API key required for Open-Meteo

def weatherforecast(lat, long, target_datetime):
    try:
        # Parse the target datetime
        target_dt = datetime.fromisoformat(target_datetime.replace('Z', '+00:00'))
        current_dt = datetime.utcnow()
        
        # Calculate the difference in days
        days_diff = (target_dt - current_dt).days
        
        # Open-Meteo API supports up to 16 days forecast
        if days_diff > 16:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Forecast only available for up to 16 days'})
            }
        
        # Format date for Open-Meteo API (YYYY-MM-DD)
        target_date = target_dt.strftime('%Y-%m-%d')
        
        # Open-Meteo API URL - no API key required
        # Using current weather and forecast endpoint
        if days_diff <= 0:  # Current weather
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={long}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&timezone=auto"
        else:  # Future forecast
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={long}&daily=temperature_2m_max,temperature_2m_min,weather_code,wind_speed_10m_max,relative_humidity_2m_mean&start_date={target_date}&end_date={target_date}&timezone=auto"
        
        http = urllib3.PoolManager()
        response = http.request('GET', url)
        data = json.loads(response.data.decode('utf-8'))
        
        # Weather code mapping for Open-Meteo
        def get_weather_description(weather_code):
            weather_codes = {
                0: "Clear sky",
                1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Fog", 48: "Depositing rime fog",
                51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
                56: "Light freezing drizzle", 57: "Dense freezing drizzle",
                61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                66: "Light freezing rain", 67: "Heavy freezing rain",
                71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
                77: "Snow grains",
                80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
                85: "Slight snow showers", 86: "Heavy snow showers",
                95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
            }
            return weather_codes.get(weather_code, "Unknown weather condition")
        
        if days_diff <= 0:  # Current weather
            current = data.get('current', {})
            weather_info = {
                'datetime': current_dt.isoformat(),
                'temperature': current.get('temperature_2m', 'N/A'),
                'feels_like': current.get('apparent_temperature', 'N/A'),
                'humidity': current.get('relative_humidity_2m', 'N/A'),
                'wind_speed': current.get('wind_speed_10m', 'N/A'),
                'weather_code': current.get('weather_code', 0),
                'weather_description': get_weather_description(current.get('weather_code', 0))
            }
        else:  # Future forecast
            daily = data.get('daily', {})
            if daily and len(daily.get('time', [])) > 0:
                weather_info = {
                    'datetime': target_dt.isoformat(),
                    'temperature_max': daily.get('temperature_2m_max', [None])[0],
                    'temperature_min': daily.get('temperature_2m_min', [None])[0],
                    'humidity': daily.get('relative_humidity_2m_mean', [None])[0],
                    'wind_speed': daily.get('wind_speed_10m_max', [None])[0],
                    'weather_code': daily.get('weather_code', [0])[0],
                    'weather_description': get_weather_description(daily.get('weather_code', [0])[0])
                }
            else:
                return {
                    'statusCode': 404,
                    'body': json.dumps({'error': 'No forecast available for the specified date'})
                }
        
        return {
            'statusCode': 200,
            'body': json.dumps(weather_info)
        }
        
    except Exception as e:
        logger.error(f"Error in weatherforecast: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Error fetching weather data: {str(e)}'})
        }

def lambda_handler(event, context):
    logging.info(f"{event=}")

    agent = event["agent"]
    actionGroup = event["actionGroup"]
    function = event["function"]
    parameters = event.get("parameters", [])
    responseBody = {"TEXT": {"body": "Error, no function was called"}}

    logger.info(f"{actionGroup=}, {function=}, {parameters=}")

    if function in FUNCTION_NAMES:
        if function == "weatherforecast":
            lat = None
            long = None
            target_datetime = None

            for param in parameters:
                if param["name"] == "lat":
                    lat = param["value"]
                elif param["name"] == "long":
                    long = param["value"]
                elif param["name"] == "target_datetime":
                    target_datetime = param["value"]

            if not lat or not long or not target_datetime:
                missing_params = []
                if not lat:
                    missing_params.append("lat")
                if not long:
                    missing_params.append("long")
                if not target_datetime:
                    missing_params.append("target_datetime")
                    
                responseBody = {
                    "TEXT": {"body": f"Missing mandatory parameter(s): {', '.join(missing_params)}"}
                }
            else:
                weather_response = weatherforecast(lat, long, target_datetime)
                logger.debug(f"Weather forecast: {weather_response=}")
                responseBody = {
                    "TEXT": {
                        "body": f"Weather forecast for coordinates ({lat}, {long}) at {target_datetime}: {weather_response['body']}"
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