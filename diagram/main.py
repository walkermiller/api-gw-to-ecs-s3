#! /usr/bin/env python
from diagrams import Diagram, Edge
from diagrams.aws.compute import ECS
from diagrams.aws.network import ELB
from diagrams.aws.network import APIGateway as apigw
from diagrams.aws.storage import S3

with Diagram("API Gateway To S3 and ECS", show=False, direction="LR"):
    lb = ELB("NLB")
    api_gw = apigw("APIGW")

    api_gw >> Edge(label="/apis") >> lb >> ECS("ECS")
    api_gw >> Edge(label="/images") >> S3("Images")
    api_gw >> Edge(label="/{folder}/{item}") >> S3("Static")
    api_gw >> Edge(label="/") >> S3("index.html")
