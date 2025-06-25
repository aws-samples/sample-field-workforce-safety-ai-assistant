import typing
from aws_cdk import (
    Stack,
    aws_apigatewayv2 as apigateway,
    aws_cognito as cognito,
    aws_lambda,
    aws_iam as iam,
    aws_logs as logs,
    RemovalPolicy,
)
from aws_cdk.aws_apigatewayv2_integrations import WebSocketLambdaIntegration
from constructs import Construct
from cdk_nag import NagSuppressions,NagPackSuppression

class CoreWebSocketApiGateway(Construct):
    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            region: str,
            websocket_handler: aws_lambda.Function,
            **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)



        # Create WebSocket API
        self.websocket_api = apigateway.WebSocketApi(
            self,
            "WebSocketApi"
        )

        self.connectRoute = self.websocket_api.add_route(
            '$connect',
            integration=WebSocketLambdaIntegration("ConnectIntegration", websocket_handler)
        )

        # Add these suppressions after creating your WebSocket API
        NagSuppressions.add_resource_suppressions(self.connectRoute
            ,
            [
                {
                    "id": "AwsSolutions-APIG4",
                    "reason": "Authorization handled in Lambda function",
                }
            ]
        )

        self.disConnectRoute = self.websocket_api.add_route(
            '$disconnect',
            integration=WebSocketLambdaIntegration("DisConnectIntegration", websocket_handler)
        )

        # Add these suppressions after creating your WebSocket API
        NagSuppressions.add_resource_suppressions(self.disConnectRoute
            ,
            [
                {
                    "id": "AwsSolutions-APIG4",
                    "reason": "Authorization handled in Lambda function",
                }
            ]
        )

        self.defaultRoute = self.websocket_api.add_route(
            '$default',
            integration=WebSocketLambdaIntegration("DefaultIntegration", websocket_handler)
        )

        # Add these suppressions after creating your WebSocket API
        NagSuppressions.add_resource_suppressions(self.defaultRoute
            ,
            [
                {
                    "id": "AwsSolutions-APIG4",
                    "reason": "Authorization handled in Lambda function",
                }
            ]
        )         

        # Deploy to stage with logging
        self.stage = apigateway.WebSocketStage(
            self,
            "WebSocketStage",
            web_socket_api=self.websocket_api,
            stage_name="dev",
            auto_deploy=True,
        )
        
        # Add suppressions for disabled logging
        NagSuppressions.add_resource_suppressions(
            self.stage,
            [
                NagPackSuppression(
                    id="AwsSolutions-APIG1",
                    reason="API Gateway logging intentionally disabled to avoid CloudWatch Logs role ARN requirement"
                ),
                NagPackSuppression(
                    id="AwsSolutions-APIG6",
                    reason="API Gateway logging intentionally disabled to avoid CloudWatch Logs role ARN requirement"
                )
            ]
        )                  
        # Get the underlying CfnStage
        cfn_stage = self.stage.node.default_child



        # Grant WebSocket management permissions
        websocket_handler.add_to_role_policy(
            iam.PolicyStatement(
                sid="WebSocketManageConnections",
                effect=iam.Effect.ALLOW,
                actions=['execute-api:ManageConnections'],
                resources=[
                    f'arn:aws:execute-api:{region}:{Stack.of(self).account}:{self.websocket_api.api_id}/{self.stage.stage_name}/*'
                ]
            )
        )
        
        # Set the WebSocket API endpoint for other stacks to use
        self.websocket_api_endpoint = f"wss://{self.websocket_api.api_id}.execute-api.{region}.amazonaws.com/{self.stage.stage_name}"
        
        # Expose the API ID directly for easier access
        self.api_id = self.websocket_api.api_id
