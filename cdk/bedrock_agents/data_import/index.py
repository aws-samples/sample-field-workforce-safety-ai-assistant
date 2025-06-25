import boto3
import csv
import json
import os
import io
from datetime import datetime, timedelta
import cfnresponse

dynamodb = boto3.resource('dynamodb')

def get_table(table_name):
    return dynamodb.Table(os.environ.get(f'{table_name}_TABLE_NAME'))

def read_csv_from_s3(bucket_name, key):
    s3_client = boto3.client('s3')
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        return list(csv.DictReader(io.TextIOWrapper(response['Body'], encoding='utf-8')))
    except Exception as e:
        print(f"Error reading {key} from S3: {str(e)}")
        return None
        
def update_work_order_dates(items):
    """
    Update work order dates to be 2 days in the future from the current date.
    This ensures work orders are always scheduled for future dates.
    """
    if not items:
        return items
        
    # Calculate the date 2 days from now
    future_date = datetime.now() + timedelta(days=2)
    
    for item in items:
        if 'scheduled_start_timestamp' in item:
            # Parse the original timestamp to keep the time portion
            original_dt = datetime.fromisoformat(item['scheduled_start_timestamp'].replace('Z', '+00:00'))
            
            # Create a new datetime with future date but same time
            new_dt = datetime(
                year=future_date.year,
                month=future_date.month,
                day=future_date.day,
                hour=original_dt.hour,
                minute=original_dt.minute,
                second=original_dt.second
            )
            
            # Update the timestamp
            item['scheduled_start_timestamp'] = new_dt.isoformat()
            
        if 'scheduled_finish_timestamp' in item:
            # Parse the original timestamp to keep the time portion
            original_dt = datetime.fromisoformat(item['scheduled_finish_timestamp'].replace('Z', '+00:00'))
            
            # Create a new datetime with future date but same time
            new_dt = datetime(
                year=future_date.year,
                month=future_date.month,
                day=future_date.day,
                hour=original_dt.hour,
                minute=original_dt.minute,
                second=original_dt.second
            )
            
            # Update the timestamp
            item['scheduled_finish_timestamp'] = new_dt.isoformat()
    
    return items

def batch_write_items(table, items):
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)

def handler(event, context):
    try:
        # Check if this is a CloudFormation custom resource request
        is_cfn_request = 'RequestType' in event
        
        print(f"Event: {json.dumps(event)}")
        print(f"Is CloudFormation request: {is_cfn_request}")
        
        # For CloudFormation Delete requests, just return success
        if is_cfn_request and event['RequestType'] == 'Delete':
            print("Delete request - nothing to do")
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {
                'Message': 'Nothing to do for Delete'
            })
            return
        
        # Proceed with data import for Create/Update or direct invocation
        s3_bucket = os.environ.get('S3_BUCKET_NAME')
        
        csv_files = {
            'work_orders': 'work_orders.csv',
            'locations': 'locations.csv',
            'hazards': 'hazards.csv',
            'incidents': 'incidents.csv',
            'assets': 'assets.csv',
            'location_hazards': 'location_hazards.csv',
            'control_measures': 'control_measures.csv'
        }
        
        results = {}
        for table_name, file_name in csv_files.items():
            items = read_csv_from_s3(s3_bucket, file_name)
            if items:
                # Update work order dates if this is the work_orders table
                if table_name == 'work_orders':
                    items = update_work_order_dates(items)
                    
                table = get_table(table_name.upper())
                batch_write_items(table, items)
                results[table_name] = len(items)
        
        response_data = {
            'message': 'Data import completed successfully',
            'records_imported': results
        }
        
        # If this is a CloudFormation request, send the appropriate response
        if is_cfn_request:
            print("Sending success response to CloudFormation")
            cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)
            return
        
        # For direct Lambda invocations, return a standard response
        return {
            'statusCode': 200,
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        error_message = str(e)
        print(f"Error: {error_message}")
        
        # If this is a CloudFormation request, send a failure response
        if 'RequestType' in event:
            print("Sending failure response to CloudFormation")
            cfnresponse.send(event, context, cfnresponse.FAILED, {
                'Error': error_message
            })
        
        # For direct Lambda invocations, return an error response
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error importing data: {error_message}')
        }
