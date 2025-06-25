import json
import os
import boto3
import time
import requests
from datetime import datetime
import functools
import traceback
import re
from collections import OrderedDict
from boto3.dynamodb.conditions import Key
from jose import jwt
from botocore.config import Config
from aws_lambda_powertools import Logger
import uuid

# Initialize services and constants
logger = Logger()
def log(message):
    logger.info(message)
dynamodb = boto3.resource('dynamodb')
ws_connection_table = dynamodb.Table(os.environ['WS_CONNECTION_TABLE_NAME'])

# Environment variables - Support both frameworks
REGION = os.environ.get("REGION", "us-east-1")
USER_POOL_ID = os.environ.get("USER_POOL_ID", "")
CLIENT_ID = os.environ.get("CLIENT_ID", "")

# Bedrock Agent configuration
BEDROCK_AGENT_ID = os.environ.get("BEDROCK_AGENT_ID")
BEDROCK_AGENT_ALIAS_ID = os.environ.get("BEDROCK_AGENT_ALIAS_ID")

# Strands Agent configuration  
STRANDS_AGENT_ID = os.environ.get("STRANDS_AGENT_ID")
STRANDS_AGENT_ALIAS_ID = os.environ.get("STRANDS_AGENT_ALIAS_ID")

# Shared configuration
WORK_ORDERS_TABLE_NAME = os.environ.get("WORK_ORDERS_TABLE_NAME")




work_orders_table = dynamodb.Table(WORK_ORDERS_TABLE_NAME) if WORK_ORDERS_TABLE_NAME else None



def extract_html_content(text):
    """
    Extract HTML content from a text string if it exists.
    Returns the HTML content if found, otherwise returns the original text.
    """
    try:
        # Look for HTML content between <html> tags
        html_pattern = re.compile(r'<html>.*?</html>', re.DOTALL)
        html_match = html_pattern.search(text)
        
        if html_match:
            return html_match.group(0)
        
        # If no <html> tags, look for content between <body> tags
        body_pattern = re.compile(r'<body>.*?</body>', re.DOTALL)
        body_match = body_pattern.search(text)
        
        if body_match:
            return body_match.group(0)
        
        # If no <body> tags, look for any HTML-like content with multiple tags
        if '<div' in text and '</div>' in text:
            # This is a simple heuristic - if there are div tags, it's likely HTML content
            return text
            
        # Return original text if no HTML patterns found
        return text
    except Exception as e:
        logger.error(f"Error extracting HTML content: {str(e)}")
        return text  # Return original text on error

# Initialize clients for both frameworks (both are always deployed)
lambda_client = boto3.client('lambda', region_name=REGION)
bedrock_agent_runtime_client = boto3.client(
    'bedrock-agent-runtime',
    config=Config(
        retries={
            'max_attempts': 5, 
            'mode': 'standard' 
        },
        read_timeout=80,       
        connect_timeout=10,    
        region_name= REGION 
    )
)

def clean_html_response(raw_response):
    """
    Clean and format HTML response for proper display and storage
    """
    try:
        if not raw_response:
            return ""
        
        # Convert to string if not already
        response_text = str(raw_response)
        
        # Remove common formatting issues
        response_text = response_text.replace('\\n', '')  # Remove literal \n
        response_text = response_text.replace('\n', ' ')   # Replace actual newlines with spaces
        response_text = response_text.replace('\r', '')    # Remove carriage returns
        response_text = response_text.replace('\t', ' ')   # Replace tabs with spaces
        
        # Remove extra whitespace
        response_text = ' '.join(response_text.split())
        
        # Remove trailing characters like '}]}'
        response_text = response_text.rstrip('}])')
        
        # Remove leading/trailing quotes if present
        response_text = response_text.strip('"\'')
        
        # Find the start of HTML content
        html_start_patterns = ['<div', '<html', '<body', '<section', '<h1']
        start_index = -1
        
        for pattern in html_start_patterns:
            index = response_text.find(pattern)
            if index != -1:
                if start_index == -1 or index < start_index:
                    start_index = index
        
        if start_index > 0:
            response_text = response_text[start_index:]
        
        # Remove any text before the first HTML tag
        import re
        # Remove any non-HTML content at the beginning
        response_text = re.sub(r'^[^<]*(?=<)', '', response_text)
        
        # Ensure proper HTML structure
        if response_text and not response_text.startswith('<'):
            # If it doesn't start with HTML, wrap it
            response_text = f'<div>{response_text}</div>'
        
        # Remove any trailing non-HTML content
        last_tag_match = re.search(r'</[^>]+>(?=[^<]*$)', response_text)
        if last_tag_match:
            response_text = response_text[:last_tag_match.end()]
        
        return response_text.strip()
        
    except Exception as e:
        logger.error(f"Error cleaning HTML response: {str(e)}")
        return str(raw_response) if raw_response else ""

def invoke_strands_agent(payload, session_id, api_gateway_management, connection_id):
    """
    Invoke Strands agent via Lambda function with direct WebSocket streaming support
    """
    try:
        # Send initial processing message
        send_to_client(api_gateway_management, connection_id, {
            'type': 'trace',
            'content': {
                'trace': {
                    'orchestrationTrace': {
                        'invocationInput': {
                            'invocationType': 'STRANDS_AGENT',
                            'text': 'Initializing Strands Safety Supervisor Agent'
                        }
                    }
                }
            },
            'agentFramework': 'StrandsSDK'
        })
        
        # Prepare payload for Strands agent with WebSocket connection details
        modified_payload = {
            "inputText": payload,
            "sessionId": session_id,
            "connectionId": connection_id,
            "apiGatewayEndpoint": api_gateway_management.meta.endpoint_url,
            "enableStreaming": True
        }
        
        # Invoke Strands Lambda directly - it will handle streaming to WebSocket
        response = lambda_client.invoke(
            FunctionName=STRANDS_AGENT_ID,
            InvocationType='RequestResponse',
            Payload=json.dumps(modified_payload)
        )
        
        response_payload = json.loads(response['Payload'].read())
        
        if 'error' in response_payload:
            raise Exception(response_payload['error'])
        
        # Parse response
        if response_payload.get('statusCode') == 200:
            body = json.loads(response_payload['body'])
            
            # Handle Strands response format - extract from content array or response field
            completion = ''
            
            # Log the full response structure for debugging
            logger.info(f"Strands response body structure: {json.dumps(body, indent=2, default=str)}")
            
            if 'response' in body:
                # The response field contains the actual Strands response
                strands_response = body['response']
                logger.info(f"Strands response type: {type(strands_response)}")
                
                # Handle different response formats
                if isinstance(strands_response, dict):
                    # Check for content array in the response
                    if 'content' in strands_response and isinstance(strands_response['content'], list):
                        logger.info(f"Found content array with {len(strands_response['content'])} items")
                        # Extract text from content array
                        for content_item in strands_response['content']:
                            if isinstance(content_item, dict):
                                # Handle different content item structures
                                if 'text' in content_item:
                                    text_content = content_item['text']
                                    # Ensure text_content is a string
                                    if isinstance(text_content, str):
                                        completion += text_content
                                        logger.info(f"Extracted text content: {len(text_content)} characters")
                                    else:
                                        # Convert non-string to string
                                        text_str = str(text_content)
                                        completion += text_str
                                        logger.info(f"Converted and extracted text content: {len(text_str)} characters")
                                else:
                                    # If no 'text' field, stringify the entire item
                                    item_str = str(content_item)
                                    completion += item_str
                                    logger.info(f"Stringified content item: {len(item_str)} characters")
                            elif isinstance(content_item, str):
                                completion += content_item
                                logger.info(f"Added string content item: {len(content_item)} characters")
                            else:
                                # Convert any other type to string
                                item_str = str(content_item)
                                completion += item_str
                                logger.info(f"Converted content item to string: {len(item_str)} characters")
                    elif 'message' in strands_response:
                        message_content = strands_response['message']
                        completion = str(message_content) if not isinstance(message_content, str) else message_content
                    else:
                        # Stringify the entire response object
                        completion = json.dumps(strands_response)
                elif isinstance(strands_response, str):
                    completion = strands_response
                else:
                    completion = str(strands_response)
            elif 'content' in body and isinstance(body['content'], list):
                # Direct content array in body
                for content_item in body['content']:
                    if isinstance(content_item, dict):
                        if content_item.get('type') == 'text' and 'text' in content_item:
                            text_content = content_item['text']
                            completion += str(text_content) if not isinstance(text_content, str) else text_content
                        elif 'text' in content_item:
                            text_content = content_item['text']
                            completion += str(text_content) if not isinstance(text_content, str) else text_content
                    elif isinstance(content_item, str):
                        completion += content_item
                    else:
                        completion += str(content_item)
            elif 'message' in body:
                # Alternative: message field
                message_content = body['message']
                completion = str(message_content) if not isinstance(message_content, str) else message_content
            else:
                # Last resort: stringify the entire body
                completion = json.dumps(body)
                logger.warning(f"Using fallback response extraction: {completion[:200]}...")
            
            logger.info(f"Final extracted completion length: {len(completion)} characters")
            logger.info(f"Final completion preview: {completion[:200]}...")
            
            # Clean the HTML response before sending and storing
            cleaned_completion = clean_html_response(completion)
            logger.info(f"Cleaned completion length: {len(cleaned_completion)} characters")
            logger.info(f"Cleaned completion preview: {cleaned_completion[:200]}...")
            
            # Send final completion using the same format as Bedrock Agent
            request_id = f"ws-strands-{connection_id}-{int(time.time())}"
            send_to_client(api_gateway_management, connection_id, {
                'type': 'final',
                'requestId': request_id,
                'status': 'COMPLETED',
                'safetyCheckResponse': cleaned_completion,  # Send cleaned response
                'safetyCheckPerformedAt': datetime.now().isoformat(),
                'agentFramework': 'StrandsSDK'
            })
            
            return cleaned_completion  # Return cleaned response for database storage
        else:
            error_msg = f"Strands agent error: {response_payload.get('body', 'Unknown error')}"
            logger.error(error_msg)
            send_to_client(api_gateway_management, connection_id, {
                'type': 'error',
                'safetyCheckResponse': error_msg,
                'agentFramework': 'StrandsSDK'
            })
            return error_msg
            
    except Exception as e:
        error_msg = f"Error invoking Strands agent: {str(e)}"
        logger.error(error_msg)
        send_to_client(api_gateway_management, connection_id, {
            'type': 'error',
            'safetyCheckResponse': error_msg,
            'agentFramework': 'StrandsSDK'
        })
        return error_msg


# This function was incorrectly named - it was actually a Strands function
# The correct invoke_bedrock_agent function is defined below
            
def invoke_bedrock_agent(payload, session_id, api_gateway_management, connection_id):
    """
    Invoke Bedrock agent (existing implementation)
    """
    try:
        # Validate Bedrock agent IDs
        if not BEDROCK_AGENT_ID or not BEDROCK_AGENT_ALIAS_ID:
            error_msg = f"Bedrock agent IDs not configured. BEDROCK_AGENT_ID: {BEDROCK_AGENT_ID}, BEDROCK_AGENT_ALIAS_ID: {BEDROCK_AGENT_ALIAS_ID}"
            logger.error(error_msg)
            send_to_client(api_gateway_management, connection_id, {
                'type': 'error',
                'message': error_msg,
                'agentFramework': 'BedrockAgent'
            })
            return error_msg
            
        # Log the agent IDs being used
        logger.info(f"Using Bedrock Agent ID: {BEDROCK_AGENT_ID}, Alias ID: {BEDROCK_AGENT_ALIAS_ID}")
            
        # Prepare input parameters for Bedrock agent
        input_params = {
            "inputText": payload,
            "agentId": BEDROCK_AGENT_ID,
            "agentAliasId": BEDROCK_AGENT_ALIAS_ID,
            "sessionId": session_id,
            "enableTrace": True
        }

        # Invoke the agent API
        response = bedrock_agent_runtime_client.invoke_agent(**input_params)

        completion = ""
        
        # Process the response chunks
        for event_item in response['completion']:
            if 'chunk' in event_item:
                chunk = event_item['chunk']
                if 'bytes' in chunk:
                    chunk_data = chunk['bytes'].decode('utf-8')
                    completion += chunk_data
            
            if 'trace' in event_item:
                trace = event_item['trace']
                timestamp = int(time.time() * 1000)
                # Send only orchestration trace, then send to client.
                send_to_client(api_gateway_management, connection_id, {
                    'type': 'trace',
                    'content': trace,
                    'agentFramework': 'BedrockAgent'
                })

        return completion
        
    except Exception as e:
        error_msg = f"Error invoking Bedrock agent: {str(e)}"
        logger.error(error_msg)
        send_to_client(api_gateway_management, connection_id, {
            'type': 'error',
            'content': error_msg,
            'agentFramework': 'BedrockAgent'
        })
        return error_msg

def verify_token(token: str) -> dict:
    try:
        url = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
        # Add timeout parameter to prevent hanging connections
        
        response = requests.get(url, timeout=15)
        response.raise_for_status()  # Raise exception for non-200 responses
        
        keys = response.json().get("keys", [])
        if not keys:
            raise ValueError("No keys found in JWKS response")
            
        header = jwt.get_unverified_header(token)
        if not header or "kid" not in header:
            raise ValueError("Invalid token header")
            
        matching_keys = [k for k in keys if k.get("kid") == header.get("kid")]
        if not matching_keys:
            raise ValueError(f"No matching key found for kid: {header.get('kid')}")
            
        key = matching_keys[0]
        
        decoded = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_at_hash": False},
            audience=CLIENT_ID,
        )
        return decoded
    except requests.RequestException as e:
        logger.error(f"Error fetching JWKS: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise

def handle_connect(connection_id):
    try:
        logger.info(f"Adding new connection entry to DynamoDB for {connection_id}")
        ws_connection_table.put_item(
            Item={
                'connectionId': connection_id,
                'ttl': int(time.time()) + 10 * 60,  # 10 minute TTL (comment says 24 hour but code was 10 min)
                'timestamp': str(datetime.now())
            }
        )
        return {'statusCode': 200, 'body': 'Connected'}
    except Exception as e:
        logger.error(f"Connection handling error: {str(e)}")
        logger.error(traceback.format_exc())
        return {'statusCode': 200, 'body': 'Connected'}

def handle_disconnect(connection_id):
    try:
        logger.info(f"Removing connection {connection_id} from DynamoDB")
        ws_connection_table.delete_item(Key={'connectionId': connection_id})
        return {'statusCode': 200, 'body': 'Disconnected'}
    except Exception as e:
        logger.error(f"Disconnect handling error: {str(e)}")
        logger.error(traceback.format_exc())
        return {'statusCode': 200, 'body': 'Disconnected'}

def handle_message(api_gateway_management, connection_id, event):
    try:
        # Parse request body
        event_body = json.loads(event["body"])

        session_id = event_body.get('session_id', str(uuid.uuid4()))
        

        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        payload = json.dumps(event_body)

        try:
            workOrderDetails = event_body['workOrderDetails']
            # Create prompt string for workorder details
            payload = f"{json.dumps(workOrderDetails)}"    
        except Exception as ex:
            logger.error(f"Error in getting work order: {str(ex)}")

        # Get the requested framework from the frontend
        requested_framework = event_body.get('agentFramework', 'BedrockAgent')
        
        # Route to appropriate agent based on framework selection
        if requested_framework == "StrandsSDK":
            completion = invoke_strands_agent(payload, session_id, api_gateway_management, connection_id)
        else:
            completion = invoke_bedrock_agent(payload, session_id, api_gateway_management, connection_id)

        # Get current timestamp in ISO format
        current_time = datetime.now().isoformat()
        # Store safety check response in WorkOrders table if available
        try:
            if work_orders_table and 'workOrderDetails' in event_body:
                work_order_id = event_body['workOrderDetails'].get('work_order_id')
                if work_order_id:
                    
                    
                    # Extract HTML content if it exists
                    processed_response = extract_html_content(completion)
                    
                    logger.info(f"Updating WorkOrders table for work_order_id: {work_order_id}")
                    # Update the WorkOrders table with the safety check response and timestamp
                    work_orders_table.update_item(
                        Key={'work_order_id': work_order_id},
                        UpdateExpression="set safetyCheckResponse = :r, safetyCheckPerformedAt = :p",
                        ExpressionAttributeValues={
                            ':r': processed_response,
                            ':p': current_time
                        }
                    )
                    logger.info(f"Successfully updated WorkOrders table for work_order_id: {work_order_id} at {current_time}")
                else:
                    logger.warning("No work_order_id found in workOrderDetails")
            elif not work_orders_table:
                logger.warning("WorkOrders table not configured, skipping update")
            else:
                logger.warning("No workOrderDetails in event body, skipping update")
        except Exception as table_error:
            logger.error(f"Error updating WorkOrders table: {str(table_error)}")
            logger.error(traceback.format_exc())
            # Continue execution even if table update fails

        # Send final completion with agent framework information
        request_id = f"ws-{connection_id}-{int(time.time())}"
        send_to_client(api_gateway_management, connection_id, {
            'type': 'final',
            'requestId': request_id,
            'status': 'COMPLETED',
            'safetyCheckResponse': completion,
            'safetyCheckPerformedAt': current_time,
            'agentFramework': requested_framework  # Use the requested framework
        })
        

        
        return {'statusCode': 200, 'body': 'Message sent'}
                
    except Exception as e:
        logger.error(f"handle_messageerror: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Use the requested framework for error message
        error_framework = event_body.get('agentFramework', 'BedrockAgent') if 'event_body' in locals() else 'BedrockAgent'
        
        send_to_client(api_gateway_management, connection_id, {
            'type': 'error',
            'requestId': request_id,
            'status': 'COMPLETED',
            'safetyCheckResponse': "Error in performing safety check::"+str(e),
            'agentFramework': error_framework
        })
        return {'statusCode': 500, 'body': f'Failed to process message: {str(e)}'}

def send_to_client(api_gateway_management, connection_id, message):
    """Send message to WebSocket client"""
    try:
        # Convert datetime to string before JSON serialization
        current_time = str(datetime.now())
        
        api_gateway_management.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({
                'message': message,
                'sender': connection_id,
                'timestamp': current_time  # Use string instead of datetime object
            }, default=str)  # Add default=str to handle any other non-serializable objects
        )
        
       # logger.info(f"Message sent to {connection_id}: {message['type']}")
    except api_gateway_management.exceptions.GoneException:
        # Connection is no longer valid
        logger.warning(f"Connection {connection_id} is invalid (GoneException).")
        try:
            ws_connection_table.delete_item(Key={'connectionId': connection_id})
        except Exception as e:
            logger.error(f"Error deleting stale connection: {str(e)}")
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        logger.error(traceback.format_exc())
        # Don't re-raise the exception to prevent Lambda failure
        # This allows the function to continue processing even if one message fails

@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        # Log the incoming event for debugging
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        # Safely get requestContext or raise a more descriptive error
        if 'requestContext' not in event:
            logger.error(f"Missing requestContext in event: {event}")
            return {'statusCode': 400, 'body': 'Invalid WebSocket event structure'}
            
        request_context = event['requestContext']
        route_key = request_context.get('routeKey')
        connection_id = request_context.get('connectionId')
        
        if not route_key or not connection_id:
            logger.error(f"Missing required fields in requestContext: {request_context}")
            return {'statusCode': 400, 'body': 'Missing required WebSocket fields'}

        if route_key == '$connect':
            logger.info(f"New connection: {connection_id}")
            return handle_connect(connection_id)
        elif route_key == '$disconnect':
            logger.info(f"Disconnection: {connection_id}")
            return handle_disconnect(connection_id)
        elif route_key == '$default':
            # Check if body exists and is valid JSON
            if 'body' not in event or not event['body']:
                logger.error("Missing or empty body in event")
                return {'statusCode': 400, 'body': 'Missing request body'}
                
            try:
                message = json.loads(event['body'])
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in body: {str(e)}")
                return {'statusCode': 400, 'body': 'Invalid JSON in request body'}
            
            # Check if the message is a heartbeat
            if message.get('messageType') == 'heartbeat':
                logger.info(f"Heartbeat received from {connection_id}")
                return {
                    'statusCode': 200,
                    'body': json.dumps({'message': 'Heartbeat received, no action taken'})
                }
                   
            # Initialize API client
            api_client = None
            logger.info(f"Processing message from {connection_id}")
            
            if request_context.get('domainName') and request_context.get('stage'):
                domain_name = request_context['domainName']
                stage = request_context['stage']
                api_client = boto3.client(
                    'apigatewaymanagementapi',
                    endpoint_url=f'https://{domain_name}/{stage}'
                )
            else:
                logger.error("Missing domainName or stage in requestContext")
                return {'statusCode': 500, 'body': 'Missing API Gateway configuration'}
        
            if not api_client:
                return {'statusCode': 500, 'body': 'Failed to initialize API client'}
                
            # Verify token
            token = message.get("token")
            if not token:
                logger.error("Token is missing in the request")
                return {'statusCode': 403, 'body': 'Token is required'}
            
            try:
                decoded = verify_token(token)
                user_email = decoded.get('email', 'unknown')
                logger.info(f"Valid token for user: {user_email}")
                return handle_message(api_client, connection_id, event)
            except Exception as e:
                logger.error(f"Token verification failed: {str(e)}")
                logger.error(traceback.format_exc())
                return {'statusCode': 403, 'body': 'Invalid Token'}
        else:
            logger.warning(f"Unsupported route: {route_key}")
            return {'statusCode': 400, 'body': f'Unsupported route: {route_key}'}
            
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        logger.error(traceback.format_exc())
        return {'statusCode': 500, 'body': f'Internal server error: {str(e)}'}
