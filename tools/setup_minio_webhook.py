import boto3
import sys
from pathlib import Path

# Ensure project root is importable when run from tools/ or repo root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.minio_config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, BUCKET_NAME, WEBHOOK_SECRET

def setup_minio_notification():
    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name="us-east-1"
    )

    print(f"Connecting to MinIO at {MINIO_ENDPOINT}...")

    # Configuration for the webhook
    # NOTE: You must replace 'YOUR_FASTAPI_IP' with the actual IP address or hostname
    # that MinIO can reach. 'localhost' usually refers to the MinIO container itself.
    WEBHOOK_ARN = "arn:minio:sqs::_:webhook" 
    
    # ⚠️ IMPORTANT:
    # MinIO requires you to configure the webhook target in its server config or environment variables FIRST.
    # You cannot create an arbitrary webhook target via the S3 API alone if it's not registered.
    # However, if you are using standard MinIO with 'MINIO_NOTIFY_WEBHOOK_ENABLE_webhook=on',
    # you can set the configuration.
    
    # Since we can't easily change MinIO server config from here, this script 
    # will mostly serve to PRINT instructions or set the bucket notification 
    # IF the target is already configured.
    
    print("\nMinIO Webhook Configuration Guide")
    print("-----------------------------------")
    print("1. MinIO needs to know about your FastAPI endpoint.")
    print("2. Start MinIO with environment variables:")
    print("   MINIO_NOTIFY_WEBHOOK_ENABLE_primary=on")
    print(f"   MINIO_NOTIFY_WEBHOOK_ENDPOINT_primary=http://host.docker.internal:8000/webhook/minio")
    print(f"   MINIO_NOTIFY_WEBHOOK_AUTH_TOKEN_primary={WEBHOOK_SECRET}")
    print("\n   (Replace 'host.docker.internal' with your machine IP if not running in Docker)")
    print("\n   Example Docker Command:")
    print(f'   docker run -p 9000:9000 -p 9090:9090 --name minio \\')
    print(f'     -e "MINIO_ROOT_USER={MINIO_ACCESS_KEY}" \\')
    print(f'     -e "MINIO_ROOT_PASSWORD={MINIO_SECRET_KEY}" \\') 
    print(f'     -e "MINIO_NOTIFY_WEBHOOK_ENABLE_primary=on" \\')
    print(f'     -e "MINIO_NOTIFY_WEBHOOK_ENDPOINT_primary=http://host.docker.internal:8000/webhook/minio" \\')
    print(f'     -e "MINIO_NOTIFY_WEBHOOK_AUTH_TOKEN_primary={WEBHOOK_SECRET}" \\')
    print(f'     minio/minio server /data --console-address ":9090"')
    
    print("\n3. Once started, apply the bucket notification:")
    
    try:
        # This assumes a webhook config named 'primary' exists on the server
        s3.put_bucket_notification_configuration(
            Bucket=BUCKET_NAME,
            NotificationConfiguration={
                'QueueConfigurations': [
                    {
                        'Id': 'FastAPI-Webhook',
                        'QueueArn': 'arn:minio:sqs::primary:webhook',
                        'Events': ['s3:ObjectCreated:*', 's3:ObjectRemoved:*'],
                        'Filter': {
                            'Key': {
                                'FilterRules': [
                                    {'Name': 'prefix', 'Value': ''}
                                ]
                            }
                        }
                    }
                ]
            }
        )
        print(f"Bucket notification synced!")
    except Exception as e:
        print(f"\nCould not set bucket notification via API.")
        print(f"Reason: {e}")
        print("This is expected if the 'primary' webhook ARN is not configured in MinIO env vars.")

if __name__ == "__main__":
    setup_minio_notification()
