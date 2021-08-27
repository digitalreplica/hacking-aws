#!/usr/bin/env python3
import json
import requests
import sys
from urllib.parse import urlparse, urlunparse

# Help
if len(sys.argv) == 1:
    print("Usage: {} url(s)".format(sys.argv[0]))
    print("- walks a url path back to the root, trying each one")
    exit()

# Functions
def test_url(url):
    r = requests.get(url)
    print("{} - {}".format(r.status_code, url))
    return r.status_code

# Main program
# Loop over all urls given on command line
urls = sys.argv[1:]
accessible_urls = []
for url in urls:
    # Unpack url and split the path
    parsed_url = urlparse(url)
    split_path = parsed_url.path.split('/')

    # Walk the path backwards
    while split_path:
        joined_url = '/'.join(split_path)
        parsed_url_copy = [
            parsed_url[0],
            parsed_url[1],
            parsed_url[2],
            parsed_url[3],
            parsed_url[4],
            parsed_url[5],
        ]

        # Test as directory, with parameters. Will succeed if public, or have S3 signed url
        parsed_url_copy[2] = joined_url + '/'   # Replace path portion of urlparse
        url_to_test = urlunparse(parsed_url_copy)
        if test_url(url_to_test) == 200:
            accessible_urls.append(url_to_test)

        # Test as file, with parameters. Will succeed if public, or have S3 signed url
        parsed_url_copy[2] = joined_url  # Replace path portion of urlparse
        url_to_test = urlunparse(parsed_url_copy)
        if test_url(url_to_test) == 200:
            accessible_urls.append(url_to_test)

        # Remove parameters for remaining tests, if they exist
        if parsed_url_copy[3] or parsed_url_copy[4] or parsed_url_copy[5]:
            parsed_url_copy[3] = ""
            parsed_url_copy[4] = ""
            parsed_url_copy[5] = ""

            # Test as directory, without parameters. Will succeed if public
            parsed_url_copy[2] = joined_url + '/'   # Replace path portion of urlparse
            url_to_test = urlunparse(parsed_url_copy)
            if test_url(url_to_test) == 200:
                accessible_urls.append(url_to_test)

            # Test as file, without parameters. Will succeed if public
            parsed_url_copy[2] = joined_url  # Replace path portion of urlparse
            url_to_test = urlunparse(parsed_url_copy)
            if test_url(url_to_test) == 200:
                accessible_urls.append(url_to_test)

        # Pop and loop
        split_path.pop()

print("")
print("Accessible Urls")
print(json.dumps(accessible_urls, indent=2))