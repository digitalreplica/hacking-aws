# AWS Weaponization
* Pentest tools for hacking AWS-based organizations*

# Requirements
* AWS account with Administrator privileges (ideally empty)
* AWS CLI installed and configured
* Python3

# Installation
## Using AWS CloudShell
This is the easiest method, since everything is already configured.

* Open your AWS Console. Search for "CloudShell", or select it from the Services dropdown. Click to open a shell.
* Run
```
git clone https://github.com/digitalreplica/hacking-aws.git
cd hacking-aws/
scripts/deploy.sh
```

# Arsenal

## Public Website
An internet-accessible website to host your html files, xss scripts, and other content. This is hosted on a public S3 bucket, so

### Redirects
Redirects can sometimes be used to bypass SSRF filters. The S3 bucket has automatic redirects for key urls.

* /redirect/http-awsmetadata/ 301 -> http://169.254.169.254/
* /redirect/http-localhost/   301 -> http://localhost/
* /redirect/https-localhost/  301 -> https://localhost/
* /redirect/https-google/     301 -> https://google.com/

Url paths are remapped to the target, so /redirect/http-localhost/foo will redirect to http://localhost/foo , allowing paths and query strings to be appended.
