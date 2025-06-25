import os
from aws_cdk import (
    Stack,
    NestedStack,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_dynamodb as dynamodb,
    CfnOutput,
    Duration,
    RemovalPolicy,
    aws_bedrock as bedrock,
    aws_logs as logs,
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression


class BedrockAgentsStack(NestedStack):
    """Nested stack for Bedrock Agents functionality"""
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
                    reason="Custom resources and CDK constructs require certain IAM permissions with wildcards"
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Using AWS managed policies is acceptable for this demo application"
                ),
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="CDK BucketDeployment construct uses a Lambda function with a runtime managed by CDK that we cannot directly control"
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
            "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        # Add NAG suppression for Lambda execution role managed policy
        NagSuppressions.add_resource_suppressions(
            lambda_execution_role,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Using AWS managed policy for Lambda basic execution is acceptable for this use case"
                )
            ],
            apply_to_children=True
        )

        # Add DynamoDB permissions for Lambda functions to access shared tables
        lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                sid="DynamoDBAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchWriteItem",
                    "dynamodb:PutItem"
                ],
                resources=[
                    work_orders_table.table_arn,
                    locations_table.table_arn,
                    hazards_table.table_arn,
                    incidents_table.table_arn,
                    assets_table.table_arn,
                    location_hazards_table.table_arn,
                    control_measures_table.table_arn,
                    f"{work_orders_table.table_arn}/index/*",
                    f"{locations_table.table_arn}/index/*",
                    f"{hazards_table.table_arn}/index/*",
                    f"{incidents_table.table_arn}/index/*",
                    f"{assets_table.table_arn}/index/*",
                    f"{location_hazards_table.table_arn}/index/*",
                    f"{control_measures_table.table_arn}/index/*"
                ]
            )
        )

        # Create explicit log group for weather agent function
        weather_agent_log_group = logs.LogGroup(
            self,
            "WeatherAgentLogGroup",
            log_group_name=f"/aws/lambda/{construct_id.lower()}-weather-agent",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Create Weather Agent Lambda Function
        weather_agent_function = lambda_.Function(
            self,
            "WeatherAgentFunction",
            function_name=f"{construct_id.lower()}-weather-agent",
            runtime=lambda_.Runtime.PYTHON_3_13,  # Updated to latest Python runtime
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset("./bedrock_agents/weather_agent"),
            role=lambda_execution_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "LOG_LEVEL": "INFO"
            }
        )
        
        # Add NAG suppression for Lambda runtime
        NagSuppressions.add_resource_suppressions(
            weather_agent_function,
            [
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="Using the latest Python runtime version 3.13"
                )
            ]
        )
        
        # Create explicit log group for location alert function
        location_alert_log_group = logs.LogGroup(
            self,
            "LocationAlertLogGroup",
            log_group_name=f"/aws/lambda/{construct_id.lower()}-location-alert",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Create Location Alert Lambda Function
        location_alert_function = lambda_.Function(
            self,
            "LocationAlertFunction",
            function_name=f"{construct_id.lower()}-location-alert",
            runtime=lambda_.Runtime.PYTHON_3_13,  # Updated to latest Python runtime
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset("./bedrock_agents/location_alert"),
            role=lambda_execution_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "WORK_ORDERS_TABLE_NAME": work_orders_table.table_name,
                "LOCATIONS_TABLE_NAME": locations_table.table_name,
                "HAZARDS_TABLE_NAME": hazards_table.table_name,
                "INCIDENTS_TABLE_NAME": incidents_table.table_name,
                "LOCATION_HAZARDS_TABLE_NAME": location_hazards_table.table_name,
                "CONTROL_MEASURES_TABLE_NAME": control_measures_table.table_name,
                "LOG_LEVEL": "INFO"
            }
        )
        
        # Add NAG suppression for Lambda runtime
        NagSuppressions.add_resource_suppressions(
            location_alert_function,
            [
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="Using the latest Python runtime version 3.13"
                )
            ]
        )
        
        # Create explicit log group for emergency alert function
        emergency_alert_log_group = logs.LogGroup(
            self,
            "EmergencyAlertLogGroup",
            log_group_name=f"/aws/lambda/{construct_id.lower()}-emergency-alert",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Create Emergency Alert Lambda Function
        emergency_alert_function = lambda_.Function(
            self,
            "EmergencyAlertFunction",
            function_name=f"{construct_id.lower()}-emergency-alert",
            runtime=lambda_.Runtime.PYTHON_3_13,  # Updated to latest Python runtime
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset("./bedrock_agents/emergency_alert"),
            role=lambda_execution_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "LOG_LEVEL": "INFO"
            }
        )
        
        # Add NAG suppression for Lambda runtime
        NagSuppressions.add_resource_suppressions(
            emergency_alert_function,
            [
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="Using the latest Python runtime version 3.13"
                )
            ]
        )
        
        # Create Weather Agent IAM Role
        weather_agent_role = iam.Role(
            self,
            "WeatherBedrockAgentExecutionRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description='Execution role for Weather Bedrock Agent'
        )
        
        # Add permissions for Weather agent to invoke Lambda function and use inference profiles
        weather_agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="AmazonBedrockAgentInferencProfilePolicy1",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel*",
                    "bedrock:CreateInferenceProfile"
                ],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/*",
                    "arn:aws:bedrock:*:*:inference-profile/*",
                    "arn:aws:bedrock:*:*:application-inference-profile/*"
                ]
            )
        )

        weather_agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="AmazonBedrockAgentInferencProfilePolicy2",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:GetInferenceProfile",
                    "bedrock:ListInferenceProfiles",
                    "bedrock:DeleteInferenceProfile",
                    "bedrock:TagResource",
                    "bedrock:UntagResource",
                    "bedrock:ListTagsForResource",
                ],
                resources=[
                    "arn:aws:bedrock:*:*:inference-profile/*",
                    "arn:aws:bedrock:*:*:application-inference-profile/*"
                ]
            )
        )


        weather_agent_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[weather_agent_function.function_arn]
            )
        )
        
        # Create Location Alert Agent IAM Role
        location_alert_agent_role = iam.Role(
            self,
            "LocationAlertBedrockAgentExecutionRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description='Execution role for Location Alert Bedrock Agent'
        )
        
        # Add permissions for Location Alert agent to invoke Lambda function and use inference profiles
        location_alert_agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="AmazonBedrockAgentInferencProfilePolicy1",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel*",
                    "bedrock:CreateInferenceProfile"
                ],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/*",
                    "arn:aws:bedrock:*:*:inference-profile/*",
                    "arn:aws:bedrock:*:*:application-inference-profile/*"
                ]
            )
        )

        location_alert_agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="AmazonBedrockAgentInferencProfilePolicy2",
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

        location_alert_agent_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[location_alert_function.function_arn]
            )
        )
        
        # Create Emergency Alert Agent IAM Role
        emergency_alert_agent_role = iam.Role(
            self,
            "EmergencyAlertBedrockAgentExecutionRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description='Execution role for Emergency Alert Bedrock Agent'
        )
        
        # Add permissions for Emergency Alert agent to invoke Lambda function and use inference profiles
        emergency_alert_agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="AmazonBedrockAgentInferencProfilePolicy1",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel*",
                    "bedrock:CreateInferenceProfile"
                ],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/*",
                    "arn:aws:bedrock:*:*:inference-profile/*",
                    "arn:aws:bedrock:*:*:application-inference-profile/*"
                ]
            )
        )
        
        emergency_alert_agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="AmazonBedrockAgentInferencProfilePolicy2",
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

        emergency_alert_agent_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[emergency_alert_function.function_arn]
            )
        )
        
        # Create Supervisor Agent IAM Role
        # Create Supervisor Agent IAM Role
        supervisor_agent_role = iam.Role(
            self,
            "SupervisorAgentRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description='Execution role for Supervisor Bedrock Agent'
        )
        
        # Add permissions for Supervisor agent to use inference profiles
        supervisor_agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="AmazonBedrockAgentInferencProfilePolicy1",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel*",
                    "bedrock:CreateInferenceProfile"
                ],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/*",
                    "arn:aws:bedrock:*:*:inference-profile/*",
                    "arn:aws:bedrock:*:*:application-inference-profile/*"
                ]
            )
        )
        
        supervisor_agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="AmazonBedrockAgentInferencProfilePolicy2",
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
        
        # Add permissions for agent collaboration
        supervisor_agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="AmazonBedrockAgentBedrockFoundationModelPolicy",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:GetAgentAlias",
                    "bedrock:InvokeAgent"
                ],
                resources=[
                    "arn:aws:bedrock:*:*:agent/*",
                    "arn:aws:bedrock:*:*:agent-alias/*"
                ]
             )
        )
        
        # Add permissions for guardrails
        supervisor_agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="AmazonBedrockAgentBedrockInvokeGuardrailModelPolicy",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:GetGuardrail",
                    "bedrock:ApplyGuardrail"
                ],
                resources=["arn:aws:bedrock:*:*:guardrail/*"]
            )
        )
        
        # Add permissions for knowledge bases
        supervisor_agent_role.add_to_policy(
            iam.PolicyStatement(
                sid="QueryKB",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:Retrieve",
                    "bedrock:RetrieveAndGenerate"
                ],
                resources=["arn:aws:bedrock:*:*:knowledge-base/*"]
            )
        )
        
        # Add CloudWatch Logs permissions for all agent roles
        for role in [weather_agent_role, location_alert_agent_role, emergency_alert_agent_role, supervisor_agent_role]:
            role.add_to_policy(
                iam.PolicyStatement(
                    sid="CloudWatchLogsAccess",
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'logs:CreateLogStream',
                        'logs:PutLogEvents'
                    ],
                    resources=[
                        f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/bedrock/*:*"
                    ]
                )
            )
        
 
    
        # Add NAG suppression for Bedrock agent role
        NagSuppressions.add_resource_suppressions(
            weather_agent_role,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Giving Bedrock permissions on Agent Role"
                )
            ],
            apply_to_children=True
        )
        # Add NAG suppression for Bedrock agent role
        NagSuppressions.add_resource_suppressions(
            location_alert_agent_role,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Giving Bedrock permissions on Agent Role"
                )
            ],
            apply_to_children=True
        )

        # Add NAG suppression for Bedrock agent role
        NagSuppressions.add_resource_suppressions(
            emergency_alert_agent_role,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Giving Bedrock permissions on Agent Role"
                )
            ],
            apply_to_children=True
        )

        # Add NAG suppression for Bedrock agent role
        NagSuppressions.add_resource_suppressions(
            supervisor_agent_role,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Giving Bedrock permissions on Agent Role"
                )
            ],
            apply_to_children=True
        )

        # Create Weather Agent Action Group
        weather_agent_action_group = bedrock.CfnAgent.AgentActionGroupProperty(
            action_group_name="WeatherForecast",
            action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                lambda_=weather_agent_function.function_arn
            ),
            description="Get weather forecast and warnings for a specific location and time",
            action_group_state="ENABLED",
            function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                functions=[
                    bedrock.CfnAgent.FunctionProperty(
                        name="weatherforecast",
                        description="Get weather forecast at lat and long for the datetime entered",
                        parameters={
                            "lat": bedrock.CfnAgent.ParameterDetailProperty(
                                type="string",
                                description="Latitude",
                                required=True
                            ),
                            "long": bedrock.CfnAgent.ParameterDetailProperty(
                                type="string",
                                description="Longitude",
                                required=True
                            ),
                            "target_datetime": bedrock.CfnAgent.ParameterDetailProperty(
                                type="string",
                                description="Target Date and Time",
                                required=True
                            )
                        }
                    )
                ]
            )
        )
        
        # Create Location Alert Action Group
        location_alert_action_group = bedrock.CfnAgent.AgentActionGroupProperty(
            action_group_name="LocationAlerts",
            action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                lambda_=location_alert_function.function_arn
            ),
            description="Get safety alerts for a specific work order location",
            action_group_state="ENABLED",
            function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                functions=[
                    bedrock.CfnAgent.FunctionProperty(
                        name="fetch_location_alerts",
                        description="Get all incidents and hazards reported the location where the workorder has been created",
                        parameters={
                            "work_order_id": bedrock.CfnAgent.ParameterDetailProperty(
                                type="string",
                                description="Work Order ID",
                                required=True
                            )
                        }
                    )
                ]
            )
        )
        
        # Create Emergency Alert Action Group
        emergency_alert_action_group = bedrock.CfnAgent.AgentActionGroupProperty(
            action_group_name="EmergencyAlerts",
            action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                lambda_=emergency_alert_function.function_arn
            ),
            description="Get emergency alerts for a specific location",
            action_group_state="ENABLED",
            function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                functions=[
                    bedrock.CfnAgent.FunctionProperty(
                        name="emvalert",
                        description="Get emergency alert at lat and long",
                        parameters={
                            "lat": bedrock.CfnAgent.ParameterDetailProperty(
                                type="string",
                                description="Latitude",
                                required=True
                            ),
                            "long": bedrock.CfnAgent.ParameterDetailProperty(
                                type="string",
                                description="Longitude",
                                required=True
                            )
                        }
                    )
                ]
            )
        )
        
        # Create Weather Agent with autoPrepare=True
        weather_agent = bedrock.CfnAgent(
            self,
            "WeatherAlertAgent",
            agent_name="FieldSafetyWeatherAgent",
            agent_resource_role_arn=weather_agent_role.role_arn,
            foundation_model=collaborator_foundation_model,
            description = "You are a weather forecast agent. On getting access to the latitude, longitude and target_date_time, you will be able to provide weather warnings and alerts",
            instruction="Goal: Fetch the weather information at a latitude and longitude at a target datetime.,Instructions: Fetch the weather information and alerts at a latitude and longitude at a target datetime. You may get the Workorder details in JSON format including workorder location",
            action_groups=[weather_agent_action_group],
            idle_session_ttl_in_seconds=1800,
            auto_prepare=True  # Use autoPrepare instead of custom resource
        )
        
        weather_agent.node.add_dependency(weather_agent_role)

        # Create Location Alert Agent with autoPrepare=True
        location_alert_agent = bedrock.CfnAgent(
            self,
            "LocationAlertAgent",
            agent_name="FieldSafetyLocationAlertAgent",
            agent_resource_role_arn=location_alert_agent_role.role_arn,
            foundation_model=collaborator_foundation_model,
            description = "You are a safety officer whose job is to find all reported incidents at the location, all hazards reported the location and then prepare a safety briefing for the field workforce technician",
            instruction="Role: Safety officer, Goal: When a workorder is assigned to a field workforce technician, provide all possible incidents and hazards reported at the location for the workorder to ensure that the technician is well informed",
            action_groups=[location_alert_action_group],
            idle_session_ttl_in_seconds=1800,
            auto_prepare=True  # Use autoPrepare instead of custom resource
        )
        
        location_alert_agent.node.add_dependency(location_alert_agent_role)

        # Create Emergency Alert Agent with autoPrepare=True
        emergency_alert_agent = bedrock.CfnAgent(
            self,
            "EmergencyAlertAgent",
            agent_name="FieldSafetyEmergencyAlertAgent",
            agent_resource_role_arn=emergency_alert_agent_role.role_arn,
            foundation_model=collaborator_foundation_model,
            description = "Agent that fetches the Emergency warnings and alerts for a given location",
            instruction="You are an emergency assistant that provides emergency alerts for specific locations. Fetch the emergency warnings at a latitude and longitude.You will get the latitude and longitude details from Workorder location.",
            action_groups=[emergency_alert_action_group],
            idle_session_ttl_in_seconds=1800,
            auto_prepare=True  # Use autoPrepare instead of custom resource
        )

        emergency_alert_agent.node.add_dependency(emergency_alert_agent_role)
        
        # Create agent aliases
        weather_agent_alias = bedrock.CfnAgentAlias(
            self,
            "WeatherAgentAlias",
            agent_id=weather_agent.attr_agent_id,
            agent_alias_name="WeatherAgentAlias",
        )
        
        location_alert_agent_alias = bedrock.CfnAgentAlias(
            self,
            "LocationAlertAgentAlias",
            agent_id=location_alert_agent.attr_agent_id,
            agent_alias_name="LocationAlertAgentAlias",
        )
        
        emergency_alert_agent_alias = bedrock.CfnAgentAlias(
            self,
            "EmergencyAlertAgentAlias",
            agent_id=emergency_alert_agent.attr_agent_id,
            agent_alias_name="EmergencyAlertAgentAlias",
        )
        
        # Set dependencies to ensure proper creation order for agent aliases
        weather_agent_alias.node.add_dependency(weather_agent)
        location_alert_agent_alias.node.add_dependency(location_alert_agent)
        emergency_alert_agent_alias.node.add_dependency(emergency_alert_agent)
        
        # Create Supervisor Agent with collaborators using native CDK constructs
        supervisor_agent = bedrock.CfnAgent(
            self,
            "SupervisorAgent",
            agent_name="FieldSafetySupervisorAgent",
            agent_resource_role_arn=supervisor_agent_role.role_arn,
            foundation_model=supervisor_foundation_model,
            description = "A specialized safety report generator that performs work order safety assessment and generates a comprehensive Work Order Safety Briefiing in HTML format.",
            instruction="""
<role_definition>
Safety Report Supervisor | Input: WorkOrder Details JSON | Output: HTML Report
</role_definition>
<workflow>            
1. When you receive input message, extract agent function call parameters work_order_id, latitude, longitude, and target_datetime.
2. To perform safety briefing, Perform hazard, weather, and emergency checks using provided collaborator agents and valid parameters.
   LocationAlertAgent - Call with only work_order_id
   WeatherAgent - Call with latitude, longitude and target_datetime
   EmergencyAlertAgent - Call with latitude, longitude 
3. Organize the information from all collaborators into a structured HTML report.
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
    <p>[Insert emergency alert infromation here]</p>
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
            idle_session_ttl_in_seconds=1800,
            auto_prepare=True,  # Use autoPrepare instead of custom resource
            # Add agent collaboration configuration
            agent_collaboration="SUPERVISOR",
            agent_collaborators=[
                bedrock.CfnAgent.AgentCollaboratorProperty(
                    agent_descriptor=bedrock.CfnAgent.AgentDescriptorProperty(
                        alias_arn=weather_agent_alias.attr_agent_alias_arn
                    ),
                    collaboration_instruction="Use this agent to get weather forecast for work order location and time.",
                    collaborator_name="WeatherAgent",
                    relay_conversation_history="DISABLED"
                ),
                bedrock.CfnAgent.AgentCollaboratorProperty(
                    agent_descriptor=bedrock.CfnAgent.AgentDescriptorProperty(
                        alias_arn=location_alert_agent_alias.attr_agent_alias_arn
                    ),
                    collaboration_instruction="Use this agent to get hazards and incidents for work order location.",
                    collaborator_name="LocationAlertAgent",
                    relay_conversation_history="DISABLED"
                ),
                bedrock.CfnAgent.AgentCollaboratorProperty(
                    agent_descriptor=bedrock.CfnAgent.AgentDescriptorProperty(
                        alias_arn=emergency_alert_agent_alias.attr_agent_alias_arn
                    ),
                    collaboration_instruction="Use this agent to get emergency alerts for work order location.",
                    collaborator_name="EmergencyAlertAgent",
                    relay_conversation_history="DISABLED"
                )
            ]
        )
        
        supervisor_agent.node.add_dependency(supervisor_agent_role)

        # Create Supervisor Agent Alias
        supervisor_agent_alias = bedrock.CfnAgentAlias(
            self,
            "SupervisorAgentAlias",
            agent_id=supervisor_agent.attr_agent_id,
            agent_alias_name="SupervisorAgentAlias",
        )
        
        # Set explicit dependencies for supervisor agent and its alias
        supervisor_agent.node.add_dependency(weather_agent)
        supervisor_agent.node.add_dependency(location_alert_agent)
        supervisor_agent.node.add_dependency(emergency_alert_agent)
        supervisor_agent.node.add_dependency(weather_agent_alias)
        supervisor_agent.node.add_dependency(location_alert_agent_alias)
        supervisor_agent.node.add_dependency(emergency_alert_agent_alias)

        supervisor_agent_alias.node.add_dependency(supervisor_agent)
        
        

       # Add explicit Lambda permissions for Bedrock agents
        weather_lambda_permission = lambda_.CfnPermission(
            self,
            "WeatherLambdaPermission",
            action="lambda:InvokeFunction",
            function_name=weather_agent_function.function_name,
            principal="bedrock.amazonaws.com",
            source_arn=f"arn:aws:bedrock:{self.region}:{self.account}:agent/{weather_agent.attr_agent_id}"
        )
        
        location_alert_lambda_permission = lambda_.CfnPermission(
            self,
            "LocationAlertLambdaPermission",
            action="lambda:InvokeFunction",
            function_name=location_alert_function.function_name,
            principal="bedrock.amazonaws.com",
            source_arn=f"arn:aws:bedrock:{self.region}:{self.account}:agent/{location_alert_agent.attr_agent_id}"
        )
        
        emergency_alert_lambda_permission = lambda_.CfnPermission(
            self,
            "EmergencyAlertLambdaPermission",
            action="lambda:InvokeFunction",
            function_name=emergency_alert_function.function_name,
            principal="bedrock.amazonaws.com",
            source_arn=f"arn:aws:bedrock:{self.region}:{self.account}:agent/{emergency_alert_agent.attr_agent_id}"
        )
        
        # Set dependencies to ensure proper creation order
        weather_lambda_permission.node.add_dependency(weather_agent)
        location_alert_lambda_permission.node.add_dependency(location_alert_agent)
        emergency_alert_lambda_permission.node.add_dependency(emergency_alert_agent)


        # Store references to resources for outputs
        self.work_orders_table_name = work_orders_table.table_name
        self.locations_table_name = locations_table.table_name
        self.supervisor_agent_id = supervisor_agent.attr_agent_id
        self.supervisor_agent_alias_id = supervisor_agent_alias.attr_agent_alias_id

        # Add outputs for agent IDs only (table outputs are handled by data infrastructure stack)
        CfnOutput(
            self,
            "WeatherAgentId",
            value=weather_agent.attr_agent_id,
            export_name=f"{construct_id}-WeatherAgentId"
        )
        
        CfnOutput(
            self,
            "LocationAlertAgentId",
            value=location_alert_agent.attr_agent_id,
            export_name=f"{construct_id}-LocationAlertAgentId"
        )
        
        CfnOutput(
            self,
            "EmergencyAlertAgentId",
            value=emergency_alert_agent.attr_agent_id,
            export_name=f"{construct_id}-EmergencyAlertAgentId"
        )
        
        # Add outputs for the supervisor agent
        CfnOutput(
            self,
            "SupervisorAgentId",
            value=supervisor_agent.attr_agent_id,
            export_name=f"{construct_id}-SupervisorAgentId"
        )
        
        CfnOutput(
            self,
            "SupervisorAgentAliasId",
            value=supervisor_agent_alias.attr_agent_alias_id,
            export_name=f"{construct_id}-SupervisorAgentAliasId"
        )
