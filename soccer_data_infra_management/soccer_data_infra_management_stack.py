from aws_cdk import core as cdk
import json
import os
# For consistency with other languages, `cdk` is the prefsoccered import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developmenter's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core
import aws_cdk.aws_codepipeline as codepipeline
import aws_cdk.aws_codecommit as codecommit
import aws_cdk.aws_codebuild as codebuild
from aws_cdk.pipelines import  CdkPipeline,SimpleSynthAction
import aws_cdk.aws_events_targets as targets
import aws_cdk.aws_events as events
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_ssm as ssm

from aws_cdk import (core, aws_ec2 as ec2, aws_ecs as ecs,
                     aws_ecs_patterns as ecs_patterns)
import aws_cdk.aws_lambda as lambda_
from aws_cdk.aws_lambda import DockerImageFunction, DockerImageCode
from aws_cdk.aws_lambda_python import PythonFunction, PythonLayerVersion
from aws_cdk.aws_iam import PolicyStatement
import aws_cdk.aws_codebuild as build
import aws_cdk.cloudformation_include as cfn_inc

import aws_cdk.aws_codepipeline_actions as codepipeline_actions
from aws_cdk.core import SecretValue
import aws_cdk.aws_iam as iam
import aws_cdk.aws_ecr as ecr

from .soccer_data import soccerDataTestEcsStage

from aws_cdk.aws_events import Rule, Schedule

class soccerDataInfraManagementStack(cdk.Stack):


  def __init__(self, scope, id, *, description=None, env=None, stackName=None, tags=None, synthesizer=None, terminationProtection=None, analyticsReporting=None, **kwargs):
    super().__init__(scope, id, description=description, env=env, stack_name=stackName, tags=tags, synthesizer=synthesizer, termination_protection=terminationProtection, analytics_reporting=analyticsReporting)

    self.vpc_id = kwargs['vpc_id']
    self.private_subnets = kwargs['private_subnet_ids']
    source_artifact = codepipeline.Artifact()
    cloud_assembly_artifact = codepipeline.Artifact()
    repo = codecommit.Repository.from_repository_name(self, "CodeCommitRepo", repository_name="soccer-data-infra-management")
    oauth = cdk.SecretValue.secrets_manager("github_token")
    github_source = codepipeline_actions.GitHubSourceAction(oauth_token=oauth,
                output=source_artifact,
                owner="GTRIGlobal",
                repo="soccer_data_infra_management",
                branch=kwargs['soccer_data_infra_management_branch'],
                action_name="GitSourceAction",
                )

    pipelineRole = iam.Role(self, "PipelineRole",
        assumed_by=iam.ServicePrincipal("codepipeline.amazonaws.com")
    )

    vpc = ec2.Vpc.from_lookup(self, "soccerApp1VPC",
        vpc_id=self.vpc_id
    )
    pipeline = CdkPipeline(self, "soccerDataTestPipeline",
        pipeline_name="soccerDataTestPipeline",
        self_mutating=True,
        cloud_assembly_artifact=cloud_assembly_artifact,
        support_docker_assets=True,
        source_action=github_source,
        synth_action=SimpleSynthAction(
            source_artifact=source_artifact,
            cloud_assembly_artifact=cloud_assembly_artifact,
            environment=build.BuildEnvironment(build_image=build.LinuxBuildImage.STANDARD_5_0, privileged=True),
            role_policy_statements=[iam.PolicyStatement(
                actions=["*"],
                resources=["*"]
                )],
            install_commands=[
                "npm install -g aws-cdk cdk-assume-role-credential-plugin",
                "python3.9 -m pip install --upgrade pip",
                "pip3 install -r requirements.txt"
                ],
             # Use this if you need a build step (if you're not using ts-node
            # or if you have TypeScript Lambdas that need to be compiled).
            synth_command="cdk synth -v"
        )
    )
    pipeline.code_pipeline.add_to_role_policy(iam.PolicyStatement(
                resources=["*"],
                actions=[
                    "sts:AssumeRole",
                    "cloudformation:*"
                    ]
        )
    )

    for environment in kwargs['environments']:
        soccer_data_test_kwargs = self.get_soccer_data_test_kwargs(environment)
        Stage = soccerDataTestEcsStage(self,
          environment,
          **soccer_data_test_kwargs
        )
        StageCdk = pipeline.add_application_stage(Stage)

  # def get_soccer_data_test_secrets(self, environment):
  #    Params = {
  #             "test" : {
  #                     "db": f"arn:aws-us-gov:secretsmanager:us-gov-west-1:{os.environ['CDK_DEFAULT_ACCOUNT']}:secret:soccer-rds-test-rc8Ye5"
  #                 }
  #             }
  #    response={
  #          "SOCCER_DATA_TEST_DATASOURCE_PASSWORD" : ecs.Secret.from_secrets_manager(
  #              secretsmanager.Secret.from_secret_name(self, f"{environment}soccerDataTestDatasourcePassword",Params[environment.lower()]['db']),
  #              field="password")
  #    }
  #    return response

  def get_soccer_data_test_environment(self, environment):
     Params = {
              "test" : {
                      "env": "arn:aws:secretsmanager:us-east-2:645551448711:secret:soccer_data_environment-h4iunI"
                  }
              }
     response={
           "Key" : ecs.Secret.from_secrets_manager(
               secretsmanager.Secret.from_secret_name(self, f"${environment}Key",Params[environment.lower()]['env']),
               field="Key"
               )
     }
     return response


  def get_soccer_data_test_kwargs(self, environment):
     Params = {
            'env':{
                'account': "645551448711",
                'region': "us-east-2"
              },
            'environment':environment.lower(),
            'container_repo':"soccer-data",
            'container_repo_arn':"arn:aws:ecr:us-east-2:645551448711:repository/soccer-data",
            'image_tag':"latest",
            # 'db_secret':f"arn:aws-gov:secretsmanager:us-gov-west-1:{os.environ['CDK_DEFAULT_ACCOUNT']}:secret:soccer-rds-test-rc8Ye5",
            'soccer_data_test_environment':self.get_soccer_data_test_environment(environment),
            "vpc_id": self.vpc_id,
            "private_subnets": self.private_subnets,
            "ip_whitelist": ["10.110.0.0/16", "10.180.0.0/16", "10.255.240.0/22", "10.10.0.0/16"],
            "hosted_zone_name":"",
            # 'secrets':self.get_soccer_data_test_secrets(environment)
             }


     return Params
