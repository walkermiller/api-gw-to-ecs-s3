from aws_cdk import (
    core,
    aws_iam as iam,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_ecs_patterns as ecsp,
    aws_s3 as s3,
    aws_apigateway as apigw
)

class ApiGwToEcsS3Stack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

## Create S3 Bucket. We'll populate it seperately. 
        bucket_name="{}-s3-ecs-apigw-test".format(core.Aws.ACCOUNT_ID)
        bucket = s3.Bucket(self, "s3-ecs-apigw-test",
            bucket_name=bucket_name,
            versioned=True,
            public_read_access=False
            )

## Create ECS  Cluster, Taks and Service
### Create the VPC for the demo
        vpc = ec2.Vpc(self, "MyVpc", max_azs=3)

### Create the ECS Cluster
        cluster = ecs.Cluster(self,
            "ecs-apigw-test-cluster",
            cluster_name="ecs-apigw-test-cluster",
            container_insights=True,
            vpc=vpc)
### Using the Network LoadBalance Fargate patterm, this wills creat the container definition, the task definition, the service and the Network load balancer for it. 
        ecs_deploy = ecsp.NetworkLoadBalancedFargateService(self, 
            "ecs-apigw-test",
            cluster=cluster,
            cpu=512,
            desired_count=1,
            public_load_balancer=False,
            memory_limit_mib=2048,
            task_image_options=ecsp.NetworkLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_registry("amazon/amazon-ecs-sample")
            )
            )


## Create API Gateway resources

### Create the VPC Link to the Network Load Balancer
        vpcLink =apigw.VpcLink(self, 
            "ecs-test-vpc-link",
            targets = [ecs_deploy.load_balancer.load_balancer_arn])
### Create the API
        api = apigw.RestApi(self, "ecs-s3-test-api",
                  rest_api_name="ECS S3 Test API",
                  description="Test API for distributing traffic to S3 and ECS",
                  binary_media_types=["image/png"])
### Create the execution role for the API methods. 
        rest_api_role = iam.Role(
            self,
            "RestAPIRole",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3ReadOnlyAccess")])

### Generic Method Response that can be used with each API method
        method_response = apigw.MethodResponse(status_code="200",
            response_parameters={"method.response.header.Content-Type": True})

### Root URI
        root_integration_response = apigw.IntegrationResponse(
            status_code="200",
            response_templates={"text/html": "$input.path('$')"},
            response_parameters={"method.response.header.Content-Type": "'text/html'"})
        root_integration_options = apigw.IntegrationOptions(
            credentials_role=rest_api_role,
            integration_responses=[root_integration_response],
            request_templates={"application/json": "Action=SendMessage&MessageBody=$input.body"},
            passthrough_behavior=apigw.PassthroughBehavior.NEVER,
            request_parameters={
                "integration.request.header.Content-Type": "'application/x-www-form-urlencoded'"})
        root_resource_s3_integration = apigw.AwsIntegration(
            service="s3",
            integration_http_method="GET",
            subdomain=bucket_name,
            path="index.html",
            options=root_integration_options)

 
        root_method = api.root.add_method("GET",
            root_resource_s3_integration,
            method_responses=[method_response])

### API URI
        api_integration_response = apigw.IntegrationResponse(
            status_code="200",
            response_templates={"text/html": "$input.path('$')"},
            response_parameters={"method.response.header.Content-Type": "'text/html'"})
        api_integration_options = apigw.IntegrationOptions(
            credentials_role=rest_api_role,
            integration_responses=[api_integration_response],
            request_templates={"application/json": "Action=SendMessage&MessageBody=$input.body"},
            passthrough_behavior=apigw.PassthroughBehavior.NEVER,
            request_parameters={
                "integration.request.header.Content-Type": "'application/x-www-form-urlencoded'",
                 "integration.request.path.api": "method.request.path.api"})
        api_integration = apigw.HttpIntegration(
            "http://{}".format(ecs_deploy.load_balancer.load_balancer_dns_name),
            options=api_integration_options,
            http_method="GET",
            proxy=True)
        apis = api.root.add_resource("apis")
        apii = apis.add_resource("{api}")
        # apis = api.root.add_resource("apis")
        apii_get = apii.add_method("GET",
            api_integration,
            method_responses=[method_response],
            request_parameters={
                "method.request.path.api": True,})

## Add Images URI
        image_integration_response = apigw.IntegrationResponse(
            status_code="200",
            content_handling=apigw.ContentHandling.CONVERT_TO_BINARY,
            # response_templates={"text/html": "$input.path('$')"},
            response_parameters={"method.response.header.Content-Type": "'image/png'"})
        image_integration_options = apigw.IntegrationOptions(
            credentials_role=rest_api_role,
            integration_responses=[image_integration_response],
            request_templates={"application/json": "Action=SendMessage&MessageBody=$input.body"},
            passthrough_behavior=apigw.PassthroughBehavior.NEVER,
            request_parameters={
                "integration.request.header.Content-Type": "'application/x-www-form-urlencoded'",
                "integration.request.path.image": "method.request.path.image"})
        images_resource_s3_integration = apigw.AwsIntegration(
            service="s3",
            integration_http_method="GET",
            subdomain=bucket_name,
            path="images/{image}",
            options=image_integration_options)
        images_resource = api.root.add_resource("images")
        image_resource = images_resource.add_resource("{image}")
        images_get = image_resource.add_method("GET",
            images_resource_s3_integration,
            method_responses=[method_response],
            request_parameters={
                "method.request.path.image": True,})

## Fall Through
        folder = api.root.add_resource("{folder}")
        item = folder.add_resource("{item}")
        integration_response = apigw.IntegrationResponse(
            status_code="200",
            response_templates={"text/html": "$input.path('$')"},
            response_parameters={"method.response.header.Content-Type": "'text/html'"})
        s3_proxy_integration_options = apigw.IntegrationOptions(
            credentials_role=rest_api_role,
            integration_responses=[integration_response],
            request_templates={"application/json": "Action=SendMessage&MessageBody=$input.body"},
            passthrough_behavior=apigw.PassthroughBehavior.NEVER,
            request_parameters={
                "integration.request.header.Content-Type": "'application/x-www-form-urlencoded'",
                "integration.request.path.item": "method.request.path.item",
                "integration.request.path.folder": "method.request.path.folder"})
        s3_proxy_resource_s3_integration = apigw.AwsIntegration(
            service="s3",
            integration_http_method="GET",
            subdomain=bucket_name,
            path="{folder}/{item}",
            options=s3_proxy_integration_options)
        item_get = item.add_method("GET",
            s3_proxy_resource_s3_integration,
            method_responses=[method_response],
            request_parameters={
                "method.request.path.item": True,
                "method.request.path.folder": True
            }
            )
  