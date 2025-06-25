import json
import boto3
import os
import logging
from boto3.dynamodb.conditions import Key
from datetime import datetime


log_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
logging.basicConfig(
    format="[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

FUNCTION_NAMES = []

try:
    FUNCTION_NAMES.append("fetch_location_alerts")
except Exception as e:
    api_key = None

dynamodb = boto3.resource('dynamodb')

def get_work_order(work_order_id):
    work_orders_table = dynamodb.Table(os.environ['WORK_ORDERS_TABLE_NAME'])
    return work_orders_table.get_item(
        Key={'work_order_id': work_order_id}
    ).get('Item', {})

def get_location_details(location_name):
    locations_table = dynamodb.Table(os.environ['LOCATIONS_TABLE_NAME'])
    return locations_table.get_item(
        Key={'location_name': location_name}
    ).get('Item', {})

def get_hazards_for_location(location_name):
    location_hazards_table = dynamodb.Table(os.environ['LOCATION_HAZARDS_TABLE_NAME'])
    hazards_table = dynamodb.Table(os.environ['HAZARDS_TABLE_NAME'])
    control_measures_table = dynamodb.Table(os.environ['CONTROL_MEASURES_TABLE_NAME'])
    
    location_hazards = location_hazards_table.query(
        KeyConditionExpression=Key('location_name').eq(location_name)
    )['Items']
    
    enriched_hazards = []
    for loc_hazard in location_hazards:
        hazard = hazards_table.get_item(
            Key={'hazard_id': loc_hazard['hazard_id']}
        ).get('Item', {})
        
        control_measures = control_measures_table.query(
            IndexName='LocationHazardIndex',
            KeyConditionExpression=Key('location_hazard_id').eq(loc_hazard['location_hazard_id'])
        )['Items']
        
        control_measures.sort(key=lambda x: x['implementation_date'], reverse=True)
        
        enriched_hazard = {
            'location_hazard_details': loc_hazard,
            'hazard_details': hazard,
            'control_measures': control_measures,
            'total_control_measures': len(control_measures),
            'active_control_measures': len([cm for cm in control_measures if cm['status'] == 'Active'])
        }
        enriched_hazards.append(enriched_hazard)
    
    risk_level_order = {'High': 3, 'Medium': 2, 'Low': 1}
    enriched_hazards.sort(
        key=lambda x: risk_level_order.get(x['location_hazard_details']['risk_level'], 0),
        reverse=True
    )
    
    return enriched_hazards

def get_incidents_for_location(location_name):
    incidents_table = dynamodb.Table(os.environ['INCIDENTS_TABLE_NAME'])
    incidents = incidents_table.query(
        IndexName='LocationIndex',
        KeyConditionExpression=Key('location_name').eq(location_name)
    )['Items']
    
    incidents.sort(key=lambda x: x['incident_date'], reverse=True)
    return incidents

def fetch_location_alerts(work_order_id):
    try:
        if not work_order_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Work order ID is required'
                })
            }
        
        # Get work order details
        work_order = get_work_order(work_order_id)
        if not work_order:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': f'Work order {work_order_id} not found'
                })
            }
        
        location_name = work_order.get('location_name')
        if not location_name:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': f'Location not found for work order {work_order_id}'
                })
            }
        
        # Get location details
        location = get_location_details(location_name)
        
        # Get hazards and control measures
        hazards = get_hazards_for_location(location_name)
        
        # Get incidents
        incidents = get_incidents_for_location(location_name)
        
        summary = {
            'total_hazards': len(hazards),
            'high_risk_hazards': len([h for h in hazards if h['location_hazard_details']['risk_level'] == 'High']),
            'total_incidents': len(incidents),
            'total_control_measures': sum(h['total_control_measures'] for h in hazards),
            'active_control_measures': sum(h['active_control_measures'] for h in hazards)
        }
        
        response = {
            'work_order': work_order,
            'location': location,
            'summary': summary,
            'hazards': hazards,
            'incidents': incidents,
            'retrieved_at': datetime.utcnow().isoformat()
        }
        
        return {
            'statusCode': 200,
            'body': json.dumps(response, default=str)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error querying data: {str(e)}'
            })
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
        if function == "fetch_location_alerts":
            work_order_id = None

            for param in parameters:
                if param["name"] == "work_order_id":
                    work_order_id = param["value"]

            if not work_order_id:
                missing_params = []
                if not work_order_id:
                    missing_params.append("work_order_id")                    
                responseBody = {
                    "TEXT": {"body": f"Missing mandatory parameter(s): {', '.join(missing_params)}"}
                }
            else:
                print(f"'{work_order_id}'")
                location_alert = fetch_location_alerts(work_order_id)
                logger.debug(f"Hazards at location {location_alert=}")
                responseBody = {
                    "TEXT": {
                        "body": f"Here are the alerts at the location for workorder '{work_order_id}' : {location_alert} "
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
