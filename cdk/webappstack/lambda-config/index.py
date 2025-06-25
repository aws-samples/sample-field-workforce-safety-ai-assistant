import json
import os
import boto3
from datetime import datetime

def lambda_handler(event, context):
    print(f'Event: {json.dumps(event)}')
    
    s3_client = boto3.client('s3')
    request_type = event['RequestType']
    
    if request_type in ['Create', 'Update']:
        try:
            # Get parameters from the event
            api_endpoint = event['ResourceProperties']['ApiEndpoint']
            workorder_api_endpoint = event['ResourceProperties']['WorkorderApiEndpoint']
            websocket_api_endpoint = event['ResourceProperties']['WebSocketApiEndpoint']
            region_name = event['ResourceProperties']['RegionName']
            cognito_user_pool_id = event['ResourceProperties']['CognitoUserPoolId']
            cognito_user_pool_client_id = event['ResourceProperties']['CognitoUserPoolClientId']
            cognito_identity_pool_id = event['ResourceProperties']['CognitoIdentityPoolId']
            cdn_distribution_url = event['ResourceProperties']['CdnDistributionUrl']
            s3_bucket_name = os.environ['S3_BUCKET_NAME']
            
            # Create runtime config.js with actual values
            print('Creating runtime config.js...')
            config_js_content = f'''// Runtime configuration - Generated at {datetime.now().isoformat()}
window.APP_CONFIG = {{
  VITE_API_ENDPOINT: "{api_endpoint}",
  VITE_WORKORDER_API_ENDPOINT: "{workorder_api_endpoint}",
  VITE_WEBSOCKET_API_ENDPOINT: "{websocket_api_endpoint}",
  VITE_REGION_NAME: "{region_name}",
  VITE_COGNITO_USER_POOL_ID: "{cognito_user_pool_id}",
  VITE_COGNITO_USER_POOL_CLIENT_ID: "{cognito_user_pool_client_id}",
  VITE_COGNITO_IDENTITY_POOL_ID: "{cognito_identity_pool_id}",
  VITE_API_NAME: "RestAPI",
  VITE_APP_NAME: "Field Workforce safety assistant",
  VITE_WorkOrder_API_NAME: "WorkOrderAPI",
  VITE_PROTOTYPE_NAME: "WorkOrderSafetyDemo",
  VITE_COGNITO_DOMAIN: ".auth.{region_name}.amazoncognito.com/",
  VITE_APP_REDIRECT_SIGN_IN_URL: "{cdn_distribution_url}",
  VITE_APP_REDIRECT_SIGN_OUT_URL: "{cdn_distribution_url}"
}};'''
            
            # Upload config.js to S3
            s3_client.put_object(
                Bucket=s3_bucket_name,
                Key='config.js',
                Body=config_js_content,
                ContentType='application/javascript'
            )
            
            print(f'Updated config.js in {s3_bucket_name}')
            
            return {
                'PhysicalResourceId': context.log_stream_name,
                'Data': {
                    'Message': 'Config.js updated successfully'
                }
            }
        except Exception as error:
            print(f'Error: {error}')
            raise error
    elif request_type == 'Delete':
        # Nothing to do for delete
        return {
            'PhysicalResourceId': event['PhysicalResourceId']
        }
