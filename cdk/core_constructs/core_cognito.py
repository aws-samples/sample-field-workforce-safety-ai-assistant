# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

from aws_cdk import (
    Stack,
    CfnOutput,
    aws_cognito as cognito,
    aws_iam as iam,
    RemovalPolicy,
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression


class CoreCognito(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        region: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)


        self.user_pool = cognito.UserPool(
            self,
            "UserPool",
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
            self_sign_up_enabled=True,
            sign_in_aliases={"email": True},
            auto_verify={"email": True},
            user_verification=cognito.UserVerificationConfig(
                email_subject="Verify your email for our app",
                email_body="Thanks for signing up! Your verification code is {####}",
                email_style=cognito.VerificationEmailStyle.CODE
            ),
            removal_policy=RemovalPolicy.DESTROY
        )


        self.user_pool.node.default_child.user_pool_add_ons = cognito.CfnUserPool.UserPoolAddOnsProperty(
            advanced_security_mode="ENFORCED",
        )
        NagSuppressions.add_resource_suppressions(
            construct=self.user_pool,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-COG2",
                    reason="MFA not required for Cognito during prototype engagement",
                ),
            ],
        )
        CfnOutput(
            self,
            "UserPoolId",
            value=self.user_pool.user_pool_id,
            export_name=f"{Stack.of(self).stack_name}{construct_id}UserPoolId",
        )

        self.user_pool_client = cognito.UserPoolClient(
            self,
            "UserPoolClient",
            user_pool=self.user_pool,
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
                admin_user_password=True,
                custom=True,
            ),
        )
        self.userPoolId = self.user_pool.user_pool_id
        self.clientId = self.user_pool_client.user_pool_client_id

        CfnOutput(
            self,
            "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            export_name=f"{Stack.of(self).stack_name}{construct_id}UserPoolClientId",
        )

        self.identity_pool = cognito.CfnIdentityPool(
            self,
            "IdentityPool",
            allow_unauthenticated_identities=False,
            cognito_identity_providers=[cognito.CfnIdentityPool.CognitoIdentityProviderProperty(
                client_id=self.user_pool_client.user_pool_client_id,
                provider_name=self.user_pool.user_pool_provider_name
            )],
        )
        CfnOutput(
            self,
            "IdentityPoolId",
            value=self.identity_pool.ref,
            export_name=f"{Stack.of(self).stack_name}{construct_id}IdentityPoolId",
        )

        self.auth_user_role = iam.Role(
            self,
            "AuthenticatedUserRole",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                {
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": self.identity_pool.ref,
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "authenticated",
                    },
                },
                "sts:AssumeRoleWithWebIdentity",
            ),
        )
        
        self.unauth_user_role = iam.Role(
            self,
            "UnauthenticatedUserRole",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                {
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": self.identity_pool.ref,
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "unauthenticated",
                    },
                }
            )
        )

        self.identity_pool_role_attachment = cognito.CfnIdentityPoolRoleAttachment(
            self,
            "IdentityPoolRoleAttachment",
            identity_pool_id=self.identity_pool.ref,
            roles={
                "authenticated": self.auth_user_role.role_arn,
                "unauthenticated": self.unauth_user_role.role_arn,
            },
            role_mappings={
                "mapping": cognito.CfnIdentityPoolRoleAttachment.RoleMappingProperty(
                    type="Token",
                    ambiguous_role_resolution="AuthenticatedRole",
                    identity_provider="cognito-idp.{}.amazonaws.com/{}:{}".format(
                        region,
                        self.user_pool.user_pool_id,
                        self.user_pool_client.user_pool_client_id))
            }
        )
