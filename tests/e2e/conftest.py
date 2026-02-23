import pytest
import logging
import os
import boto3
import base64

logger = logging.getLogger(__name__)

def pytest_addoption(parser):
    parser.addoption(
        "--stack-name",
        action="store",
        default=None,
        help="AWS MATLAB Linux S3 template URL",
    )
    parser.addoption(
        "--aws-region",
        action="store",
        default=None,
        help="AWS region to deploy",
    )

def _get_config_value(request, option_name, env_var_name):
    value = request.config.getoption(f"--{option_name}")
    if value:
        logger.info(f"Configuration '{option_name}' loaded from CLI argument: {value}")
        return value
    value = os.environ.get(env_var_name)
    if value:
        logger.info(
            f"Configuration '{option_name}' loaded from environment variable {env_var_name}: {value}"
        )
        return value

    error_msg = f"Missing configuration. Provide either --{option_name} or set {env_var_name} environment variable."
    logger.error(error_msg)
    pytest.fail(error_msg)

@pytest.fixture(scope="session")
def stack_name(request):
    return _get_config_value(request, "stack-name", "STACK_NAME")

@pytest.fixture(scope="session")
def aws_region(request):
    return _get_config_value(request, "aws-region", "AWS_REGION")

@pytest.fixture(scope="session")
def license_string():
    value = os.environ.get("MATLAB_LICENSE_STRING")
    if value:
        return value
    else:
        pytest.fail("Missing MATLAB_LICENSE_STRING env var")

@pytest.fixture(scope="session")
def ec2_client(aws_region):
    return boto3.client("ec2", region_name=aws_region)

@pytest.fixture(scope="session")
def cf_client(aws_region):
    return boto3.client("cloudformation", region_name=aws_region)

@pytest.fixture(scope="session")
def ssm_client(aws_region):
    return boto3.client("ssm", region_name=aws_region)

@pytest.fixture(scope="session")
def instance_id(cf_client, stack_name):
    logger.info(f"Retrieving Instance ID for stack: {stack_name}")
    try:
        resources = cf_client.describe_stack_resources(StackName=stack_name)
        for resource in resources["StackResources"]:
            if resource["ResourceType"] == "AWS::EC2::Instance":
                instance_id_value = resource["PhysicalResourceId"]
                logger.info(f"Instance ID retrieved: {instance_id_value}")
                return instance_id_value
        pytest.fail(f"Could not find an EC2 Instance ID in stack '{stack_name}' outputs or resources.")
    except Exception as e:
        error_msg = f"Failed to retrieve instance ID from stack '{stack_name}': {str(e)}"
        logger.error(error_msg)
        pytest.fail(error_msg)


@pytest.fixture(scope="session")
def transfer_license(ssm_client, instance_id, license_string):
    logger.info("Trying to transfer license file...")
    b64_content = base64.b64encode(license_string.encode("utf-8")).decode("utf-8")
    remote_path = "/tmp/license.dat"
    command = (
        f"set +x; " # Disable shell echoing
        f"echo '{b64_content}' | base64 -d | tee {remote_path}; "
    )
    try:
        response = ssm_client.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={"commands": [command]},
            Comment=f"Transferring license file."
        )
        command_id = response["Command"]["CommandId"]
        
        waiter = ssm_client.get_waiter('command_executed')
        
        try:
            waiter.wait(
                CommandId=command_id,
                InstanceId=instance_id,
                WaiterConfig={
                    'Delay': 2,
                    'MaxAttempts': 30
                }
            )
        except boto3.exceptions.WaiterError as e:
            logger.error(f"Timeout waiting for SSM command execution: {e}")
            raise

        output = ssm_client.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id,
        )
        
        if output['Status'] == 'Success':
            logger.info(f"License transfer successful. Remote path: {remote_path}")
            return True
        else:
            logger.error(f"SSM Failed. Status: {output['Status']}. Error: {output.get('StandardErrorContent')}")
            raise Exception(f"SSM Transfer failed: {output.get('StatusDetails')}")

    except Exception as e:
        logger.error(f"Failed to transfer license: {str(e)}")
        raise

