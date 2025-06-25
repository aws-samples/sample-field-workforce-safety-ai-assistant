import boto3
import json
import os
from datetime import datetime, timezone
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit



# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
WorkOrderTableName = os.getenv("WorkOrderTableName")
LocationTableName = os.getenv("LocationTableName")
work_orders_table = dynamodb.Table(WorkOrderTableName)
locations_table = dynamodb.Table(LocationTableName)


# Initialize Powertools utilities
POWERTOOLS_SERVICE_NAME = os.getenv("POWERTOOLS_SERVICE_NAME")
logger = Logger(service=POWERTOOLS_SERVICE_NAME)
tracer = Tracer(service=POWERTOOLS_SERVICE_NAME)
metrics = Metrics(namespace="WorkOrderNamespace")



@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event, context):
    """
    Lambda function to query work orders and their associated locations from DynamoDB.
    """
    try:
        # Define the current timestamp (UTC)
        current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
        logger.info(f"Current time: {current_time}")

        # Scan work orders table
        tracer.put_annotation("DynamoDBTable", "WorkOrders")
        work_orders_response = work_orders_table.scan()
        work_orders = work_orders_response.get('Items', [])
        logger.info(f"Retrieved {len(work_orders)} work orders")

        # Filter work orders based on the current date/time
       # filtered_work_orders = [
       #     order for order in work_orders 
       #     if order['scheduled_start_timestamp'] >= current_time
       # ]
       # logger.info(f"Filtered {len(filtered_work_orders)} work orders")

        # Query locations table to fetch location details
        tracer.put_annotation("DynamoDBTable", "Locations")
        locations_response = locations_table.scan()
        locations = {loc['location_name']: loc for loc in locations_response.get('Items', [])}
        logger.info(f"Retrieved {len(locations)} locations")

        # Add location details to each work order
        for order in work_orders:
            location_name = order.get('location_name')
            if location_name in locations:
                order['location_details'] = locations[location_name]
            else:
                order['location_details'] = None  # Handle missing location details

        # Record a metric for successful processing
        #metrics.add_metric(name="SuccessfulWorkOrdersQuery", unit=MetricUnit.Count, value=1)
        
         # Sort work orders by 'work_order_id'
        sorted_work_orders = sorted(work_orders, key=lambda x: x.get('work_order_id', ''))
        # Return the work_orders with CORS headers
        return {
            "statusCode": 200,
            "isBase64Encoded": False,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True,
            },
            "body": json.dumps(sorted_work_orders),
        }

    except Exception as e:
        logger.exception("Error querying DynamoDB")
        
        # Record a metric for failed processing
       # metrics.add_metric(name="FailedWorkOrdersQuery", unit=MetricUnit.Count, value=1)

        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
