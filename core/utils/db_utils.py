import os, json, boto3
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

def get_rds_credentials():
    """
    Retrieve DB credentials from AWS Secrets Manager if available.
    Fallback: environment variables.
    Final fallback: None (signals SQLite use).
    """

    secret_name = "rds!db-7bd3cc4b-9cc9-4678-ae33-e127d19231ab"
    region_name = "ap-south-1"

    # Case 1: Try AWS Secrets Manager
    try:
        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager", region_name=region_name)

        resp = client.get_secret_value(SecretId=secret_name)
        secret_str = resp.get("SecretString")
        if secret_str:
            creds = json.loads(secret_str)
            logger.info("Loaded DB credentials from Secrets Manager")

            # normalize keys
            norm = {k.lower(): v for k, v in creds.items()}

            return {
                "NAME": norm.get("dbname") or norm.get("name"),
                "USER": norm.get("username") or norm.get("user"),
                "PASSWORD": norm.get("password"),
                "HOST": norm.get("host"),
                "PORT": int(norm.get("port") or 3306),
            }
    except ClientError as e:
        logger.warning(f"Secrets Manager lookup failed: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error fetching secret: {e}")

    # Case 2: Fall back to env vars
    db_host = os.getenv("DB_HOST")
    if db_host:
        logger.info("Loaded DB credentials from environment variables")
        return {
            "NAME": os.getenv("DB_NAME", ""),
            "USER": os.getenv("DB_USER", ""),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": db_host,
            "PORT": int(os.getenv("DB_PORT") or 3306),
        }

    # Case 3: Fallback to None (use SQLite)
    logger.info("No DB credentials found; fallback to SQLite")
    return None
