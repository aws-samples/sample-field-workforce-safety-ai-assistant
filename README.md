# Gen AI Based Field Workforce Safety Assistant

## Architecture Overview

This solution provides a safety assistant for field workforce personnel, leveraging generative AI to help workers assess and mitigate safety risks in industrial environments.

### Backend

The backend is built using AWS services including:
- Amazon Bedrock for foundation models
- Amazon Bedrock Agents and Strands agents SDK options for orchestrating multi-agent workflows
- AWS Lambda for serverless compute
- Amazon DynamoDB for data storage
- Amazon API Gateway for REST API endpoints
- Amazon Cognito for authentication

## Deployment

You can deploy this solution using either AWS CDK directly or via CloudFormation.

### Prerequisites

- An AWS account
- Access to Amazon Bedrock foundation models (Claude 3.5 and above recommended),
- Enable required models in the Amazon Bedrock console (https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess). You may need to request access if not already granted.
- We recommend using Cross Region Inference profile for better agent performance, please refer instructions at https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html for details.


### Deployment Options

#### Option 1: Deploy using CloudFormation

1. Download the CloudFormation template from the `cfn-templates` directory
2. Navigate to the AWS CloudFormation console
3. Create a new stack using the template
4. Provide the required parameters:
   - CollaboratorFoundationModel: Foundation model or Cross Region Inference Profile ID for the collaborator agent (default: anthropic.claude-3-5-haiku-20241022-v1:0)
   - SupervisorFoundationModel: Foundation model or Cross Region Inference Profile ID for the supervisor agent (default: anthropic.claude-3-7-sonnet-20250219-v1:0)
5. Wait for the stack to complete deployment (this may take 15-20 minutes)

The CloudFormation template will:
- Clone the repository from GitHub
- Bootstrap the CDK environment
- Deploy all required resources using CDK

6. After successful deployment, go to the newly created stack **Outputs** tab. Look for the **FrontendUrl** output - this is your application URL. Click on the URL to open the application

#### Option 2: Deploy using CDK directly

##### Prerequisites
- Configure AWS credentials in your environment
- Download and install [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- Ensure Docker is running on your workstation. CDK uses Docker for bundling assets and packaging Lambda functions with dependencies. If you don't have Docker Desktop, you can use alternatives like colima/podman.

1. Create and activate a Python virtual environment:

```bash
cd cdk
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate.bat
```
You should see (.venv) at the beginning of your command prompt.

2. Install required dependencies:

```bash
pip install -r requirements.txt
```
3. Ensure Docker is running. CDK uses Docker for bundling assets and packaging Lambda functions with dependencies. If you don't have Docker Desktop, you can use alternatives:

4. Log in to the AWS ECR Public registry. This is needed to download docker images for builds.
```bash
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
```

5. If this is the first time using CDK in this account and region, bootstrap CDK. This is a one-time setup that provisions resources CDK needs to deploy your stacks.
```bash
cdk bootstrap
```

6. Deploy the FieldWorkForceSafetyMainStack stack with required parameters:
```bash    
cdk deploy FieldWorkForceSafetyMainStack --require-approval never --context collaborator_foundation_model="claude-3-5-haiku-20241022-v1:0" --context supervisor_foundation_model="anthropic.claude-3-7-sonnet-20250219-v1:0" 
```

7. After CDK deployment, you can find the frontend URL in the stack outputs displayed in your terminal -- this is your application URL. Click on the URL to open the application

## Clean Up
To avoid further charges, follow the tear down procedure:

1. If you deployed using CloudFormation, delete the CloudFormation stack from the AWS console.

2. If you deployed using CDK directly, destroy the parent stack:
```bash
cdk destroy FieldWorkForceSafetyMainStack --require-approval never
```

For a comprehensive list of arguments and options, consult the [CDK CLI documentation](https://docs.aws.amazon.com/cdk/v2/guide/cli.html).

## Security Guideline
Please see the [security guidelines](documentation/security.md).

## Content Security Legal Disclaimer
Sample code, software libraries, command line tools, proofs of concept, templates, or other related technology are provided as AWS Content or Third-Party Content under the AWS Customer Agreement, or the relevant written agreement between you and AWS (whichever applies). You should not use this AWS Content or Third-Party Content in your production accounts, or on production or other critical data. You are responsible for testing, securing, and optimizing the AWS Content or Third-Party Content, such as sample code, as appropriate for production grade use based on your specific quality control practices and standards. Deploying AWS Content or Third-Party Content may incur AWS charges for creating or using AWS chargeable resources, such as running Amazon EC2 instances or using Amazon S3 storage.