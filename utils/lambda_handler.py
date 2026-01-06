import boto3
import os

def lambda_handler(event, context):
    eb = boto3.client('elasticbeanstalk')
    
    # Update this with your environment name
    environment_name = os.environ.get('EB_ENV_NAME', 'quelo-web-v5-dev')
    
    try:
        response = eb.restart_app_server(EnvironmentName=environment_name)
        print(f"✅ Restart triggered: {response}")
        return {"status": "success"}
    except Exception as e:
        print(f"❌ Failed to restart: {e}")
        return {"status": "error", "message": str(e)}
