import json
import os
import logging
import boto3
from datetime import datetime
from typing import Dict, Any, Optional
import threading

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
logging.basicConfig(
    format="[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

# Import Strands SDK
try:
    from strands import Agent, tool
    from strands.models import BedrockModel
except ImportError as e:
    logger.error(f"Failed to import Strands SDK: {e}")
    # For deployment purposes, we'll handle this gracefully
    Agent = None
    tool = None
    BedrockModel = None

# Environment variables
COLLABORATOR_MODEL = os.environ.get("COLLABORATOR_MODEL", "anthropic.claude-3-sonnet-20240229-v1:0")
SUPERVISOR_MODEL = os.environ.get("SUPERVISOR_MODEL", "anthropic.claude-3-sonnet-20240229-v1:0")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# DynamoDB table names
WORK_ORDERS_TABLE = os.environ.get("WORK_ORDERS_TABLE")
LOCATIONS_TABLE = os.environ.get("LOCATIONS_TABLE")
HAZARDS_TABLE = os.environ.get("HAZARDS_TABLE")
INCIDENTS_TABLE = os.environ.get("INCIDENTS_TABLE")
ASSETS_TABLE = os.environ.get("ASSETS_TABLE")
LOCATION_HAZARDS_TABLE = os.environ.get("LOCATION_HAZARDS_TABLE")
CONTROL_MEASURES_TABLE = os.environ.get("CONTROL_MEASURES_TABLE")

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)

# Global variable to store streaming callback
streaming_callback = None

import threading

# Thread-local storage for WebSocket connections (secure for concurrent users)
thread_local_data = threading.local()

def send_streaming_update(update_type: str, content: str, tool_name: str = None):
    """Send streaming updates directly to the correct WebSocket connection (thread-safe)"""
    try:
        # Get connection details from thread-local storage
        connection_id = getattr(thread_local_data, 'connection_id', None)
        api_gateway_management_api = getattr(thread_local_data, 'api_gateway_management_api', None)
        
        if connection_id and api_gateway_management_api:
            try:
                # Send directly to the correct WebSocket connection
                api_gateway_management_api.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({
                        'type': 'trace',
                        'content': {
                            'trace': {
                                'orchestrationTrace': {
                                    'invocationInput': {
                                        'invocationType': tool_name or 'STRANDS_TOOL',
                                        'text': content
                                    }
                                }
                            }
                        },
                        'agentFramework': 'StrandsSDK'
                    })
                )
                logger.info(f"[STREAMING-{connection_id}] {update_type}: {content}")
            except Exception as e:
                logger.error(f"Error sending WebSocket message to {connection_id}: {str(e)}")
                # Fallback to logging with connection ID
                logger.info(f"[STREAMING-{connection_id}] {update_type}: {content} (tool: {tool_name})")
        else:
            # If no WebSocket connection, log the update for debugging
            logger.info(f"[STREAMING-NO-CONNECTION] {update_type}: {content} (tool: {tool_name})")
    except Exception as e:
        logger.error(f"Error in send_streaming_update: {str(e)}")
        logger.info(f"[STREAMING-ERROR] {update_type}: {content} (tool: {tool_name})")

# Weather API tool with streaming using Open-Meteo (no API key required)
@tool
def weather_forecast_tool(lat: str, long: str, target_datetime: str) -> str:
    """
    Get weather forecast for specific coordinates and datetime using Open-Meteo API.
    
    Args:
        lat: Latitude coordinate
        long: Longitude coordinate
        target_datetime: Target datetime in ISO format
        
    Returns:
        Weather forecast information
    """
    import urllib3
    import json
    from datetime import datetime
    
    send_streaming_update("trace", f"🌤️ Fetching weather forecast", "weather_forecast")
    
    try:
        # Parse the target datetime
        target_dt = datetime.fromisoformat(target_datetime.replace('Z', '+00:00'))
        current_dt = datetime.utcnow()
        
        # Calculate the difference in days
        days_diff = (target_dt - current_dt).days
        
        # Open-Meteo API supports up to 16 days forecast
        if days_diff > 16:
            return "Forecast only available for up to 16 days"
        
        # Format date for Open-Meteo API (YYYY-MM-DD)
        target_date = target_dt.strftime('%Y-%m-%d')
        
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
        
        # Open-Meteo API URL - no API key required
        if days_diff <= 0:  # Current weather
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={long}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&timezone=auto"
        else:  # Future forecast
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={long}&daily=temperature_2m_max,temperature_2m_min,weather_code,wind_speed_10m_max,relative_humidity_2m_mean&start_date={target_date}&end_date={target_date}&timezone=auto"
        
        http = urllib3.PoolManager()
        response = http.request('GET', url)
        data = json.loads(response.data.decode('utf-8'))
        
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
                return "No forecast available for the specified date"
        
        # Format weather description for display
        if days_diff <= 0:
            weather_desc = f"{weather_info['weather_description']}, {weather_info['temperature']}°C"
        else:
            weather_desc = f"{weather_info['weather_description']}, {weather_info['temperature_max']}°C/{weather_info['temperature_min']}°C"
        
        send_streaming_update("trace", f"✅ Weather: {weather_desc}", "weather_forecast")
        return json.dumps(weather_info, indent=2)
        
    except Exception as e:
        logger.error(f"Error in weather_forecast_tool: {str(e)}")
        send_streaming_update("trace", f"❌ Weather error: {str(e)}", "weather_forecast")
        return f"Error fetching weather data: {str(e)}"

@tool
def location_hazards_tool(work_order_id: str) -> str:
    """
    Get location hazards and incidents for a work order.
    
    Args:
        work_order_id: Work order ID to get location information
        
    Returns:
        Location hazards and incidents information
    """
    send_streaming_update("trace", f"🏢 Analyzing location hazards", "location_hazards")
    
    try:
        # Get work order details
        work_orders_table = dynamodb.Table(WORK_ORDERS_TABLE)
        work_order_response = work_orders_table.get_item(Key={'work_order_id': work_order_id})
        
        if 'Item' not in work_order_response:
            send_streaming_update("trace", f"❌ Work order {work_order_id} not found", "location_hazards")
            return f"Work order {work_order_id} not found"
            
        work_order = work_order_response['Item']
        location_name = work_order.get('location_name')
        
        if not location_name:
            return "No location associated with this work order"
        
        # Get location details
        locations_table = dynamodb.Table(LOCATIONS_TABLE)
        location_response = locations_table.get_item(Key={'location_name': location_name})
        location_info = location_response.get('Item', {})
        
        # Get hazards for this location using location_name
        location_hazards_table = dynamodb.Table(LOCATION_HAZARDS_TABLE)
        hazards_table = dynamodb.Table(HAZARDS_TABLE)
        control_measures_table = dynamodb.Table(CONTROL_MEASURES_TABLE)
        
        # Query location hazards by location_name
        location_hazards_response = location_hazards_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('location_name').eq(location_name)
        )
        location_hazards = location_hazards_response.get('Items', [])
        
        # Enrich hazards with detailed information and control measures
        enriched_hazards = []
        for loc_hazard in location_hazards:
            # Get hazard details
            hazard_response = hazards_table.get_item(Key={'hazard_id': loc_hazard['hazard_id']})
            hazard_details = hazard_response.get('Item', {})
            
            # Get control measures for this location hazard
            control_measures_response = control_measures_table.query(
                IndexName='LocationHazardIndex',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('location_hazard_id').eq(loc_hazard['location_hazard_id'])
            )
            control_measures = control_measures_response.get('Items', [])
            
            # Sort control measures by implementation date (most recent first)
            control_measures.sort(key=lambda x: x.get('implementation_date', ''), reverse=True)
            
            enriched_hazard = {
                'location_hazard_details': loc_hazard,
                'hazard_details': hazard_details,
                'control_measures': control_measures,
                'total_control_measures': len(control_measures),
                'active_control_measures': len([cm for cm in control_measures if cm.get('status') == 'Active'])
            }
            enriched_hazards.append(enriched_hazard)
        
        # Sort hazards by risk level (High > Medium > Low)
        risk_level_order = {'High': 3, 'Medium': 2, 'Low': 1}
        enriched_hazards.sort(
            key=lambda x: risk_level_order.get(x['location_hazard_details'].get('risk_level', 'Low'), 0),
            reverse=True
        )
        
        # Get incidents for this location using location_name
        incidents_table = dynamodb.Table(INCIDENTS_TABLE)
        incidents_response = incidents_table.query(
            IndexName='LocationIndex',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('location_name').eq(location_name)
        )
        incidents = incidents_response.get('Items', [])
        
        # Sort incidents by date (most recent first)
        incidents.sort(key=lambda x: x.get('incident_date', ''), reverse=True)
        
        # Create summary statistics
        summary = {
            'total_hazards': len(enriched_hazards),
            'high_risk_hazards': len([h for h in enriched_hazards if h['location_hazard_details'].get('risk_level') == 'High']),
            'total_incidents': len(incidents),
            'total_control_measures': sum(h['total_control_measures'] for h in enriched_hazards),
            'active_control_measures': sum(h['active_control_measures'] for h in enriched_hazards)
        }
        
        result = {
            'work_order': work_order,
            'location': location_info,
            'summary': summary,
            'hazards': enriched_hazards,
            'incidents': incidents,
            'retrieved_at': datetime.utcnow().isoformat()
        }
        
        send_streaming_update("trace", f"✅ Found {summary['total_hazards']} hazards, {summary['total_incidents']} incidents", "location_hazards")
        return json.dumps(result, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error in location_hazards_tool: {str(e)}")
        send_streaming_update("trace", f"❌ Location hazards error: {str(e)}", "location_hazards")
        return f"Error fetching location data: {str(e)}"

@tool
def emergency_alerts_tool(lat: str, long: str) -> str:
    """
    Get emergency alerts for specific coordinates using Victoria Emergency Services API.
    
    Args:
        lat: Latitude coordinate
        long: Longitude coordinate
        
    Returns:
        Emergency alerts information
    """
    import urllib3
    import math
    
    send_streaming_update("trace", f"🚨 Checking emergency alerts", "emergency_alerts")
    
    try:
        def haversine_distance(lat1, lon1, lat2, lon2):
            """Calculate the great circle distance between two points on earth"""
            R = 6371  # Earth's radius in kilometers
            
            # Convert inputs to float
            lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
            lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            return R * c
        
        def is_relevant(geometry, search_point):
            """Check if geometry is within 20km of search point"""
            if geometry['type'] == 'Point':
                point_lon, point_lat = geometry['coordinates']
                distance = haversine_distance(float(search_point[1]), float(search_point[0]), float(point_lat), float(point_lon))
                return distance <= 20  # 20 km radius
            elif geometry['type'] == 'Polygon':
                for coord in geometry['coordinates'][0]:
                    distance = haversine_distance(float(search_point[1]), float(search_point[0]), float(coord[1]), float(coord[0]))
                    if distance <= 20:
                        return True
            return False
        
        search_point = (float(long), float(lat))
        
        # Download the GeoJSON data from Victoria Emergency Services
        http = urllib3.PoolManager()
        response = http.request('GET', 'https://emergency.vic.gov.au/public/events-geojson.json')
        
        if response.status != 200:
            return json.dumps({
                'location': f"Lat: {lat}, Long: {long}",
                'alerts': [{
                    'type': 'service_unavailable',
                    'severity': 'info',
                    'description': 'Emergency services data temporarily unavailable',
                    'timestamp': datetime.utcnow().isoformat()
                }],
                'retrieved_at': datetime.utcnow().isoformat()
            }, indent=2)
        
        geojson_data = json.loads(response.data.decode('utf-8'))
        
        relevant_incidents = []
        
        for feature in geojson_data.get('features', []):
            geometry = feature.get('geometry', {})
            
            if geometry.get('type') == 'GeometryCollection':
                for geom in geometry.get('geometries', []):
                    if is_relevant(geom, search_point):
                        relevant_incidents.append(feature)
                        break
            else:
                if is_relevant(geometry, search_point):
                    relevant_incidents.append(feature)
        
        # Format the response
        if relevant_incidents:
            alerts = []
            for incident in relevant_incidents:
                properties = incident.get('properties', {})
                alert = {
                    'type': properties.get('category1', 'emergency'),
                    'severity': properties.get('status', 'unknown'),
                    'description': properties.get('title', 'Emergency incident'),
                    'location': properties.get('location', 'Location not specified'),
                    'timestamp': properties.get('sourceDateTime', datetime.utcnow().isoformat()),
                    'source': 'Victoria Emergency Services'
                }
                alerts.append(alert)
            
            emergency_info = {
                'location': f"Lat: {lat}, Long: {long}",
                'alerts': alerts,
                'total_alerts': len(alerts),
                'search_radius_km': 20,
                'retrieved_at': datetime.utcnow().isoformat()
            }
            
            send_streaming_update("trace", f"⚠️ Found {len(alerts)} emergency alerts", "emergency_alerts")
        else:
            emergency_info = {
                'location': f"Lat: {lat}, Long: {long}",
                'alerts': [{
                    'type': 'all_clear',
                    'severity': 'info',
                    'description': 'No active emergency alerts for this location',
                    'timestamp': datetime.utcnow().isoformat(),
                    'source': 'Victoria Emergency Services'
                }],
                'total_alerts': 0,
                'search_radius_km': 20,
                'retrieved_at': datetime.utcnow().isoformat()
            }
            
            send_streaming_update("trace", "✅ No emergency alerts found", "emergency_alerts")
        
        return json.dumps(emergency_info, indent=2)
        
    except Exception as e:
        logger.error(f"Error in emergency_alerts_tool: {str(e)}")
        send_streaming_update("trace", f"❌ Emergency alerts error: {str(e)}", "emergency_alerts")
        
        # Return fallback response on error
        fallback_info = {
            'location': f"Lat: {lat}, Long: {long}",
            'alerts': [{
                'type': 'service_error',
                'severity': 'warning',
                'description': f'Unable to retrieve emergency alerts: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            }],
            'error': str(e),
            'retrieved_at': datetime.utcnow().isoformat()
        }
        
        return json.dumps(fallback_info, indent=2)
        
    except Exception as e:
        logger.error(f"Error in emergency_alerts_tool: {str(e)}")
        send_streaming_update("trace", f"❌ Error fetching emergency alerts: {str(e)}", "emergency_alerts")
        return f"Error fetching emergency alerts: {str(e)}"



def create_supervisor_agent():
    """Create and configure the Strands supervisor agent with agent-as-tools pattern"""
    if not Agent or not BedrockModel:
        raise ImportError("Strands SDK not available")
        
    # Create Bedrock model instances
    #collaborator_model = BedrockModel(model_id=COLLABORATOR_MODEL)
    supervisor_model = BedrockModel(model_id=SUPERVISOR_MODEL)
    
    # Custom streaming callback handler for Strands
    def strands_callback_handler(**kwargs):
        """Handle Strands agent streaming events with detailed tracing"""
        try:
            if "data" in kwargs:
                # Stream text generation chunks
                chunk_data = kwargs["data"]
                #send_streaming_update("chunk", chunk_data, "text_generation")
                
            elif "current_tool_use" in kwargs:
                # Tool usage information with detailed context
                tool_info = kwargs["current_tool_use"]
                tool_name = tool_info.get("name", "unknown")
                tool_id = tool_info.get("toolUseId", "")
                
                # Create detailed tool usage message
                tool_message = f"🔧 Using tool: {tool_name}"
                
                # Add tool input details if available
                if "input" in tool_info and tool_info["input"]:
                    tool_input = tool_info["input"]
                    if isinstance(tool_input, dict):
                        # Format key inputs for display
                        input_parts = []
                        for key, value in tool_input.items():
                            if key in ['location', 'latitude', 'longitude', 'datetime', 'work_order_id']:
                                input_parts.append(f"{key}: {value}")
                        if input_parts:
                            tool_message += f" ({', '.join(input_parts)})"
                
               # send_streaming_update("trace", tool_message, "tool_usage")
                
            elif "tool_result" in kwargs:
                # Tool completion information
                result_info = kwargs["tool_result"]
                tool_name = result_info.get("name", "unknown")
                
                result_message = f"✅ Tool '{tool_name}' completed successfully"
                
                # Add result summary if available
                if "content" in result_info:
                    content = result_info["content"]
                    if isinstance(content, str) and len(content) > 0:
                        # Truncate long results for trace display
                        summary = content[:100] + "..." if len(content) > 100 else content
                        result_message += f" - {summary}"
                
               # send_streaming_update("trace", result_message, "tool_result")
                
            elif "thinking" in kwargs:
                # Agent reasoning/thinking process
                thinking_content = kwargs.get("thinking", "")
                if thinking_content and len(thinking_content.strip()) > 0:
                    thinking_message = f"🤔 Agent reasoning: {thinking_content}"
                   # send_streaming_update("trace", thinking_message, "reasoning")
                    
            elif "step" in kwargs:
                # Agent execution steps
                step_info = kwargs.get("step", "")
                if step_info:
                    step_message = f"📋 Processing step: {step_info}"
                   # send_streaming_update("trace", step_message, "step")
                    
        except Exception as e:
            logger.error(f"Error in callback handler: {str(e)}")
            # Send error trace
            #send_streaming_update("trace", f"⚠️ Callback error: {str(e)}", "error")
    
    # Create supervisor agent with tools and streaming callback
    supervisor_agent = Agent(
        model=supervisor_model,
        callback_handler=strands_callback_handler,
        system_prompt="""<role_definition>
Safety Report Supervisor | Input: WorkOrder Details JSON | Output: HTML Report
</role_definition>

<workflow>            
1. When you receive input message, extract agent function call parameters work_order_id, latitude, longitude, and target_datetime.
2. To perform safety briefing, Perform hazard, weather, and emergency checks using provided collaborator agents and valid parameters.
   location_hazards_tool - Call with only work_order_id to retrieve hazards for a work order location
   weather_forecast_tool - Call with latitude, longitude and target_datetime to retrieve weather forecast
   emergency_alerts_tool - Call with latitude, longitude to retrieve emergency warnings/alerts
3. Create a comprehensive HTML safety report based on all agent analyses
</workflow>

<outputreportformat>
You must format your final report using this exact HTML structure:
<div>
<h1>Safety Report for Work Order [work_order_id]</h1>
<section>
<h2>Location Alerts</h2>
<p>[Insert workorder location specific hazard, incident information here]</p>
</section>
<section>
<h2>Weather Forecast</h2>
<p>[Insert weather information and warnings here]</p>
</section>
<section>
<h2>Emergency Alerts</h2>
<p>[Insert emergency alert information here]</p>
</section>
<section>
<h2>Safety Recommendations</h2>
<p>[Insert Safety Recommendation, Location specific Control Measures here]</p>
</section>
</div>
</outputreportformat>

<critical_notes>
- STRICTLY FOLLOW <WORKFLOW> steps
- NEVER SHOW INTERNAL PROCESSING STEPS, Location Coordinates in the output report
- PRODUCE VALID HTML OUTPUT
</critical_notes>""",
        tools=[
            weather_forecast_tool,  # Weather specialist agent as tool
            location_hazards_tool,  # Location hazards specialist agent as tool
            emergency_alerts_tool,  # Emergency alerts specialist agent as tool
        ]
    )
    
    return supervisor_agent

def lambda_handler(event, context):
    """
    Lambda handler for Strands supervisor agent with streaming support
    """
    logger.info(f"Received event: {json.dumps(event, default=str)}")
    
    # Global WebSocket connection setup (Strands-specific) - using thread-local storage for security
    global thread_local_data
    
    try:
        # Handle different event sources
        if 'inputText' in event:
            # Direct invocation with inputText (similar to Bedrock agent format)
            input_text = event['inputText']
            session_id = event.get('sessionId', 'default-session')
            enable_streaming = event.get('enableStreaming', False)
            connection_id = event.get('connectionId')
            api_gateway_endpoint = event.get('apiGatewayEndpoint')
        elif 'body' in event:
            # API Gateway invocation
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            input_text = body.get('inputText', body.get('message', ''))
            session_id = body.get('sessionId', 'default-session')
            enable_streaming = body.get('enableStreaming', False)
            connection_id = body.get('connectionId')
            api_gateway_endpoint = body.get('apiGatewayEndpoint')
        else:
            # Direct message
            input_text = event.get('message', json.dumps(event))
            session_id = event.get('sessionId', 'default-session')
            enable_streaming = event.get('enableStreaming', False)
            connection_id = event.get('connectionId')
            api_gateway_endpoint = event.get('apiGatewayEndpoint')
        
        if not input_text:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No input text provided'})
            }
        
        # Set up WebSocket connection for direct streaming (Strands-specific) - thread-safe
        if enable_streaming and connection_id and api_gateway_endpoint:
            try:
                # Initialize API Gateway Management API client for direct WebSocket communication
                api_gateway_management_api = boto3.client(
                    'apigatewaymanagementapi',
                    endpoint_url=api_gateway_endpoint
                )
                
                # Store connection details in thread-local storage (secure for concurrent users)
                thread_local_data.connection_id = connection_id
                thread_local_data.api_gateway_management_api = api_gateway_management_api
                
                logger.info(f"WebSocket streaming enabled for connection: {connection_id}")
            except Exception as e:
                logger.error(f"Error setting up WebSocket connection: {str(e)}")
                # Clear thread-local data on error
                thread_local_data.connection_id = None
                thread_local_data.api_gateway_management_api = None
        else:
            # Clear thread-local data if streaming not enabled
            thread_local_data.connection_id = None
            thread_local_data.api_gateway_management_api = None
        
        # Send initial trace
        send_streaming_update("trace", "🚀 Initializing Safety Supervisor", "supervisor")
        
        # Create supervisor agent
        supervisor_agent = create_supervisor_agent()
        
        # Process the request
        logger.info(f"Processing input: {input_text[:100]}...")
        
        response = supervisor_agent(input_text)
        
        # Extract response content based on Strands response format
        response_content = None
        
        # Log the raw response for debugging
        logger.info(f"Raw Strands response type: {type(response)}")
        logger.info(f"Raw Strands response: {response}")
        
        # Handle the actual Strands response object structure
        if hasattr(response, 'content') and isinstance(response.content, list):
            # Strands format: response.content is an array of content items
            logger.info(f"Found response.content array with {len(response.content)} items")
            response_content = response.content
        elif hasattr(response, 'message'):
            # Fallback: use message attribute - wrap in content array format
            logger.info("Using response.message as fallback")
            response_content = [{"text": response.message}]
        else:
            # Last resort: stringify the response - wrap in content array format
            logger.info("Using stringified response as last resort")
            response_content = [{"text": str(response)}]
        
        # Format response to match the structure you showed: {"role":"assistant","content":[{"text":"..."}]}
        formatted_response = {
            "role": "assistant",
            "content": response_content
        }
        
        # Format final result
        result = {
            'statusCode': 200,
            'body': json.dumps({
                'sessionId': session_id,
                'response': formatted_response,  # Send the full structured response
                'timestamp': datetime.utcnow().isoformat(),
                'framework': 'StrandsSDK'
            })
        }
        
        logger.info(f"Generated response with content array length: {len(response_content) if response_content else 0}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error processing request: {str(e)}',
                'timestamp': datetime.utcnow().isoformat(),
                'framework': 'StrandsSDK'
            })
        }
