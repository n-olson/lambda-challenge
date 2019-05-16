import json
import boto3
import logging
import os
from gzip import GzipFile
from io import BytesIO
from botocore.vendored import requests


logger = logging.getLogger()
logger.setLevel(logging.INFO)
SLACK_URL = os.environ['SLACK_URL']
s3 = boto3.client('s3')


def format_data(data):
    """
    Function take gzipped binary data from s3 and converts it to easily
    iterable json. event data presented in lambda_handler.py is information
    about the bucket and file, not the file content itself.

    :param data: compressed utf-8 encoded data passed to lambda by s3
    :return json after being decompressed and decoded
    """
    bucket = data['Records'][0]['s3']['bucket']['name']
    key = data['Records'][0]['s3']['object']['key']
    # Uses bucket/key in lambda function event data to get data from s3 bucket
    data = s3.get_object(Bucket=bucket, Key=key)
    bytestream = BytesIO(data['Body'].read())
    # reads decoded data from compressed bytestream above
    data_str = GzipFile(None, 'rb', fileobj=bytestream).read().decode('utf-8')
    # load string from unzipped data into json to return to lambda_handler
    data_json = json.loads(data_str)
    # print(data_json) # debugging when you dont want to parse timestamps
    return data_json


def get_events(json_data, event_type):
    """
    Function takes json and an AWS event type to get events of that type. This
    could be split into get_events and a function to return specific information
    on the events. In this case, it serves a specific purpose to return known
    data field so for brevity, leaving this as a single function.

    :param json_data: json event data
    :param event_type: case-sensitive AWS event name to search for
    :return tuple containing user, role, and instance names
    """
    for record in json_data['Records']:
        if record['eventName'] == event_type:
            logger.info('RUNINSTANCES event found.')
            # 'arn' contains assumed role & user in single field, easy to split
            iam_entity = record['userIdentity']['arn']
            arn, role, username = iam_entity.split('/')
            logger.info(f'Assumed Role == {role}\nUsername == {username}')
            instances = record['responseElements']['instancesSet']['items']
            # list for storing instance names in ['items'] above
            instance_names = []
            for item in instances:
                instance_name = item['instanceId']
                instance_names.append(instance_name)
            return (1, username, role, instance_names)
    return (0, 'Event not present.')


def update_slack(username, role, instances):
    """
    Function takes username, role, and instance names and sends data to POST
    to Slack channel.

    :param username: username affilliated with AWS event
    :param role: assumed AWS role of user
    :param instances: Names of instances launched in AWS
    :return http status code for future error handling
    """
    # formatting to return list of instance names in slack response
    instance_str = '\n'.join(instances)
    header = {"content-type": "application/json"}
    data = {
        "text": "RunInstances event detected.",
        "attachments": [
            {
                "author_name": f"User: {username}\nRole: {role}",
                "title": "Instance Names",
                "text": instance_str,
                "color": "#FF0000"
            }
        ]
    }
    send_to_slack = requests.post(SLACK_URL, headers=header, json=data)
    logger.info(f'Slack POST returned HTTP code {send_to_slack.status_code}')
    return send_to_slack.status_code


def lambda_handler(event, context):
    """
    No return value required when executed from an event. Per AWS documentation;
    "Optionally, the handler can return a value... If you use the Event
    invocation type (asynchronous execution), the value is discarded."
    https://docs.aws.amazon.com/lambda/latest/dg/python-programming-model-handler-types.html
    """
    json_data = format_data(event)
    event_vals = get_events(json_data, 'RunInstances')
    if event_vals[0] == 1:
        username = event_vals[1]
        iam_role = event_vals[2]
        instance_names = event_vals[3]
        update_slack(username, iam_role, instance_names)
