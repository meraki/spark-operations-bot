import os
import boto3
from pathlib import Path
import time
import sys


s3_bucket = os.getenv("S3_BUCKET")
s3_key = os.getenv("S3_ACCESS_KEY_ID")
s3_secret = os.getenv("S3_SECRET_ACCESS_KEY")

if not s3_bucket or not s3_key or not s3_secret:
    print("Missing Environment Variable.")
    sys.exit()


def download_dir(client, resource, dist, local='/tmp', bucket=''):
    # https://stackoverflow.com/questions/31918960/boto3-to-download-all-files-from-a-s3-bucket
    paginator = client.get_paginator('list_objects')
    for result in paginator.paginate(Bucket=bucket, Delimiter='/', Prefix=dist):
        if result.get('CommonPrefixes') is not None:
            for subdir in result.get('CommonPrefixes'):
                download_dir(client, resource, subdir.get('Prefix'), local, bucket)
        if result.get('Contents') is not None:
            for file in result.get('Contents'):
                if not os.path.exists(os.path.dirname(local + os.sep + file.get('Key'))):
                     os.makedirs(os.path.dirname(local + os.sep + file.get('Key')))

                print(file.get('Key'))
                my_file = Path(local + os.sep + file.get('Key'))
                if my_file.is_file():
                    # already exists, don't download again
                    pass
                else:
                    resource.meta.client.download_file(bucket, file.get('Key'), local + os.sep + file.get('Key'))


def cleanup_files(cl, dist, local='/tmp'):
    s3flist = []
    objd = cl.list_objects_v2(Bucket=s3_bucket)
    for x in objd["Contents"]:
        s3flist.append(x["Key"])

    flist = os.listdir(local + os.sep + dist)
    for fdir in flist:
        if os.path.isdir(local + os.sep + dist + fdir):
            flist2 = os.listdir(local + os.sep + dist + fdir)
            if len(flist2) == 0:
                print("removing empty directory " + local + os.sep + dist + fdir)
                os.rmdir(local + os.sep + dist + fdir)
            for fn in flist2:
                fpath = dist + fdir + os.sep + fn
                if fpath not in s3flist:
                    print("delete " + local + os.sep + fpath)
                    os.remove(local + os.sep + fpath)


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


while True:
    try:
        download_dir(cl, rs, 'dnslogs/', '/tmp', s3_bucket)
    except:
        print("Error Loading Logs...")

    cleanup_files(cl, 'dnslogs/', '/tmp')
    print("Sleeping for 5 minutes...")
    time.sleep(60*5)   # Delay for 5 minute (60 seconds * 5 minutes).
