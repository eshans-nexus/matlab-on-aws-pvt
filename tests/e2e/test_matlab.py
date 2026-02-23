import pytest
import logging

logger = logging.getLogger(__name__)

@pytest.mark.usefixtures("transfer_license")
def test_matlab_hello_world(ssm_client, instance_id):
    matlab_cmd = "ver"
    shell_cmd = f'export MLM_LICENSE_FILE=/tmp/license.dat; matlab -licmode file -batch "{matlab_cmd}"'
    
    logger.info(f"Sending MATLAB command to {instance_id}...")
    
    response = ssm_client.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [shell_cmd]},
        Comment="Running MATLAB Smoke Test"
    )
    command_id = response["Command"]["CommandId"]
    
    waiter = ssm_client.get_waiter('command_executed')
    try:
        waiter.wait(
            CommandId=command_id,
            InstanceId=instance_id,
            WaiterConfig={'Delay': 5, 'MaxAttempts': 20}
        )
    except Exception as e:
        pytest.fail(f"Timeout waiting for MATLAB command: {e}")

    output = ssm_client.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id,
    )
    
    stdout = output.get('StandardOutputContent', '')
    stderr = output.get('StandardErrorContent', '')
    status = output.get('Status')

    logger.info(f"MATLAB Output:\n{stdout}")
    
    if status != 'Success':
        logger.error(f"MATLAB Error Output:\n{stderr}")
        pytest.fail(f"MATLAB command failed with status: {status}")

    assert "MATLAB Version:" in stdout, "MATLAB did not output the expected success message."
