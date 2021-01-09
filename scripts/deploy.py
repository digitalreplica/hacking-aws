#!/usr/bin/env python3
import argparse
import boto3
import botocore
import glob
import json
from pathlib import Path
import os
import time

##### Configuration #####
CONFIG = {
    "cloudformation_files": "cloudformation/*.json",
    "public_website_dir": "files/s3-public-website",
    "output_save_location": "stack_output.json"
}
CLOUDFORMATION_COMPLETE_STATUSES = [
    "CREATE_COMPLETE",
    "UPDATE_COMPLETE"
]
CONTENT_TYPE_MAPPING = {
    ".html": "text/html",
    ".js": "text/javascript"
}

##### Deploy Class #####
class AwsDeploy:
    def __init__(self, deployment):
        self.deployment = deployment
        self.cloudformation_client = boto3.client('cloudformation')
        self.s3_resource = boto3.resource('s3')
        self.outputs = []

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
        stack_name = "{}-{}".format(
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
                    print("- no updates required")
                    # Describe the stack to get its outputs
                    stack_info = self.cloudformation_client.describe_stacks(StackName=stack_name)
                    self.gather_stack_output(stack_info)

                    # Unset stack_id, so we don't wait for stack changes to complete
                    stack_id = None
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
            self.gather_stack_output(stack_info)
        print("")

    def gather_stack_output(self, stack_info):
        '''
        Gathers all outputs from the stack, so it can be referenced by later deployment steps.
        :return:
        '''
        stack_outputs = stack_info.get('Stacks')[0].get('Outputs', [])
        self.outputs = self.outputs + stack_outputs

        # Print it
        for output_info in stack_outputs:
            print("{} : {}".format(output_info.get('OutputKey'), output_info.get('OutputValue')) )

    def save_stack_outputs(self):
        '''
        Saves the stack outputs into a JSON file
        :return:
        '''
        print("Saving stack outputs to {}".format(CONFIG["output_save_location"]))
        with open(CONFIG["output_save_location"], "w") as output_file:
            json.dump(self.outputs, output_file, indent=2)

    def get_output_value(self, key):
        '''
        Finds the stack OutputValue for a given OutputKey
        :return: OutputValue
        '''
        for output_info in self.outputs:
            if output_info.get('OutputKey') == key:
                return output_info.get('OutputValue')
        return None

    def sync_s3_bucket(self, bucket_name, local_dir):
        '''
        Syncs a local directory with a given bucket
        :return:
        '''
        for file in Path(local_dir).glob('**/*'):
            if os.path.isfile(file):
                # Get path, relative to local_dir
                relative_file_path = os.path.relpath(file, start=local_dir)
                (file_base, file_ext) = os.path.splitext(file)

                # Determine file type
                file_type = 'binary/octet-stream'
                if file_ext in CONTENT_TYPE_MAPPING:
                    file_type = CONTENT_TYPE_MAPPING[file_ext]

                print("  {} -> {} (as {})".format(file, relative_file_path, file_type))
                self.s3_resource.meta.client.upload_file(
                    str(file),
                    bucket_name,
                    relative_file_path,
                    ExtraArgs={'ACL': 'public-read', 'ContentType':file_type})

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
        my_aws.save_stack_outputs()

        # Copy S3 files
        print("")
        public_bucket_name = my_aws.get_output_value('PublicBucketName')
        print("Copying website files to {}".format(public_bucket_name))
        my_aws.sync_s3_bucket(public_bucket_name, CONFIG["public_website_dir"])
    else:
        parse.print_help()
