import json
import git
import boto3
import os
def handler(event, context):
    print (json.dumps(event,default=str))
    print (json.dumps(context, default=str))
    remote_refs = {}
    g = git.cmd.Git()
    for ref in g.ls_remote("codecommit::us-east-1://ipac").split('\n'):
        hash_ref_list = ref.split('\t')
        remote_refs[hash_ref_list[1]] = hash_ref_list[0]

    client = boto3.client('codebuild')
    if event['detail']['referenceType'] == "tag" and event['detail']['event'] == "referenceCreated":
        tagName = event['detail']['referenceName']
        commitId = remote_refs[event['detail']['referenceFullName']]

        if f"{event['detail']['referenceFullName']}^{{}}" in remote_refs:
            commitId = remote_refs[f"{event['detail']['referenceFullName']}^{{}}"]
        repositoryName = event['detail']['repositoryName']

        response = client.start_build(
            projectName=os.environ['codebuild_project_name'],
            sourceVersion=commitId,
            environmentVariablesOverride=[
                {
                    'name': 'REPOSITORY_NAME',
                    'value': repositoryName,
                    'type': 'PLAINTEXT'
                },
                {
                    'name': 'COMMIT_ID',
                    'value': commitId,
                    'type': 'PLAINTEXT'
                },
                {
                    'name': 'TAG_NAME',
                    'value': tagName, 
                    'type': 'PLAINTEXT'
                },
            ],
        )
    return

