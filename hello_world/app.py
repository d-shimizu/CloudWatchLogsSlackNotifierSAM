import json
import os
import urllib.request
import boto3

ssm = boto3.client('ssm')

def get_parameter(name):
    response = ssm.get_parameter(Name=name, WithDecryption=True)
    return response['Parameter']['Value']

def lambda_handler(event, context):
    # SSM Parameter Store から Slack OAuth Token と Channel ID を取得
    slack_token = get_parameter(os.environ['SLACK_BOT_TOKEN_PARAMETER'])
    channel_id = get_parameter(os.environ['SLACK_CHANNEL_ID_PARAMETER'])
    
    # SNS メッセージからログメッセージを取得
    message = json.loads(event['Records'][0]['Sns']['Message'])
    log_message = message.get('AlarmDescription', 'No description available')
    log_data = message.get('NewStateReason', 'No reason available')

    # Slack に送信するメッセージを作成
    slack_message = {
        'channel': channel_id,
        'text': f"*Alert*: {log_message}\n*Details*: {log_data}"
    }

    # Slack API にメッセージを送信
    req = urllib.request.Request(
        'https://slack.com/api/chat.postMessage',
        data=json.dumps(slack_message).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {slack_token}'
        }
    )

    try:
        with urllib.request.urlopen(req) as response:
            response_body = response.read()
            print(f"Message posted to Slack: {response_body}")
    except Exception as e:
        print(f"Failed to send message to Slack: {e}")

    return {
        'statusCode': 200,
        'body': json.dumps('Message sent to Slack')
    }