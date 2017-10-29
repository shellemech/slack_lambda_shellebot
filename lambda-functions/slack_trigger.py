import os
import re
import logging
import urllib
import random
import boto3
from botocore.exceptions import ClientError
from collections import defaultdict

BOT_TOKEN = os.environ["BOT_TOKEN"]
SLACK_URL = "https://slack.com/api/chat.postMessage"
accounts = ['098798438173']

def run_ec2(region, accountid, searchword):
    """Use boto3 to return a list of aws instances.
    """
    instance_list = ''
    sts_client = boto3.client('sts')

    assumedRoleObject = sts_client.assume_role(
        RoleArn="arn:aws:iam::" + accountid + ":role/shellemech_lambda_ro",
        RoleSessionName="AssumeRoleSession1"
    )
    credentials = assumedRoleObject['Credentials']

    # Use the temporary credentials from the AssumeRole, and the region
    ec2 = boto3.resource(
        'ec2',
        aws_access_key_id = credentials['AccessKeyId'],
        aws_secret_access_key = credentials['SecretAccessKey'],
        aws_session_token = credentials['SessionToken'],
        region_name = region
    )

    # Filter the instances, return the list to slack
    if searchword:
        my_instances = ec2.instances.filter(Filters=[
            {'Name': 'tag:owner','Values': ['michelle']},
            {'Name': 'tag:Name','Values': [searchword]}
        ])
    else:
        my_instances = ec2.instances.filter(Filters=[
            {'Name': 'tag:owner','Values': ['michelle']}
        ])
    ec2info = defaultdict()
    for instance in my_instances:
        for tag in instance.tags:
            if 'Name'in tag['Key']:
                name = tag['Value']
        # Add instance info to a dictionary
        ec2info[instance.id] = {
            'Name': name,
            'IP': instance.private_ip_address,
            'State': instance.state["Name"],
            'Launched': instance.launch_time
        }
    for instance_id, instance in ec2info.items():
        instance_list += ">{Name} {IP} {State} {Launched} \n".format(**instance)
    return instance_list

def return_message(message, channel_id):
    """Send data back to slack.
    """
    # We need to send back:
    #     1. The text (text)
    #     2. The channel id (channel)
    #     3. The OAuth slack token (token)
    # Then create a url encoded array
    data = urllib.parse.urlencode(
        (
            ("token", BOT_TOKEN),
            ("channel", channel_id),
            ("text", message)
        )
    )
    data = data.encode("ascii")

    # Construct the HTTP request that will be sent to the Slack API
    request = urllib.request.Request(
        SLACK_URL,
        data=data,
        method="POST"
    )
    # Add a header mentioning that the text is URL-encoded
    request.add_header(
        "Content-Type",
        "application/x-www-form-urlencoded"
    )

    # Fire off the request
    urllib.request.urlopen(request).read()

def handler(data, context):
    """Handle an incoming HTTP request from slack.
    """
    if "challenge" in data:
        return data["challenge"]
    slack_event = data['event']
    channel_id = slack_event["channel"]
    sentence = ((slack_event["text"]).strip()).lower()

    # Ignore event if its from a bot, doesn't start with 'shellebot', or there's no slack token
    if "bot_id" in slack_event or not sentence.startswith("shellebot") or not os.environ["slack_token"] in str(data):
        logging.warn("Ignore bot event")
    else:
        # See if we recognise the command, else return syntax help
        if "list instances" in sentence:
            instances = ''
            searchword = ''
            # Extract search term
            terms = ("mrbc", "chef", "jenkins")
            for term in terms:
                if term in sentence:
                    searchword = term
            for accountid in accounts:
                 instances = "_Here's a list of " + searchword + " instances in us-west-1 (" + accountid + ")_ \n"
                 instances += run_ec2 ("us-west-1", accountid, searchword)
                 instances += "_Here's a list of " + searchword + " instances in us-west-2 (" + accountid + ")_ \n"
                 instances += run_ec2 ("us-west-2", accountid, searchword)
            return_message(instances, channel_id)
        else:
            error_text = ">Uhhhh... ¯\_(ツ)_/¯ \n"
            error_text += ">Syntax: _shellebot list instances <searchword>_ "
            error_text += "You can search for mrbc, chef, jenkins, "
            error_text += "or leave searchword blank to list all instances."
            return_message(error_text, channel_id)
    # A-OK
    return "200 OK"
