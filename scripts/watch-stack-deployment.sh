#!/usr/bin/env bash

# Check input
if [ -z "$1" ]; then
  echo "usage: $0 stack-name"
  exit
fi
STACK_NAME="$1"

# Show events until stack is updated
while true
do
  STACK_STATUS=`aws cloudformation describe-stack-events --stack-name "$STACK_NAME" --max-items 1 | jq -r '.StackEvents[].ResourceStatus'`
  echo "$STACK_STATUS"
  if [ "$STACK_STATUS" == "UPDATE_COMPLETE" ]; then
    break
  fi
  sleep 5
done
