import os

meraki_api_token = os.getenv("MERAKI_API_TOKEN")
meraki_org = os.getenv("MERAKI_ORG")
spark_api_token = os.getenv("SPARK_API_TOKEN")
s3_bucket = os.getenv("S3_BUCKET")
s3_key = os.getenv("S3_ACCESS_KEY_ID")
s3_secret = os.getenv("S3_SECRET_ACCESS_KEY")


def meraki_support():
    if meraki_api_token and meraki_org:
        return True
    else:
        return False


def spark_call_support():
    if spark_api_token:
        return True
    else:
        return False


def umbrella_support():
    if s3_bucket and s3_key and s3_secret:
        return True
    else:
        return False