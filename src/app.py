import json
import os
import urllib.request
import boto3

ssm = boto3.client('ssm')

def get_parameter(name):
    response = ssm.get_parameter(Name=name, WithDecryption=True)
    return response['Parameter']['Value']

def notify_slack(event, context):
    # SSM Parameter Store から Slack OAuth Token と Channel ID を取得
    slack_token = get_parameter(os.environ['SLACK_BOT_TOKEN_PARAMETER'])
    channel_id = get_parameter(os.environ['SLACK_CHANNEL_ID_PARAMETER'])
    
    # CloudWatch Logs サブスクリプションフィルターイベントからデータを取得
    try:
        # Base64 エンコードされているデータをデコードし、gzip 圧縮を解凍
        compressed_data = base64.b64decode(event['awslogs']['data'])
        decompressed_data = gzip.decompress(compressed_data)
        log_event = json.loads(decompressed_data)

        log_group = log_event['logGroup']
        log_stream = log_event['logStream']
        
        # 各ログイベントを処理
        error_log_message = ""
        for log in log_event['logEvents']:
            timestamp = datetime.fromtimestamp(log['timestamp'] / 1000, timezone(timedelta(hours=+9), 'JST'))
            error_log_message += str(timestamp) + ': '  + "\n" + log['message'] + "\n---\n"
                
        # Slack に送信するメッセージを作成
        slack_message = {
            'username': 'Error Notifiy Bot',
            'channel': channel_id,
            'text': f"アプリケーションエラーが発生しました。\n*ErrorLog Message*: \n{error_log_message}\n*CloudWatchLogs Log Group*: {log_group}\n*CloudWatchLogs Log Stream*: {log_stream}"
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
                response_data = json.loads(response_body)

                # Slack API のレスポンスをチェック
                if not response_data.get("ok"):
                    error_message = response_data.get("error", "Unknown error")
                    raise Exception(f"Slack API error: {error_message}")
                
                print(f"Message posted to Slack: {response_body}")
        
        except Exception as e:
            print(f"Failed to send message to Slack: {e}")
            raise e  # Lambda 関数をエラーとして終了させる

    except Exception as e:
        print(f"Error processing CloudWatch Logs event: {e}")
        raise e

    return {
        'statusCode': 200,
        'body': json.dumps('Message sent to Slack')
    }

def lambda_handler(event, context):
  notify_slack(event, context)

