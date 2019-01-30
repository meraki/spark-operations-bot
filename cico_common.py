'''
    This module is specifically for common functions that are expected to be used in multiple places across the
    various modules
'''
import os


# ========================================================
# Load required parameters from environment variables
# ========================================================

meraki_api_token = os.getenv("MERAKI_API_TOKEN")
meraki_org = os.getenv("MERAKI_ORG")
meraki_http_username = os.getenv("MERAKI_HTTP_USERNAME")
meraki_http_password = os.getenv("MERAKI_HTTP_PASSWORD")
spark_api_token = os.getenv("SPARK_API_TOKEN")
s3_bucket = os.getenv("S3_BUCKET")
s3_key = os.getenv("S3_ACCESS_KEY_ID")
s3_secret = os.getenv("S3_SECRET_ACCESS_KEY")
a4e_client_id = os.getenv("A4E_CLIENT_ID")
a4e_client_secret = os.getenv("A4E_CLIENT_SECRET")


# ========================================================
# Initialize Program - Function Definitions
# ========================================================


def meraki_support():
    '''
    This function is used to check whether the Meraki environment variables have been set. It will return true
    if they have and false if they have not

    :return: true/false based on whether or not Meraki support is available
    '''
    if meraki_api_token:        # and meraki_org: --removed: org auto-selection has been added, so org not required--
        return True
    else:
        return False


def meraki_dashboard_support():
    '''
    This function is used to check whether the Meraki dashboard environment variables have been set. It will return true
    if they have and false if they have not. These variables are optional, and are used to build better cross-launch
    links to the dashboard

    :return: true/false based on whether or not Meraki dashboard support is available
    '''
    if meraki_http_password and meraki_http_username:
        return True
    else:
        return False


def spark_call_support():
    '''
    This function is used to check whether the Spark Call environment variables have been set. It will return true
    if they have and false if they have not

    :return: true/false based on whether or not Spark Call support is available
    '''
    if spark_api_token:
        return True
    else:
        return False


def umbrella_support():
    '''
    This function is used to check whether the Umbrella (S3) environment variables have been set. It will return true
    if they have and false if they have not

    :return: true/false based on whether or not Umbrella support is available
    '''
    if s3_bucket and s3_key and s3_secret:
        return True
    else:
        return False

def a4e_support():
    '''
    This function is used to check whether the Amp for Endpoints environment variables have been set. It will return
    true if they have and false if they have not

    :return: true/false based on whether or not A4E support is available
    '''
    if a4e_client_id and a4e_client_secret:
        return True
    else:
        return False