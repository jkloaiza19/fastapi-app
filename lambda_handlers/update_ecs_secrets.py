import boto3
import json


def lambda_handler(event, context):
    ecs_client = boto3.client("ecs")
    secrets_client = boto3.client("secretsmanager")

    # Secret and ECS details
    secret_arn = "arn:aws:secretsmanager:us-west-2:123456789012:secret:my-app-secret"
    cluster_name = "my-cluster"
    service_name = "my-service"
    task_family = "my-task"

    # Get updated secret
    secret_value = secrets_client.get_secret_value(SecretId=secret_arn)
    secrets = json.loads(secret_value["SecretString"])

    # Fetch the current task definition
    response = ecs_client.describe_task_definition(taskDefinition=task_family)
    container_definitions = response["taskDefinition"]["containerDefinitions"]

    # Add secrets to the container definitions
    for container in container_definitions:
        container["secrets"] = [
            {"name": key, "valueFrom": f"{secret_arn}:{key}::"}
            for key in secrets.keys()
        ]

    # Register a new task definition with updated secrets
    ecs_client.register_task_definition(
        family=task_family,
        containerDefinitions=container_definitions,
        executionRoleArn=response["taskDefinition"]["executionRoleArn"],
        taskRoleArn=response["taskDefinition"]["taskRoleArn"],
        networkMode=response["taskDefinition"]["networkMode"],
        requiresCompatibilities=response["taskDefinition"]["requiresCompatibilities"],
        cpu=response["taskDefinition"]["cpu"],
        memory=response["taskDefinition"]["memory"]
    )

    # Update the ECS service to use the new task definition
    ecs_client.update_service(
        cluster=cluster_name,
        service=service_name,
        forceNewDeployment=True
    )

    return {"status": "Task Definition Updated"}
