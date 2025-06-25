import os
from aws_cdk import (
    Stack,
    NestedStack,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_dynamodb as dynamodb,
    CfnOutput,
    Duration,
    RemovalPolicy,
    aws_logs as logs,
    CustomResource,
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression


class DataInfrastructureStack(NestedStack):
    """Nested stack for shared data infrastructure (DynamoDB tables, S3 bucket, data import)"""
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
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

        # Create S3 Bucket for CSV files
        data_bucket = s3.Bucket(
            self,
            "DataBucket",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,  # Enable auto-deletion of objects when bucket is deleted
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,  # Enforce SSL for all requests
        )
        
        # Add NAG suppression for S3 bucket server access logs
        NagSuppressions.add_resource_suppressions(
            data_bucket,
            [
                NagPackSuppression(
                    id="AwsSolutions-S1",
                    reason="Server access logs are not required for this demo bucket as it only contains sample data files"
                )
            ]
        )

        # Deploy CSV files from local data directory to S3 bucket
        data_deployment = s3deploy.BucketDeployment(
             self,
             "DeployCSVFiles",
             sources=[s3deploy.Source.asset("../data", exclude=["**/*", "!**/*.csv"])],
             destination_bucket=data_bucket,
             log_retention=logs.RetentionDays.ONE_WEEK,
             memory_limit=512
        )
        
        # The stack-level suppression will handle the L1 error for the BucketDeployment Lambda
        # We need to add a specific suppression for the IAM5 error on this resource
        NagSuppressions.add_resource_suppressions(
            data_deployment,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="The BucketDeployment construct requires s3:DeleteObject* permissions to clean up files during deployment"
                )
            ],
            apply_to_children=True
        )

        # Create DynamoDB Tables
        work_orders_table = dynamodb.Table(
            self,
            "WorkOrdersTable",
            table_name=f"{construct_id.lower()}-work-orders",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            partition_key=dynamodb.Attribute(
                name="work_order_id",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        work_orders_table.add_global_secondary_index(
            index_name="LocationIndex",
            partition_key=dynamodb.Attribute(
                name="location_name",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        locations_table = dynamodb.Table(
            self,
            "LocationsTable",
            table_name=f"{construct_id.lower()}-locations",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            partition_key=dynamodb.Attribute(
                name="location_name",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )

        hazards_table = dynamodb.Table(
            self,
            "HazardsTable",
            table_name=f"{construct_id.lower()}-hazards",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            partition_key=dynamodb.Attribute(
                name="hazard_id",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        hazards_table.add_global_secondary_index(
            index_name="LocationIndex",
            partition_key=dynamodb.Attribute(
                name="location_name",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        incidents_table = dynamodb.Table(
            self,
            "IncidentsTable",
            table_name=f"{construct_id.lower()}-incidents",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            partition_key=dynamodb.Attribute(
                name="incident_id",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        incidents_table.add_global_secondary_index(
            index_name="LocationIndex",
            partition_key=dynamodb.Attribute(
                name="location_name",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        control_measures_table = dynamodb.Table(
            self,
            "ControlMeasuresTable",
            table_name=f"{construct_id.lower()}-control-measures",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            partition_key=dynamodb.Attribute(
                name="control_measure_id",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        control_measures_table.add_global_secondary_index(
            index_name="LocationHazardIndex",
            partition_key=dynamodb.Attribute(
                name="location_hazard_id",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        assets_table = dynamodb.Table(
            self,
            "AssetsTable",
            table_name=f"{construct_id.lower()}-assets",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            partition_key=dynamodb.Attribute(
                name="asset_id",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        assets_table.add_global_secondary_index(
            index_name="LocationIndex",
            partition_key=dynamodb.Attribute(
                name="location_name",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        location_hazards_table = dynamodb.Table(
            self,
            "LocationHazardsTable",
            table_name=f"{construct_id.lower()}-location-hazards",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            partition_key=dynamodb.Attribute(
                name="location_name",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="hazard_id",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        location_hazards_table.add_global_secondary_index(
            index_name="HazardIndex",
            partition_key=dynamodb.Attribute(
                name="hazard_id",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Create Lambda execution role for data import
        lambda_execution_role = iam.Role(
            self,
            "DataImportLambdaExecutionRole",
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

        # Add permissions for Lambda execution role
        lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3BucketAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:ListBucket",
                    "s3:GetBucketLocation"
                ],
                resources=[data_bucket.bucket_arn]
            )
        )
        
        lambda_execution_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3ObjectAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject"
                ],
                resources=[f"{data_bucket.bucket_arn}/*"]
            )
        )
        
        # Add NAG suppression for the Lambda execution role S3 permissions
        NagSuppressions.add_resource_suppressions(
            lambda_execution_role,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Lambda needs specific S3 object permissions to process files in the bucket"
                )
            ],
            apply_to_children=True
        )
        
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

        # Create Data Import Lambda Function
        data_import_function = lambda_.Function(
            self,
            "DataImportFunction",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=lambda_.Code.from_asset("./bedrock_agents/data_import"),
            role=lambda_execution_role,
            timeout=Duration.seconds(300),
            memory_size=256,
            environment={
                "S3_BUCKET_NAME": data_bucket.bucket_name,
                "WORK_ORDERS_TABLE_NAME": work_orders_table.table_name,
                "LOCATIONS_TABLE_NAME": locations_table.table_name,
                "HAZARDS_TABLE_NAME": hazards_table.table_name,
                "INCIDENTS_TABLE_NAME": incidents_table.table_name,
                "ASSETS_TABLE_NAME": assets_table.table_name,
                "LOCATION_HAZARDS_TABLE_NAME": location_hazards_table.table_name,
                "CONTROL_MEASURES_TABLE_NAME": control_measures_table.table_name
            }
        )
        
        # Add NAG suppression for Lambda runtime
        NagSuppressions.add_resource_suppressions(
            data_import_function,
            [
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="Using the latest Python runtime version 3.13"
                )
            ]
        )
        
        # Create a simple custom resource to trigger the data import function after deployment
        data_import_trigger = CustomResource(
            self,
            "DataImportTrigger",
            service_token=data_import_function.function_arn,
        )
        
        # Add explicit dependencies to ensure proper execution order
        data_import_trigger.node.add_dependency(data_deployment)
        data_import_trigger.node.add_dependency(work_orders_table)
        data_import_trigger.node.add_dependency(locations_table)
        data_import_trigger.node.add_dependency(hazards_table)
        data_import_trigger.node.add_dependency(incidents_table)
        data_import_trigger.node.add_dependency(assets_table)
        data_import_trigger.node.add_dependency(location_hazards_table)
        data_import_trigger.node.add_dependency(control_measures_table)

        # Store references to resources for outputs and sharing with other stacks
        self.data_bucket = data_bucket
        self.work_orders_table = work_orders_table
        self.locations_table = locations_table
        self.hazards_table = hazards_table
        self.incidents_table = incidents_table
        self.assets_table = assets_table
        self.location_hazards_table = location_hazards_table
        self.control_measures_table = control_measures_table
        
        # Expose table names for other stacks
        self.work_orders_table_name = work_orders_table.table_name
        self.locations_table_name = locations_table.table_name
        self.hazards_table_name = hazards_table.table_name
        self.incidents_table_name = incidents_table.table_name
        self.assets_table_name = assets_table.table_name
        self.location_hazards_table_name = location_hazards_table.table_name
        self.control_measures_table_name = control_measures_table.table_name

        # Add outputs
        CfnOutput(
            self,
            "DataBucketName",
            value=data_bucket.bucket_name,
            export_name=f"{construct_id}-DataBucketName"
        )
        
        CfnOutput(
            self,
            "WorkOrdersTableName",
            value=work_orders_table.table_name,
            export_name=f"{construct_id}-WorkOrdersTableName"
        )
        
        CfnOutput(
            self,
            "LocationsTableName",
            value=locations_table.table_name,
            export_name=f"{construct_id}-LocationsTableName"
        )
        
        CfnOutput(
            self,
            "HazardsTableName",
            value=hazards_table.table_name,
            export_name=f"{construct_id}-HazardsTableName"
        )
        
        CfnOutput(
            self,
            "IncidentsTableName",
            value=incidents_table.table_name,
            export_name=f"{construct_id}-IncidentsTableName"
        )
        
        CfnOutput(
            self,
            "AssetsTableName",
            value=assets_table.table_name,
            export_name=f"{construct_id}-AssetsTableName"
        )
        
        CfnOutput(
            self,
            "LocationHazardsTableName",
            value=location_hazards_table.table_name,
            export_name=f"{construct_id}-LocationHazardsTableName"
        )
        
        CfnOutput(
            self,
            "ControlMeasuresTableName",
            value=control_measures_table.table_name,
            export_name=f"{construct_id}-ControlMeasuresTableName"
        )
