#!/usr/bin/env bash

# Configure python
if [ ! -d "venv" ]; then
  echo "Creating python virtual environment"
  python3 -m venv venv
  source venv/bin/activate
  pip3 install --upgrade pip
  pip3 install -r requirements.txt
  echo ""
else
  source venv/bin/activate
fi

# Get deployment name, or default
DEPLOYMENT_NAME="bugbounty"
if [ -n "$1" ]; then
  if [ "$1" == "--help" ]; then
    echo "Usage: $0 <deployment-tag>"
    echo ""
    echo "<deployment-tag>: unique name for this deployment."
    echo ""
    exit
  fi
  DEPLOYMENT_NAME="$1"
fi

exit
# Deploy Cloudformation templates
echo "Deploying Cloudformation templates tagged with $DEPLOYMENT_NAME"
python3 scripts/deploy.py --deployment "$DEPLOYMENT_NAME"
