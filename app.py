#!/usr/bin/env python3

from aws_cdk import core

from api_gw_to_ecs_s3.api_gw_to_ecs_s3_stack import ApiGwToEcsS3Stack


app = core.App()
ApiGwToEcsS3Stack(app, "api-gw-to-ecs-s3")

app.synth()
