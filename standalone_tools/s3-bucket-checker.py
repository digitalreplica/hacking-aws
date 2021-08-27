import arn
import boto3
import json
import pytest
import re
import requests
import sys
from urllib.parse import urlparse, urlunparse

##### Helper functions #####
def parse_s3_url(url):
    '''
    Parses a url-based S3 bucket path
    :param url: a URL matching common AWS S3 formats
    :return: dict
    Example: url=https://my-bucket.s3.us-west-2.amazonaws.com/folder1/image.png
    {
      "urls": [
        "https://my-bucket.s3.us-west-2.amazonaws.com/folder1/image.png"
      ],
      "objects": [
        "/folder1/image.png"
      ],
      "arn": "arn:aws:s3:us-west-2::my-bucket",
      "bucket": "my-bucket",
      "region": "us-west-2",
      "account": null
    }
    '''
    parsed_url = urlparse(url)
    data = {
        "urls": [url],
        "objects": [parsed_url.path],
        "arn": None,
        "bucket": None,
        "region": None,
        "account": None
    }

    # Try dualstack formats first, to allow '.' characters in later patterns
    ## Try {bucketname}.s3.dualstack.{aws-region}.amazonaws.com
    match = re.match(r"(.*?)\.s3\.dualstack\.(.*?)\.amazonaws.com", parsed_url.hostname)
    if match:
        #print("- matches {bucketname}.s3.dualstack.{aws-region}.amazonaws.com")
        data["bucket"] = match.group(1)
        data["region"] = match.group(2)
        data["arn"] = "arn:aws:s3:{region}::{bucket_name}".format(
            region=match.group(2),
            bucket_name=match.group(1)
        )
        return data

    ## Try s3.dualstack.{aws-region}.amazonaws.com/{bucketname}
    match = re.match(r"s3\.dualstack\.(.*?)\.amazonaws.com", parsed_url.hostname)
    if match:
        #print("- matches s3.dualstack.{aws-region}.amazonaws.com/{bucketname}")
        data["region"] = match.group(1)

        # match path for /{bucketname}/{object-path}
        match = re.match(r"/(.*?)(/.*)", parsed_url.path)
        data["bucket"] = match.group(1)
        data["objects"][0] = match.group(2)
        data["arn"] = "arn:aws:s3:{region}::{bucket_name}".format(
            region=data["region"],
            bucket_name=match.group(1)
        )
        return data

    # Try AWS REST endpoints with bucket names: lowercase letters, numbers, dots (.), and hyphens (-)
    ## Try {bucketname}.s3.{aws-region}.amazonaws.com
    match = re.match(r"(.*?)\.s3\.(.*?)\.amazonaws.com", parsed_url.hostname)
    if match:
        #print("- matches {bucketname}.s3.{aws-region}.amazonaws.com")
        data["bucket"] = match.group(1)
        data["region"] = match.group(2)
        data["arn"] = "arn:aws:s3:{region}::{bucket_name}".format(
            region=match.group(2),
            bucket_name=match.group(1)
        )
        return data

    ## Try s3.{aws-region}.amazonaws.com/{bucketname}
    match = re.match(r"s3\.(.*?)\.amazonaws.com", parsed_url.hostname)
    if match:
        #print("- matches s3.{aws-region}.amazonaws.com/{bucketname}")
        data["region"] = match.group(1)
        # match path for /{bucketname}/{object-path}
        match = re.match(r"/(.*?)(/.*)", parsed_url.path)
        data["bucket"] = match.group(1)
        data["objects"][0] = match.group(2)
        data["arn"] = "arn:aws:s3:{region}::{bucket_name}".format(
            region=data["region"],
            bucket_name=match.group(1)
        )
        return data

    # Try S3 static website formats
    ## Try http://{bucket-name}.s3-website-{aws-region}.amazonaws.com
    match = re.match(r"(.*?)\.s3-website-(.*?)\.amazonaws.com", parsed_url.hostname)
    if match:
        #print("- matches {bucket-name}.s3-website-{aws-region}.amazonaws.com")
        data["bucket"] = match.group(1)
        data["region"] = match.group(2)
        data["arn"] = "arn:aws:s3:{region}::{bucket_name}".format(
            region=match.group(2),
            bucket_name=match.group(1)
        )
        return data

    ## Try http://{bucket-name}.s3-website.{aws-region}.amazonaws.com
    match = re.match(r"(.*?)\.s3-website\.(.*?)\.amazonaws.com", parsed_url.hostname)
    if match:
        #print("- matches {bucket-name}.s3-website.{aws-region}.amazonaws.com")
        data["bucket"] = match.group(1)
        data["region"] = match.group(2)
        data["arn"] = "arn:aws:s3:{region}::{bucket_name}".format(
            region=match.group(2),
            bucket_name=match.group(1)
        )
        return data

    # Nothing matched
    return None

##### Test url parsing #####
@pytest.mark.parametrize("url", [
    "https://my-bucket.s3.us-west-2.amazonaws.com/aaa5f5ee-846b-43b4-a126-673c07ff44a5/image.png",
    "https://s3.us-west-2.amazonaws.com/my-bucket/aaa5f5ee-846b-43b4-a126-673c07ff44a5/image.png",
    "https://my-bucket.s3.dualstack.us-west-2.amazonaws.com/aaa5f5ee-846b-43b4-a126-673c07ff44a5/image.png",
    "https://s3.dualstack.us-west-2.amazonaws.com/my-bucket/aaa5f5ee-846b-43b4-a126-673c07ff44a5/image.png",
    "http://my-bucket.s3-website-us-west-2.amazonaws.com/aaa5f5ee-846b-43b4-a126-673c07ff44a5/image.png",
    "http://my-bucket.s3-website.us-west-2.amazonaws.com/aaa5f5ee-846b-43b4-a126-673c07ff44a5/image.png"
])
def test_parse_s3_url(url):
    parsed_url = parse_s3_url(url)
    assert parsed_url["arn"] == "arn:aws:s3:us-west-2::my-bucket"
    assert parsed_url["bucket"] == "my-bucket"
    assert parsed_url["region"] == "us-west-2"
    assert parsed_url["account"] == None
    assert parsed_url["urls"][0] == url
    assert parsed_url["objects"][0] == "/aaa5f5ee-846b-43b4-a126-673c07ff44a5/image.png"
    print(json.dumps(parsed_url, indent=2))
    print("")

##### S3 checks #####
# All S3 checks accept a dictionary returned from parse_s3_url
def does_bucket_exist(data, triesLeft=2):
    '''
    :param data: parse_s3_url dict
    :return: true|false
    Checks bucket existence by hitting S3 REST endpoint
    Basic logic taken from https://github.com/sa7mon/S3Scanner/blob/master/s3utils.py
    '''
    return_data = {
        "exists": False,
        "public": False,
        "reason": ""
    }
    if triesLeft == 0:
        return_data["reason"] = "{} returns 503 status".format(bucketUrl)
        return return_data

    bucketUrl = 'http://' + data["bucket"] + '.s3.amazonaws.com'

    r = requests.head(bucketUrl)

    if r.status_code == 200:    # Successfully found a bucket!
        return_data["exists"] = True
        return_data["public"] = True
        return_data["reason"] = "{} returns 200 status".format(bucketUrl)
        return return_data
    elif r.status_code == 403:  # Bucket exists, but we're not allowed to LIST it.
        return_data["exists"] = True
        return_data["reason"] = "{} returns 403 status".format(bucketUrl)
        return return_data
    elif r.status_code == 404:  # This is definitely not a valid bucket name.
        return_data["reason"] = "{} returns 404 status".format(bucketUrl)
        return return_data
    elif r.status_code == 503:
        return does_bucket_exist(data, triesLeft - 1)
    else:
        raise ValueError("Got an unhandled status code back: " + str(r.status_code) + " for bucket: " + data["bucket"])

if __name__ == "__main__":
    # Get url argument
    if len(sys.argv) < 2:
        print("Usage: {} <S3 Url>".format(sys.argv[0]))
    url = sys.argv[1]
    parsed_url = parse_s3_url(url)
    print(json.dumps(parsed_url, indent=2))
    print("")

    # Bucket existence
    print("does_bucket_exist()")
    bucket_exists = does_bucket_exist(parsed_url)
    print(json.dumps(bucket_exists, indent=2))
