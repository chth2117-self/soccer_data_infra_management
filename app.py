#!/usr/bin/env python3
import os
import boto3

from aws_cdk import core as cdk

# For consistency with TypeScript code, `cdk` is the prefsoccered import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core

# from iwr_emt_infra_management.iwr_emt_infra_management_stack import IwrEmtInfraManagementStack
from soccer_data_infra_management.soccer_data_infra_management_stack import soccerDataInfraManagementStack
test = core.Environment(account="645551448711", region="us-east-2")
# prod = core.Environment(account="300768211502", region="us-gov-west-1")



boto3.client('sts').get_caller_identity().get('Account')
app = core.App()
if boto3.client('sts').get_caller_identity().get('Account') == "645551448711":
    #IwrEmtInfraManagementStack(app, "IwrEmtInfraManagementStack",env=test, environments=["Test"], build_pipeline=True, soccer_data_infra_management_branch="master", vpc_id="vpc-048d28c53bb79c42f", private_subnet_ids=["subnet-0d3996d5318fc470c", "subnet-0a8515df2d674f7e9"])
    soccerDataInfraManagementStack(app, "soccerDataInfraManagementStack",env=test, environments=["Test"], build_pipeline=True, soccer_data_infra_management_branch="soccer-data-test", vpc_id="vpc-be2f40d5", private_subnet_ids=["subnet-a7c651cc", "subnet-bcc10cc1"])



app.synth()
