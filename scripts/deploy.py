#!/usr/bin/env python3
import argparse
import boto3
import botocore
import glob
import os
import time

##### Configuration #####
CONFIG = {
    "cloudformation_files": "cloudformation/*.json"
}
CLOUDFORMATION_COMPLETE_STATUSES = [
    "CREATE_COMPLETE",
    "UPDATE_COMPLETE"
]

##### Deploy Class #####
class AwsDeploy:
    def __init__(self, deployment):
        self.deployment = deployment
        self.cloudformation_client = boto3.client('cloudformation')

    def deploy_stacks(self):
        '''
        Deploys all the cloudformation templates in the cloudformation folder
        :return:
        '''
        for cloudformation_template in glob.glob(CONFIG["cloudformation_files"]):
            self.create_or_update_stack(cloudformation_template)

    def create_or_update_stack(self, cloudformation_template_filename):
        '''
        Creates or updates a cloudformation stack
        :param cloudformation_template: filename of cloudformation template
        :return:
        '''
        # Read in the stack template
        with open(cloudformation_template_filename) as f:
            cloudformation_template = f.read()

        # Tag all stacks with the deployment tag
        stack_name = "".format(
            self.deployment,
            os.path.splitext(os.path.basename(cloudformation_template_filename))[0]
            )

        # Find out if the stack exists
        create_stack = False
        try:
            stack_info = self.cloudformation_client.describe_stacks(StackName=stack_name)
        except botocore.exceptions.ClientError:
            create_stack = True

        # Create or update
        if create_stack:
            print("Creating stack {}".format(stack_name))
            stack_info = self.cloudformation_client.create_stack(StackName=stack_name,
                                                                TemplateBody=cloudformation_template,
                                                                Tags=[
                                                                 { 'Key': 'deployment', 'Value': 'string' },
                                                                ],
                                                                OnFailure='DELETE')
            stack_id = stack_info.get('StackId')
        else:
            print("Updating stack {}".format(stack_name))
            try:
                stack_info = self.cloudformation_client.update_stack(StackName=stack_name,
                                                                   TemplateBody=cloudformation_template)
                stack_id = stack_info.get('StackId')
            except botocore.exceptions.ClientError as e:
                if str(e).endswith('No updates are to be performed.'):
                    stack_id = None
                    print("- no updates required")
                else:
                    raise

        # Wait for stack to complete
        if stack_id:
            while True:
                stack_info = self.cloudformation_client.describe_stack_events(StackName=stack_id)
                stack_status = stack_info.get('StackEvents', [])[0].get('ResourceStatus')
                print(stack_status)
                if stack_status in CLOUDFORMATION_COMPLETE_STATUSES:
                    break
                time.sleep(5)

            # Show stack outputs
            stack_info = self.cloudformation_client.describe_stacks(StackName=stack_name)
            for output_info in stack_info.get('Stacks')[0].get('Outputs', []):
                print("{}:{}".format(output_info.get('OutputKey'), output_info.get('OutputValue')) )
        print("")


##### Find Cloudformation files #####
if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Deploy Cloudformation templates')
    parser.add_argument('-d', '--deployment', action='store', nargs='?', required=True, default="bugbounty",
                        help='Unique name for this deployment')

    args = parser.parse_args()

    if args.deployment:
        my_aws = AwsDeploy(args.deployment)
        my_aws.deploy_stacks()
    else:
        parse.print_help()
