#core/utils/aws_secrets.py
import os,boto3, json
from botocore.exceptions import ClientError


def get_secret(
    secret_name="rds!db-d696ccf3-bb2b-45bf-b977-1435e53876df",
    region_name="ap-south-1"
):
    """
    Fetch RDS-managed secret (username/password) and supplement
    with static host/port/dbname for Django.
    """

    client = boto3.client("secretsmanager", region_name=region_name)

    try:
        resp = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise RuntimeError(f"Unable to fetch secret {secret_name}: {e}")

    secret_str = resp.get("SecretString")
    if not secret_str:
        raise RuntimeError(f"Secret {secret_name} has no SecretString")

    raw = json.loads(secret_str)

    # RDS-managed secret only has username/password
    username = raw.get("username")
    password = raw.get("password")

    if not username or not password:
        raise RuntimeError(f"Secret {secret_name} missing username/password")

    # 🔹 Fill in static values for host/dbname/port
    return {
        "NAME": "quelo",   # your DB name in RDS
        "USER": username,
        "PASSWORD": password,
        "HOST": "quelo-db-optimized.cdma4wimseay.ap-south-1.rds.amazonaws.com",
        "PORT": 3306,
    }
