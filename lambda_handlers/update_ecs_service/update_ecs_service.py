import boto3
import os

ecs_client = boto3.client("ecs")


def lambda_handler(event, context):
    response = ecs_client.update_service(
        cluster=os.environ["ECS_CLUSTER"],
        service=os.environ["ECS_SERVICE"],
        forceNewDeployment=True
    )
    print("ECS Deployment Triggered:", response)
