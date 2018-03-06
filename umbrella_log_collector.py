'''
    This module is specifically for Umbrella log collection operations. This is for the Amazon S3 API.
'''
import os
import boto3
from pathlib import Path

# ========================================================
# Load required parameters from environment variables
# ========================================================

s3_bucket = os.getenv("S3_BUCKET")
s3_key = os.getenv("S3_ACCESS_KEY_ID")
s3_secret = os.getenv("S3_SECRET_ACCESS_KEY")

if not s3_bucket or not s3_key or not s3_secret:
    print("umbrella_log_collector.py - Missing Environment Variable.")
    if not s3_bucket:
        print("S3_BUCKET")
    if not s3_key:
        print("S3_ACCESS_KEY_ID")
    if not s3_secret:
        print("S3_SECRET_ACCESS_KEY")

# ========================================================
# Initialize Program - Function Definitions
# ========================================================


def download_dir(client, resource, dist, local='/tmp', bucket=''):
    '''
    This code was taken from here:
    https://stackoverflow.com/questions/31918960/boto3-to-download-all-files-from-a-s3-bucket

    :param client:
    :param resource:
    :param dist:
    :param local:
    :param bucket:
    :return: Nothing. This function will download files to the local filesystem.
    '''

    paginator = client.get_paginator('list_objects')
    for result in paginator.paginate(Bucket=bucket, Delimiter='/', Prefix=dist):
        if result.get('CommonPrefixes') is not None:
            for subdir in result.get('CommonPrefixes'):
                download_dir(client, resource, subdir.get('Prefix'), local, bucket)
        if result.get('Contents') is not None:
            for file in result.get('Contents'):
                print(file.get('Key'))
                if not os.path.exists(os.path.dirname(local + os.sep + file.get('Key'))):
                     os.makedirs(os.path.dirname(local + os.sep + file.get('Key')))

                my_file = Path(local + os.sep + file.get('Key'))
                if my_file.is_file():
                    # already exists, don't download again
                    pass
                else:
                    resource.meta.client.download_file(bucket, file.get('Key'), local + os.sep + file.get('Key'))


def cleanup_files(cl, dist, local='/tmp'):
    '''
    Check to see if any files / directories need to be removed from the file system. First, take a list of all objects
    in the bucket, then compare to the file system. If anything exists on the filesystem that is not in the object
    list, delete.

    :param cl: boto3 client
    :param dist: String. Subfolder to clean up.
    :param local: String. Base path to clean up. (so it's local/dist or local\dist)
    :return: Nothing
    '''

    # Get list of all AWS S3 objects
    s3flist = []
    try:
        objd = cl.list_objects_v2(Bucket=s3_bucket)
    except:
        objd = None
        print("Error Attempting to load S3 Objects")

    if objd:
        for x in objd["Contents"]:
            s3flist.append(x["Key"])

        # Get list of all filesystem objects
        try:
            flist = os.listdir(local + os.sep + dist)
            # Iterate list of fs objects
            for fdir in flist:
                # Everything in the base path should be a directory. Only continue if this is a directory object
                if os.path.isdir(local + os.sep + dist + fdir):
                    # Check to see how many files are in this directory
                    flist2 = os.listdir(local + os.sep + dist + fdir)
                    # If 0 files, delete directory
                    if len(flist2) == 0:
                        print("removing empty directory " + local + os.sep + dist + fdir)
                        os.rmdir(local + os.sep + dist + fdir)

                    # Iterate list of files
                    for fn in flist2:
                        fpath = dist + fdir + os.sep + fn
                        # If this file is not in the Amazon S3 object list, then we want to delete
                        if fpath not in s3flist:
                            print("delete " + local + os.sep + fpath)
                            os.remove(local + os.sep + fpath)
        except:
            print("Error: unable to clean up...")


def get_logs():
    '''
    Main entry point for log collection.

    :return: Nothing
    '''

    print("Parsing Umbrella logs...")
    cl = boto3.client(
            's3',
            aws_access_key_id=s3_key,
            aws_secret_access_key=s3_secret,
            region_name="us-east-1"
        )
    rs = boto3.resource(
            's3',
            aws_access_key_id=s3_key,
            aws_secret_access_key=s3_secret,
            region_name="us-east-1"
        )

    try:
        download_dir(cl, rs, 'dnslogs/', '/tmp', s3_bucket)
    except:
        print("Error Loading Logs...")

    cleanup_files(cl, 'dnslogs/', '/tmp')
    # print("Sleeping for 5 minutes...")
    # time.sleep(60*5)   # Delay for 5 minute (60 seconds * 5 minutes).

if __name__ == '__main__':
    get_logs()