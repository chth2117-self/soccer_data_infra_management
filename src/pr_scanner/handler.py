import json
import boto3
import os
def handler(event, context):
    print (json.dumps(event,default=str))
    print (json.dumps(context, default=str))
    client = boto3.client('codebuild')
    response = client.start_build(
        projectName=os.environ['codebuild_project_name'],
        sourceVersion=event['detail']['sourceCommit'],
        environmentVariablesOverride=[
            {
                'name': 'REPOSITORY_NAME',
                'value': event['detail']['repositoryNames'][0],
                'type': 'PLAINTEXT'
            },
            {
                'name': 'SOURCE_BRANCH',
                'value': event['detail']['sourceReference'],
                'type': 'PLAINTEXT'
            },
            {
                'name': 'TITLE',
                'value': event['detail']['title'],
                'type': 'PLAINTEXT'
            },
            {
                'name': 'PULL_REQUEST_ID',
                'value': event['detail']['pullRequestId'],
                'type': 'PLAINTEXT'
            },
            {
                'name': 'BEFORE_COMMIT_ID',
                'value': event['detail']['sourceCommit'],
                'type': 'PLAINTEXT'
            },
            {
                'name': 'AFTER_COMMIT_ID',
                'value': event['detail']['destinationCommit'],
                'type': 'PLAINTEXT'
            },
        ],
    )
    return
