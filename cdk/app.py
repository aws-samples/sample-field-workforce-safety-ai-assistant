#!/usr/bin/env python3

# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    NestedStack,
    CfnParameter,
    CfnOutput
)
from constructs import Construct
from cdk_nag import AwsSolutionsChecks, NagSuppressions, NagPackSuppression

# Import nested stack classes directly from their respective modules
from bedrock_agents import BedrockAgentsStack
from strands_agents import StrandsAgentsStack
from data_infrastructure import DataInfrastructureStack
from backend import BackendStack
from webappstack import FrontendStack

class FieldWorkForceSafetyMainStack(Stack):
    """Parent stack that contains all nested stacks"""
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Add stack-level NAG suppressions for common patterns
        NagSuppressions.add_stack_suppressions(
            self,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Custom resources and CDK constructs require certain IAM permissions with wildcards"
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Using AWS managed policies is acceptable for this demo application"
                ),
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="CDK BucketDeployment construct uses a Lambda function with a runtime managed by CDK that we cannot directly control"
                ),
            ]
        )

        # Frontend is always deployed by default

        # Get foundation model parameters from context
        collaborator_foundation_model = self.node.try_get_context("collaborator_foundation_model")
        if collaborator_foundation_model is None:
            collaborator_foundation_model = "anthropic.claude-3-sonnet-20240229-v1:0"

        supervisor_foundation_model = self.node.try_get_context("supervisor_foundation_model")
        if supervisor_foundation_model is None:
            supervisor_foundation_model = "anthropic.claude-3-sonnet-20240229-v1:0"

        # Deploy both agent frameworks by default
        deploy_bedrock_agents = "yes"
        deploy_strands_agents = "yes"
        
        print("🚀 Deploying both Bedrock Agents and Strands Agents by default")
        print(f"🎯 Framework deployment configuration:")
        print(f"   - Bedrock Agents: ✅ Enabled")
        print(f"   - Strands Agents: ✅ Enabled")

        # Default language
        language_code = "en"

        # Deploy shared data infrastructure stack first
        data_infrastructure_stack = DataInfrastructureStack(
            self,
            "FieldSafetyDataInfrastructureStack"
        )

        # Initialize agent variables
        bedrock_agent_id = None
        bedrock_agent_alias_id = None
        strands_agent_id = None
        strands_agent_alias_id = None

        # Deploy Bedrock Agents stack
        print("🤖 Deploying Bedrock Agents stack...")
        bedrock_agents_stack = BedrockAgentsStack(
            self,
            "FieldSafetyBedrockAgentStack",
            collaborator_foundation_model=collaborator_foundation_model,
            supervisor_foundation_model=supervisor_foundation_model,
            data_infrastructure_stack=data_infrastructure_stack
        )
        bedrock_agents_stack.add_dependency(data_infrastructure_stack)
        
        bedrock_agent_id = bedrock_agents_stack.supervisor_agent_id
        bedrock_agent_alias_id = bedrock_agents_stack.supervisor_agent_alias_id
        
        # Output Bedrock Agent details
        CfnOutput(
            self,
            "BedrockAgentId",
            value=bedrock_agent_id,
            description="Bedrock Agent ID for safety analysis"
        )
        CfnOutput(
            self,
            "BedrockAgentAliasId", 
            value=bedrock_agent_alias_id,
            description="Bedrock Agent Alias ID for safety analysis"
        )

        # Deploy Strands Agents stack
        print("🧠 Deploying Strands Agents stack...")
        strands_agents_stack = StrandsAgentsStack(
            self,
            "FieldSafetyStrandsAgentStack",
            collaborator_foundation_model=collaborator_foundation_model,
            supervisor_foundation_model=supervisor_foundation_model,
            data_infrastructure_stack=data_infrastructure_stack
        )
        strands_agents_stack.add_dependency(data_infrastructure_stack)
        
        strands_agent_id = strands_agents_stack.supervisor_function_name
        strands_agent_alias_id = strands_agents_stack.supervisor_function_arn
        
        # Output Strands Agent details
        CfnOutput(
            self,
            "StrandsAgentFunctionName",
            value=strands_agent_id,
            description="Strands Agent Lambda function name for safety analysis"
        )
        CfnOutput(
            self,
            "StrandsAgentFunctionArn",
            value=strands_agent_alias_id,
            description="Strands Agent Lambda function ARN for safety analysis"
        )

        # Always deploy Backend and Frontend stacks
        print("🌐 Deploying Backend and Frontend stacks...")
        
        # Deploy Backend stack with both agent configurations
        backend_stack = BackendStack(
            self,
            "FieldSafetyBackendAPIStack",
            language_code=language_code,
            # Bedrock Agent parameters
            bedrock_agent_id=bedrock_agent_id,
            bedrock_agent_alias_id=bedrock_agent_alias_id,
            # Strands Agent parameters  
            strands_agent_id=strands_agent_id,
            strands_agent_alias_id=strands_agent_alias_id,
            # Shared parameters
            work_order_table_name=data_infrastructure_stack.work_orders_table_name,
            location_table_name=data_infrastructure_stack.locations_table_name,
            # Framework deployment flags - both are always deployed
            deploy_bedrock_agents=deploy_bedrock_agents,
            deploy_strands_agents=deploy_strands_agents
        )
        
        # Add dependencies for both agent stacks
        backend_stack.add_dependency(bedrock_agents_stack)
        backend_stack.add_dependency(strands_agents_stack)

        # Deploy Frontend stack
        frontend_stack = FrontendStack(
            self,
            "FieldSafetyFrontendStack",
            api_endpoint=backend_stack.api_endpoint,
            workorder_api_endpoint=backend_stack.workorder_api_endpoint,
            websocket_api_endpoint=backend_stack.websocket_api_endpoint,
            region_name=backend_stack.region_name,
            cognito_user_pool_id=backend_stack.user_pool_id,
            cognito_user_pool_client_id=backend_stack.user_pool_client_id,
            cognito_identity_pool_id=backend_stack.identity_pool_id
        )
        frontend_stack.add_dependency(backend_stack)

        # Add output for webapp url
        CfnOutput(
            self,
            "FrontendUrl",
            value=frontend_stack.frontend_url,
            description="Frontend App Access URL"
        )

        # Summary output
        print("\n🎉 Deployment Summary:")
        print(f"   📊 Data Infrastructure: ✅ Deployed")
        print(f"   🤖 Bedrock Agents: ✅ Deployed")
        print(f"   🧠 Strands Agents: ✅ Deployed")
        print(f"   🌐 Backend & Frontend: ✅ Deployed")
        print()

# Create the app and deploy the parent stack
app = cdk.App()
parent_stack = FieldWorkForceSafetyMainStack(app, "FieldWorkForceSafetyMainStack")
cdk.Aspects.of(app).add(AwsSolutionsChecks())
app.synth()
