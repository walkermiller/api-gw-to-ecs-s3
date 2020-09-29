from aws_cdk import (
    core,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_ecs_patterns as ecsp,
    aws_s3 as s3,
    aws_apigateway as gw
)

class ApiGwToEcsS3Stack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

## Create S3 Bucket
        bucket = s3.Bucket(self, "s3-ecs-apigw-test",
            bucket_name="s3-ecs-apigw-test",
            versioned=True,
            public_read_access=False
            )

## Create ECS  Cluster, Taks and Service
        vpc_id = core.CfnParameter(self, 
            "vpcid",
            type="EC2::VPC::Id",
            description="VPC ID")

        vpc = ec2.Vpc.from_lookup(self, "vpc", vpc_id=vpc_id.to_string())

        cluster = ecs.Cluster(self,
            "ecs-apigw-test-cluster",
            cluster_name="ecs-apigw-test-cluster",
            container_insights=True,
            vpc=vpc)

        ecsp.ApplicationLoadBalancedFargateService(self, 
            "ecs-apigw-test",
            cluster=cluster,
            cpu=512,
            desired_count=1,
            public_load_balancer=False,
            memory_limit_mib=2048,
            task_image_options=ecsp.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_registry("amazon/amazon-ecs-sample")
            )
            )

## Create API Gateway
        api = gw.RestApi(self, "ecs-s3-test-api",
                  rest_api_name="ECS S3 Test API",
                  description="Test API for distributing traffic to S3 and ECS")
        
        root_method = api.root.add_method("GET")   # GET /
        apis = api.root.add_resource("apis")
        proxy = api.root.add_resource("{proxy+}")

        apis.add_method("GET")
        
        proxy.add_method("GET")
        
    