# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import os
from aws_cdk import (
    Stack,
    NestedStack,
    CfnOutput,
    RemovalPolicy,
    Duration,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_logs as logs,
    aws_dynamodb as dynamodb,
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression


class StrandsAgentsStack(NestedStack):
    """Nested stack for Strands Agents functionality"""
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        collaborator_foundation_model: str,
        supervisor_foundation_model: str,
        data_infrastructure_stack,  # Reference to shared data infrastructure
        **kwargs
    ) -> None:
        
        super().__init__(scope, construct_id, **kwargs)
        
        # Add stack-level NAG suppressions for common patterns
        NagSuppressions.add_stack_suppressions(
            self,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Lambda functions require certain IAM permissions with wildcards for AWS service access"
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Using AWS managed policies is acceptable for this demo application"
                ),
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="Using the latest Python runtime version available"
                )
            ]
        )

        # Use shared data infrastructure instead of creating our own
        work_orders_table = data_infrastructure_stack.work_orders_table
        locations_table = data_infrastructure_stack.locations_table
        hazards_table = data_infrastructure_stack.hazards_table
        incidents_table = data_infrastructure_stack.incidents_table
        assets_table = data_infrastructure_stack.assets_table
        location_hazards_table = data_infrastructure_stack.location_hazards_table
        control_measures_table = data_infrastructure_stack.control_measures_table

        # Create Lambda execution role
        lambda_execution_role = iam.Role(
            self,
            "StrandsLambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        # Add NAG suppression for Lambda execution role
        NagSuppressions.add_resource_suppressions(
            lambda_execution_role,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Using AWS managed policy for Lambda basic execution is acceptable for this use case"
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Bedrock permissions require wildcards for foundation models and inference profiles across regions"
                )
            ],
            apply_to_children=True
        )

        # Add DynamoDB permissions for tables and their indexes
        lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem", 
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchGetItem",
                    "dynamodb:BatchWriteItem"
                ],
                resources=[
                    work_orders_table.table_arn,
                    f"{work_orders_table.table_arn}/index/*",
                    locations_table.table_arn,
                    f"{locations_table.table_arn}/index/*",
                    hazards_table.table_arn,
                    f"{hazards_table.table_arn}/index/*",
                    incidents_table.table_arn,
                    f"{incidents_table.table_arn}/index/*",
                    assets_table.table_arn,
                    f"{assets_table.table_arn}/index/*",
                    location_hazards_table.table_arn,
                    f"{location_hazards_table.table_arn}/index/*",
                    control_measures_table.table_arn,
                    f"{control_measures_table.table_arn}/index/*",
                ]
            )
        )

        # Add WebSocket permissions for Strands agent direct streaming
        lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "execute-api:ManageConnections"
                ],
                resources=[
                    f"arn:aws:execute-api:*:*:*/*/POST/@connections/*"
                ]
            )
        )
        lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockFoundationModelAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/*"
                ]
            )
        )
        
        # Add permissions for Bedrock inference profiles
        lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockInferenceProfileAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:CreateInferenceProfile"
                ],
                resources=[
                    "arn:aws:bedrock:*:*:inference-profile/*",
                    "arn:aws:bedrock:*:*:application-inference-profile/*"
                ]
            )
        )
        
        # Add permissions to manage inference profiles
        lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockInferenceProfileManagement",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:GetInferenceProfile",
                    "bedrock:ListInferenceProfiles",
                    "bedrock:DeleteInferenceProfile",
                    "bedrock:TagResource",
                    "bedrock:UntagResource",
                    "bedrock:ListTagsForResource"
                ],
                resources=[
                    "arn:aws:bedrock:*:*:inference-profile/*",
                    "arn:aws:bedrock:*:*:application-inference-profile/*"
                ]
            )
        )

        # Create explicit log group for Strands supervisor function
        strands_supervisor_log_group = logs.LogGroup(
            self,
            "StrandsSupervisorLogGroup",
            log_group_name=f"/aws/lambda/{construct_id.lower()}-strands-supervisor",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create Strands Supervisor Lambda Function using Docker container
        strands_supervisor_function = lambda_.DockerImageFunction(
            self,
            "StrandsSupervisorFunction",
            function_name=f"{construct_id.lower()}-strands-supervisor",
            code=lambda_.DockerImageCode.from_image_asset("./strands_agents/supervisor_agent"),
            description="Strands-based safety supervisor agent",
            timeout=Duration.seconds(180),
            memory_size=1024,
            architecture=lambda_.Architecture.X86_64,
            role=lambda_execution_role,
            environment={
                "COLLABORATOR_MODEL": collaborator_foundation_model,
                "SUPERVISOR_MODEL": supervisor_foundation_model,
                "WORK_ORDERS_TABLE": work_orders_table.table_name,
                "LOCATIONS_TABLE": locations_table.table_name,
                "HAZARDS_TABLE": hazards_table.table_name,
                "INCIDENTS_TABLE": incidents_table.table_name,
                "ASSETS_TABLE": assets_table.table_name,
                "LOCATION_HAZARDS_TABLE": location_hazards_table.table_name,
                "CONTROL_MEASURES_TABLE": control_measures_table.table_name,
                "LOG_LEVEL": "INFO"
            }
        )

        # Add NAG suppression for Lambda runtime
        NagSuppressions.add_resource_suppressions(
            strands_supervisor_function,
            [
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="Using the latest Python runtime version 3.13"
                )
            ]
        )

        # Store references to resources for outputs
        self.work_orders_table_name = work_orders_table.table_name
        self.locations_table_name = locations_table.table_name
        self.supervisor_function_name = strands_supervisor_function.function_name
        self.supervisor_function_arn = strands_supervisor_function.function_arn

        # Create outputs for compatibility with existing backend (function outputs only)
        CfnOutput(
            self,
            "StrandsSupervisorFunctionName",
            value=strands_supervisor_function.function_name,
            export_name=f"{construct_id}-StrandsSupervisorFunctionName"
        )

        CfnOutput(
            self,
            "StrandsSupervisorFunctionArn", 
            value=strands_supervisor_function.function_arn,
            export_name=f"{construct_id}-StrandsSupervisorFunctionArn"
        )
