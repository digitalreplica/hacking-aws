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

# Deploy Cloudformation templates
echo "Deploying Cloudformation templates"
python3 scripts/deploy.py
