from aws_cdk import core as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk.aws_elasticloadbalancingv2 import ApplicationProtocol
from aws_cdk import (core, aws_ec2 as ec2, aws_ecs as ecs,
                     aws_ecs_patterns as ecs_patterns)
from aws_cdk import aws_secretsmanager as secretsmanager
import aws_cdk.aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_rds as rds
from aws_cdk import aws_wafv2
from aws_cdk import aws_secretsmanager as secretsmanager
import aws_cdk.aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk import aws_codepipeline_actions as codepipeline_actions
from aws_cdk import aws_certificatemanager as acm
import json as JSON

#TODO Setup RDS Security group
class SoccerDataStackTest(cdk.Stack):
    def __init__(self, scope, construct_id, **kwargs):
        self._container_repo = kwargs.pop('container_repo')
        self._container_repo_arn = kwargs.pop('container_repo_arn')
        self._image_tag = kwargs.pop('image_tag')
        self._environment = kwargs.pop('environment')
        # self._db_secret = kwargs.pop('db_secret')
        self._vpc_id = kwargs.pop('vpc_id')
        self._private_subnets = kwargs.pop('private_subnets')
        self._ip_whitelist = kwargs.pop('ip_whitelist')
        self._public_lb = False
        self._hosted_zone_name = kwargs.pop('hosted_zone_name')
        # secrets = kwargs.pop("secrets")
        soccer_data_test_environment = kwargs.pop("soccer_data_test_environment")
        if 'public_lb' in kwargs:
            self._public_lb = kwargs.pop('public_lb')

        self._acm_cert = None
        if 'acm_certificate' in kwargs:
            self._acm_cert = kwargs.pop('acm_certificate')
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc.from_lookup(self, "VPC",
            vpc_id=self._vpc_id
        )

        cluster = ecs.Cluster(self, "SoccerDataTestCluster", vpc=vpc)

        # secret_arn = secretsmanager.Secret.from_secret_partial_arn(self, "secret_partial_arn", self._db_secret)


        soccer_data_test_artifact = codepipeline.Artifact()

        fargate_task_definition = ecs.FargateTaskDefinition(self, "TaskDef",
            memory_limit_mib=2048,
            cpu=1024,
        )

        fargate_task_definition.add_container("container",
            image=ecs.ContainerImage.from_registry(f"{self._container_repo_arn}:{self._image_tag}"),
            container_name="soccer-data-test",
            port_mappings=[{"containerPort": 8080}],
            logging=ecs.LogDrivers.aws_logs(stream_prefix=f"{self._environment}_soccer_data_test"),
            environment={
                },
            secrets=soccer_data_test_environment
        )

        fargate_task_definition.add_to_execution_role_policy(iam.PolicyStatement(
                resources=["*"],
                actions=[
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:GetRepositoryPolicy",
                    "ecr:DescribeRepositories",
                    "ecr:ListImages",
                    "ecr:DescribeImages",
                    "ecr:BatchGetImage",
                    "ecr:InitiateLayerUpload",
                    "ecr:UploadLayerPart",
                    "ecr:CompleteLayerUpload",
                    "ecr:PutImage",
                    "secretsmanager:GetSecretValue"
                    ]
                )
        )

        subnetid1 = ec2.Subnet.from_subnet_id(self, "PrivateSubnetA", subnet_id=self._private_subnets[0])
        subnetid2 = ec2.Subnet.from_subnet_id(self, "PrivateSubnetB", subnet_id=self._private_subnets[1])
        vpc_subnets_selection = ec2.SubnetSelection(subnets = [subnetid1, subnetid2])

        ecs_security_group = ec2.SecurityGroup(self, "EcsSG", vpc=vpc )
        ecs_port = ec2.Port(string_representation="HTTPS", protocol=ec2.Protocol.TCP, from_port=3115, to_port=3115)
        for address in self._ip_whitelist:
            ecs_security_group.add_ingress_rule(peer=ec2.Peer.ipv4(address), connection=ecs_port)


        ecs_service = ecs.FargateService(self, "SoccerDataTestService",
            assign_public_ip=False,
            cluster=cluster,
            security_groups= [ecs_security_group],
            vpc_subnets=vpc_subnets_selection,

            #!! update this to 1 when dev team has image in ecr repo !!
            desired_count=1,

            health_check_grace_period=core.Duration.minutes(4),
            task_definition=fargate_task_definition)

        tg = elbv2.NetworkTargetGroup.from_target_group_attributes(scope, "targetGroup", target_group_arn="arn:aws-us-gov:elasticloadbalancing:us-gov-west-1:276847049069:targetgroup/soccer-data-test-tg/8585ff062bcc6d7f")

        ecs_service.attach_to_network_target_group(tg)


        # ECR Build task
        ecr_build = codebuild.PipelineProject(self,
                            'EcrBuild',
                            vpc=vpc,
                            environment=codebuild.BuildEnvironment(privileged=True, build_image=codebuild.LinuxBuildImage.STANDARD_2_0),
                            build_spec=codebuild.BuildSpec.from_object(dict(
                                version="0.2",
                                phases=dict(
                                    install=dict(
                                        commands=[
                                            "apt-get install jq -y",
                                        ]),
                                    build=dict(commands=[
                                               "ContainerName=\"soccer-data-test\"",
                                               "ImageURI=$(cat imageDetail.json | jq -r '.ImageURI')",
                                               "printf '[{\"name\":\"CONTAINER_NAME\",\"imageUri\":\"IMAGE_URI\"}]' > imagedefinitions.json",
                                               "sed -i -e \"s|CONTAINER_NAME|$ContainerName|g\" imagedefinitions.json",
                                               "sed -i -e \"s|IMAGE_URI|$ImageURI|g\" imagedefinitions.json",
                                               "cat imagedefinitions.json"
                                        ])),
                                artifacts={
                                    "files": [
                                        "imagedefinitions.json"]},
                                environment=dict(buildImage=codebuild.LinuxBuildImage.STANDARD_2_0))
                            )
                            )

        # ECR CodeBuild Task permissions
        ecr_build.add_to_role_policy(iam.PolicyStatement(
                resources=["*"],
                actions=[
                    "secretsmanager:GetSecretValue",
                    "ecr:GetAuthorizationToken",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:PutImage",
                    "ecr:InitiateLayerUpload",
                    "ecr:UploadLayerPart",
                    "ecr:CompleteLayerUpload",
                    ]
                )
        )

        ecr_repository = ecr.Repository.from_repository_name(self, "SoccerDataTestServiceRepository", repository_name=self._container_repo)
        source_output = codepipeline.Artifact()
        source_action = codepipeline_actions.EcrSourceAction(
            action_name="ECR",
            repository=ecr_repository,
            image_tag=self._image_tag,
            output=source_output
        )

        ecr_build_output = codepipeline.Artifact("EcrBuildOutput")
        ecs_deployment = codepipeline_actions.EcsDeployAction(action_name="DeploySoccerDataTest",
                                                              image_file=codepipeline.ArtifactPath(artifact=ecr_build_output, file_name="imagedefinitions.json"),
                                                              service=ecs_service)
        ecr_build_action = codepipeline_actions.CodeBuildAction(
                            action_name="ECR_Build",
                            project=ecr_build,
                            input=source_output,
                            outputs=[ecr_build_output])

        ecr_pipeline = codepipeline.Pipeline(self, "EcrPipeline",
            stages=[
                codepipeline.StageProps(stage_name="Source",
                    actions=[
                            source_action
                            ]),
                codepipeline.StageProps(stage_name="Build",
                    actions=[
                            ecr_build_action
                            ]
                    ),
                codepipeline.StageProps(stage_name="Deploy",
                    actions=[
                        ecs_deployment
                        ]
                    )
            ]
        )



class soccerDataTestEcsStage(cdk.Stage):

    def __init__(self, scope, id, **kwargs):
        self._container_repo = kwargs.pop('container_repo')
        self._container_repo_arn = kwargs.pop('container_repo_arn')
        self._image_tag = kwargs.pop('image_tag')
        self._environment = kwargs.pop('environment')
        # self._db_secret = kwargs.pop('db_secret')
        self._private_subnets = kwargs.pop('private_subnets')
        self._vpc_id = kwargs.pop('vpc_id')
        self._public_lb = False
        self._ip_whitelist = kwargs.pop('ip_whitelist')
        # secrets = kwargs.pop("secrets")
        self._hosted_zone_name = kwargs.pop('hosted_zone_name')
        soccer_data_test_environment = kwargs.pop('soccer_data_test_environment')
        if 'public_lb' in kwargs:
            self._public_lb = kwargs.pop('public_lb')

        self._acm_certificate = None
        if 'acm_certificate' in kwargs:
            self._acm_certificate = kwargs.pop('acm_certificate')
        super().__init__(scope, id, **kwargs)
        SoccerDataStackTest1 = SoccerDataStackTest(self,
                                    f"soccerDataTestEcsStage",
                                    synthesizer=cdk.DefaultStackSynthesizer(),
                                    container_repo=self._container_repo,
                                    container_repo_arn=self._container_repo_arn,
                                    image_tag=self._image_tag,
                                    # db_secret=self._db_secret,
                                    acm_certificate=self._acm_certificate,
                                    public_lb=self._public_lb,
                                    environment=self._environment,
                                    # secrets=secrets,
                                    vpc_id=self._vpc_id,
                                    private_subnets=self._private_subnets,
                                    ip_whitelist=self._ip_whitelist,
                                    hosted_zone_name=self._hosted_zone_name,
                                    soccer_data_test_environment=soccer_data_test_environment)
