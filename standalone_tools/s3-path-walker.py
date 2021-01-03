#!/usr/bin/env python3
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

# Main program
# Loop over all urls given on command line
urls = sys.argv[1:]
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

        # Test as directory
        parsed_url_copy[2] = joined_url + '/'   # Replace path portion of urlparse
        url_to_test = urlunparse(parsed_url_copy)
        test_url(url_to_test)

        # Test as file
        parsed_url_copy[2] = joined_url  # Replace path portion of urlparse
        url_to_test = urlunparse(parsed_url_copy)
        test_url(url_to_test)

        # Pop and loop
        split_path.pop()
