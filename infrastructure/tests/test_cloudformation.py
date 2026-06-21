from pathlib import Path

import pytest
import yaml

INFRA_DIR = Path(__file__).resolve().parents[1]


class CloudFormationLoader(yaml.SafeLoader):
    pass


def _construct_ref(loader: CloudFormationLoader, node: yaml.Node) -> dict:
    return {"Ref": loader.construct_scalar(node)}


def _construct_getatt(loader: CloudFormationLoader, node: yaml.Node) -> dict:
    if isinstance(node, yaml.ScalarNode):
        resource, attribute = loader.construct_scalar(node).split(".", 1)
        return {"Fn::GetAtt": [resource, attribute]}
    return {"Fn::GetAtt": loader.construct_sequence(node)}


def _construct_sub(loader: CloudFormationLoader, node: yaml.Node) -> dict:
    if isinstance(node, yaml.ScalarNode):
        return {"Fn::Sub": loader.construct_scalar(node)}
    return {"Fn::Sub": loader.construct_sequence(node)}


def _construct_sequence_intrinsic(tag: str):
    def constructor(loader: CloudFormationLoader, node: yaml.Node) -> dict:
        return {tag: loader.construct_sequence(node)}

    return constructor


def _construct_equals(loader: CloudFormationLoader, node: yaml.Node) -> dict:
    return {"Fn::Equals": loader.construct_sequence(node)}


def _construct_not(loader: CloudFormationLoader, node: yaml.Node) -> dict:
    return {"Fn::Not": loader.construct_sequence(node)}


def _construct_and(loader: CloudFormationLoader, node: yaml.Node) -> dict:
    return {"Fn::And": loader.construct_sequence(node)}


def _construct_if(loader: CloudFormationLoader, node: yaml.Node) -> dict:
    return {"Fn::If": loader.construct_sequence(node)}


CloudFormationLoader.add_constructor("!Ref", _construct_ref)
CloudFormationLoader.add_constructor("!GetAtt", _construct_getatt)
CloudFormationLoader.add_constructor("!Sub", _construct_sub)
CloudFormationLoader.add_constructor("!Join", _construct_sequence_intrinsic("Fn::Join"))
CloudFormationLoader.add_constructor("!Select", _construct_sequence_intrinsic("Fn::Select"))
CloudFormationLoader.add_constructor("!Split", _construct_sequence_intrinsic("Fn::Split"))
CloudFormationLoader.add_constructor("!Cidr", _construct_sequence_intrinsic("Fn::Cidr"))
CloudFormationLoader.add_constructor("!Equals", _construct_equals)
CloudFormationLoader.add_constructor("!Not", _construct_not)
CloudFormationLoader.add_constructor("!And", _construct_and)
CloudFormationLoader.add_constructor("!If", _construct_if)


def load_template(name: str) -> dict:
    with (INFRA_DIR / name).open(encoding="utf-8") as handle:
        return yaml.load(handle, Loader=CloudFormationLoader)


def resource_types(template: dict) -> set[str]:
    resources = template.get("Resources", {})
    return {spec["Type"] for spec in resources.values()}


@pytest.mark.parametrize(
    ("filename", "expected_types"),
    [
        (
            "network.yaml",
            {
                "AWS::EC2::VPC",
                "AWS::EC2::Subnet",
                "AWS::EC2::InternetGateway",
                "AWS::EC2::NatGateway",
                "AWS::EC2::RouteTable",
                "AWS::EC2::Route",
            },
        ),
        (
            "security.yaml",
            {
                "AWS::EC2::SecurityGroup",
            },
        ),
        (
            "iam.yaml",
            {
                "AWS::IAM::Role",
            },
        ),
    ],
)
def test_templates_define_required_resource_types(filename: str, expected_types: set[str]) -> None:
    template = load_template(filename)
    types = resource_types(template)
    missing = expected_types - types
    assert not missing, f"{filename} missing resource types: {missing}"


def test_network_template_uses_two_availability_zones() -> None:
    template = load_template("network.yaml")
    subnets = [
        spec for spec in template["Resources"].values() if spec["Type"] == "AWS::EC2::Subnet"
    ]
    assert len(subnets) == 4
    zones = {subnet["Properties"]["AvailabilityZone"]["Ref"] for subnet in subnets}
    assert zones == {"AvailabilityZone1", "AvailabilityZone2"}


def test_network_template_has_public_and_private_subnets() -> None:
    template = load_template("network.yaml")
    subnet_names = [
        name
        for name, spec in template["Resources"].items()
        if spec["Type"] == "AWS::EC2::Subnet"
    ]
    assert any("Public" in name for name in subnet_names)
    assert any("Private" in name for name in subnet_names)


def test_security_groups_do_not_expose_rds_publicly() -> None:
    template = load_template("security.yaml")
    rds_group = template["Resources"]["RdsSecurityGroup"]["Properties"]
    ingress_rules = rds_group.get("SecurityGroupIngress", [])
    for rule in ingress_rules:
        assert "CidrIp" not in rule


def test_master_stack_nests_network_security_and_iam() -> None:
    template = load_template("master.yaml")
    nested = {
        name: spec
        for name, spec in template["Resources"].items()
        if spec["Type"] == "AWS::CloudFormation::Stack"
    }
    assert {"NetworkStack", "SecurityStack", "IamStack"} <= set(nested)
    assert nested["NetworkStack"]["Properties"]["TemplateURL"] == "network.yaml"
    assert nested["SecurityStack"]["Properties"]["TemplateURL"] == "security.yaml"
    assert nested["IamStack"]["Properties"]["TemplateURL"] == "iam.yaml"


def test_master_outputs_match_contract() -> None:
    master_outputs = set(load_template("master.yaml").get("Outputs", {}))
    contract = yaml.safe_load((INFRA_DIR / "outputs.yaml").read_text(encoding="utf-8"))
    required_outputs = set(contract)
    assert required_outputs <= master_outputs


def test_master_exports_values_for_downstream_stacks() -> None:
    outputs = load_template("master.yaml")["Outputs"]
    for key in ("VpcId", "PrivateSubnetIds", "EcsApiTaskRoleArn", "RdsSecurityGroupId"):
        assert "Export" in outputs[key]


def test_api_master_nests_ecr_rds_and_ecs_api() -> None:
    template = load_template("api-master.yaml")
    nested = {
        name: spec
        for name, spec in template["Resources"].items()
        if spec["Type"] == "AWS::CloudFormation::Stack"
    }
    assert {"EcrStack", "RdsStack", "S3Stack", "ProcessingStack", "NotificationsStack", "EcsApiStack", "EcsWorkerStack"} <= set(
        nested
    )
    assert nested["ProcessingStack"]["Properties"]["TemplateURL"] == "processing.yaml"
    assert nested["NotificationsStack"]["Properties"]["TemplateURL"] == "notifications.yaml"
    assert nested["EcsWorkerStack"]["Properties"]["TemplateURL"] == "ecs-worker.yaml"
    assert nested["EcrStack"]["Properties"]["TemplateURL"] == "ecr.yaml"
    assert nested["RdsStack"]["Properties"]["TemplateURL"] == "rds.yaml"
    assert nested["S3Stack"]["Properties"]["TemplateURL"] == "s3.yaml"
    assert nested["EcsApiStack"]["Properties"]["TemplateURL"] == "ecs-api.yaml"


def test_processing_stack_routes_s3_events_to_sqs() -> None:
    template = load_template("processing.yaml")
    types = resource_types(template)
    assert "AWS::SQS::Queue" in types
    assert "AWS::Events::Rule" in types
    assert "AWS::IAM::Policy" in types
    rule = template["Resources"]["UploadProcessingRule"]["Properties"]
    assert rule["EventPattern"]["detail-type"] == ["Object Created"]


def test_ecs_worker_template_defines_worker_service() -> None:
    template = load_template("ecs-worker.yaml")
    types = resource_types(template)
    assert {"AWS::ECS::TaskDefinition", "AWS::ECS::Service", "AWS::Logs::LogGroup"} <= types


def test_ecs_worker_receives_processing_queue_url() -> None:
    template = load_template("api-master.yaml")
    worker_params = template["Resources"]["EcsWorkerStack"]["Properties"]["Parameters"]
    assert worker_params["ProcessingQueueUrl"] == {
        "Fn::GetAtt": ["ProcessingStack", "Outputs.ProcessingQueueUrl"]
    }
    assert worker_params["ProcessingNotificationTopicArn"] == {
        "Fn::GetAtt": ["NotificationsStack", "Outputs.ProcessingNotificationTopicArn"]
    }


def test_notifications_stack_defines_sns_topic_and_worker_publish_policy() -> None:
    template = load_template("notifications.yaml")
    types = resource_types(template)
    assert "AWS::SNS::Topic" in types
    assert "AWS::IAM::Policy" in types
    policy = template["Resources"]["WorkerSnsPublishPolicy"]["Properties"]["PolicyDocument"]
    actions = policy["Statement"][0]["Action"]
    assert "sns:Publish" in actions


def test_notifications_stack_creates_email_subscription_when_email_provided() -> None:
    template = load_template("notifications.yaml")
    subscription = template["Resources"]["ProcessingNotificationEmailSubscription"]
    assert subscription["Type"] == "AWS::SNS::Subscription"
    assert subscription["Properties"]["Protocol"] == "email"
    assert "Condition" in subscription


def test_ecs_worker_receives_sns_topic_arn_env_var() -> None:
    template = load_template("ecs-worker.yaml")
    container = template["Resources"]["WorkerTaskDefinition"]["Properties"][
        "ContainerDefinitions"
    ][0]
    env_names = {entry["Name"] for entry in container["Environment"]}
    assert "SNS_PROCESSING_TOPIC_ARN" in env_names


def test_ecs_worker_uses_groq_secret_and_model_env() -> None:
    template = load_template("ecs-worker.yaml")
    types = resource_types(template)
    assert "AWS::SecretsManager::Secret" in types
    container = template["Resources"]["WorkerTaskDefinition"]["Properties"][
        "ContainerDefinitions"
    ][0]
    env_names = {entry["Name"] for entry in container["Environment"]}
    assert {"GROQ_MODEL", "AI_MOCK_MODE"} <= env_names
    secret_names = {entry["Name"] for entry in container["Secrets"]}
    assert "GROQ_API_KEY" in secret_names
    policy = template["Resources"]["WorkerExecutionSecretsPolicy"]["Properties"]["PolicyDocument"]
    resources = policy["Statement"][0]["Resource"]
    assert any("GroqApiKeySecret" in str(resource) for resource in resources)


def test_s3_bucket_enables_eventbridge_notifications() -> None:
    template = load_template("s3.yaml")
    bucket = template["Resources"]["MediaBucket"]["Properties"]
    assert bucket["NotificationConfiguration"]["EventBridgeConfiguration"]["EventBridgeEnabled"] is True


def test_ecr_template_defines_worker_repository() -> None:
    template = load_template("ecr.yaml")
    assert "AWS::ECR::Repository" in resource_types(template)
    repositories = [
        name
        for name, spec in template["Resources"].items()
        if spec["Type"] == "AWS::ECR::Repository"
    ]
    assert any("Worker" in name for name in repositories)


def test_ecs_api_receives_media_bucket_from_s3_stack() -> None:
    template = load_template("api-master.yaml")
    ecs_params = template["Resources"]["EcsApiStack"]["Properties"]["Parameters"]
    assert ecs_params["MediaBucketName"] == {"Fn::GetAtt": ["S3Stack", "Outputs.MediaBucketName"]}
    assert ecs_params["MediaBucketArn"] == {"Fn::GetAtt": ["S3Stack", "Outputs.MediaBucketArn"]}


def test_cloudfront_template_defines_distribution_oac_and_bucket_policy() -> None:
    template = load_template("cloudfront.yaml")
    types = resource_types(template)
    assert {
        "AWS::CloudFront::Distribution",
        "AWS::CloudFront::OriginAccessControl",
        "AWS::S3::BucketPolicy",
    } <= types
    distribution = template["Resources"]["CloudFrontDistribution"]["Properties"]["DistributionConfig"]
    assert distribution["DefaultCacheBehavior"]["ViewerProtocolPolicy"] == "redirect-to-https"
    assert distribution["DefaultCacheBehavior"]["CachePolicyId"] == "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
    cache_behaviors = distribution["CacheBehaviors"]
    path_patterns = {behavior["PathPattern"] for behavior in cache_behaviors}
    assert path_patterns == {"thumbnails/*", "static/*"}


def test_cloudfront_bucket_policy_allows_only_processed_prefixes() -> None:
    template = load_template("cloudfront.yaml")
    policy = template["Resources"]["MediaBucketCloudFrontPolicy"]["Properties"]["PolicyDocument"]
    resources = policy["Statement"][0]["Resource"]
    resource_text = str(resources)
    assert "/thumbnails/*" in resource_text
    assert "/static/*" in resource_text
    assert "/uploads/*" not in resource_text


def test_ecs_api_nests_cloudfront_stack_and_passes_cdn_url_to_task() -> None:
    template = load_template("ecs-api.yaml")
    nested = template["Resources"]["CloudFrontStack"]
    assert nested["Type"] == "AWS::CloudFormation::Stack"
    assert nested["Properties"]["TemplateURL"] == "cloudfront.yaml"
    task_def = template["Resources"]["ApiTaskDefinition"]
    depends_on = task_def.get("DependsOn", [])
    if isinstance(depends_on, str):
        depends_on = [depends_on]
    assert "CloudFrontStack" in depends_on
    env = {
        entry["Name"]: entry["Value"]
        for entry in task_def["Properties"]["ContainerDefinitions"][0]["Environment"]
    }
    assert env["CLOUDFRONT_MEDIA_BASE_URL"] == {
        "Fn::GetAtt": ["CloudFrontStack", "Outputs.CloudFrontMediaBaseUrl"]
    }


def test_s3_bucket_blocks_public_access() -> None:
    template = load_template("s3.yaml")
    bucket = template["Resources"]["MediaBucket"]["Properties"]
    public_access = bucket["PublicAccessBlockConfiguration"]
    assert public_access["BlockPublicAcls"] is True
    assert public_access["RestrictPublicBuckets"] is True
    assert bucket["BucketEncryption"]["ServerSideEncryptionConfiguration"][0][
        "ServerSideEncryptionByDefault"
    ]["SSEAlgorithm"] == "AES256"


def test_s3_template_grants_api_put_object_permission() -> None:
    template = load_template("s3.yaml")
    policy = template["Resources"]["ApiMediaUploadPolicy"]["Properties"]["PolicyDocument"]
    actions = policy["Statement"][0]["Action"]
    assert "s3:PutObject" in actions


def test_api_master_outputs_match_contract() -> None:
    api_outputs = set(load_template("api-master.yaml").get("Outputs", {}))
    contract = yaml.safe_load((INFRA_DIR / "api-outputs.yaml").read_text(encoding="utf-8"))
    required_outputs = set(contract)
    assert required_outputs <= api_outputs


def test_ecs_api_template_defines_alb_ecs_and_logs() -> None:
    template = load_template("ecs-api.yaml")
    types = resource_types(template)
    expected = {
        "AWS::ECS::Cluster",
        "AWS::ECS::TaskDefinition",
        "AWS::ECS::Service",
        "AWS::ElasticLoadBalancingV2::LoadBalancer",
        "AWS::ElasticLoadBalancingV2::TargetGroup",
        "AWS::ElasticLoadBalancingV2::Listener",
        "AWS::Logs::LogGroup",
    }
    missing = expected - types
    assert not missing, f"ecs-api.yaml missing resource types: {missing}"


def test_ecs_api_health_check_uses_health_endpoint() -> None:
    template = load_template("ecs-api.yaml")
    target_group = template["Resources"]["ApiTargetGroup"]["Properties"]
    assert target_group["HealthCheckPath"] == "/health"
    assert target_group["Matcher"]["HttpCode"] == "200"


def test_rds_is_not_publicly_accessible() -> None:
    template = load_template("rds.yaml")
    db = template["Resources"]["DatabaseInstance"]["Properties"]
    assert db["PubliclyAccessible"] is False


def test_ecr_template_defines_repository() -> None:
    template = load_template("ecr.yaml")
    assert "AWS::ECR::Repository" in resource_types(template)


def test_security_stack_receives_vpc_id_from_network_stack() -> None:
    template = load_template("master.yaml")
    security_params = template["Resources"]["SecurityStack"]["Properties"]["Parameters"]
    assert security_params["VpcId"] == {"Fn::GetAtt": ["NetworkStack", "Outputs.VpcId"]}


def test_monitoring_template_defines_log_group_and_alarms() -> None:
    template = load_template("monitoring.yaml")
    types = resource_types(template)
    assert "AWS::Logs::LogGroup" in types
    assert "AWS::CloudWatch::Alarm" in types
    log_group = template["Resources"]["EventsLogGroup"]["Properties"]
    assert log_group["LogGroupName"] == "/aws/events/media-platform"
    alarm_names = {
        name
        for name, spec in template["Resources"].items()
        if spec["Type"] == "AWS::CloudWatch::Alarm"
    }
    assert {
        "SqsBacklogAlarm",
        "SqsOldestMessageAlarm",
        "ApiTarget5xxAlarm",
        "RdsCpuAlarm",
        "RdsConnectionsAlarm",
    } <= alarm_names


def test_monitoring_sqs_alarm_uses_queue_name_dimension() -> None:
    template = load_template("monitoring.yaml")
    alarm = template["Resources"]["SqsBacklogAlarm"]["Properties"]
    assert alarm["Namespace"] == "AWS/SQS"
    assert alarm["MetricName"] == "ApproximateNumberOfMessagesVisible"
    dimensions = {entry["Name"]: entry["Value"] for entry in alarm["Dimensions"]}
    assert dimensions["QueueName"] == {"Ref": "ProcessingQueueName"}


def test_cloudtrail_template_defines_audit_bucket_and_trail() -> None:
    template = load_template("cloudtrail.yaml")
    types = resource_types(template)
    assert {
        "AWS::S3::Bucket",
        "AWS::S3::BucketPolicy",
        "AWS::CloudTrail::Trail",
    } <= types
    bucket = template["Resources"]["AuditBucket"]["Properties"]
    public_access = bucket["PublicAccessBlockConfiguration"]
    assert public_access["BlockPublicAcls"] is True
    assert public_access["RestrictPublicBuckets"] is True
    trail = template["Resources"]["AuditTrail"]["Properties"]
    assert trail["IsLogging"] is True
    assert trail["EnableLogFileValidation"] is True


def test_master_stack_nests_cloudtrail() -> None:
    template = load_template("master.yaml")
    nested = {
        name: spec
        for name, spec in template["Resources"].items()
        if spec["Type"] == "AWS::CloudFormation::Stack"
    }
    assert "CloudTrailStack" in nested
    assert nested["CloudTrailStack"]["Properties"]["TemplateURL"] == "cloudtrail.yaml"


def test_budget_template_defines_monthly_cost_budget() -> None:
    template = load_template("budget.yaml")
    assert "AWS::Budgets::Budget" in resource_types(template)
    budget = template["Resources"]["MonthlyCostBudget"]["Properties"]["Budget"]
    assert budget["BudgetType"] == "COST"
    assert budget["TimeUnit"] == "MONTHLY"


def test_master_stack_nests_budget() -> None:
    template = load_template("master.yaml")
    nested = {
        name: spec
        for name, spec in template["Resources"].items()
        if spec["Type"] == "AWS::CloudFormation::Stack"
    }
    assert "BudgetStack" in nested
    assert nested["BudgetStack"]["Properties"]["TemplateURL"] == "budget.yaml"


def test_api_master_nests_monitoring_stack() -> None:
    template = load_template("api-master.yaml")
    nested = {
        name: spec
        for name, spec in template["Resources"].items()
        if spec["Type"] == "AWS::CloudFormation::Stack"
    }
    assert "MonitoringStack" in nested
    monitoring = nested["MonitoringStack"]["Properties"]
    assert monitoring["TemplateURL"] == "monitoring.yaml"
    params = monitoring["Parameters"]
    assert params["ProcessingQueueName"] == {
        "Fn::GetAtt": ["ProcessingStack", "Outputs.ProcessingQueueName"]
    }
    assert params["ApiLoadBalancerFullName"] == {
        "Fn::GetAtt": ["EcsApiStack", "Outputs.ApiLoadBalancerFullName"]
    }


def test_ecs_log_groups_use_standard_paths() -> None:
    api_template = load_template("ecs-api.yaml")
    worker_template = load_template("ecs-worker.yaml")
    assert api_template["Resources"]["ApiLogGroup"]["Properties"]["LogGroupName"] == "/ecs/api"
    assert worker_template["Resources"]["WorkerLogGroup"]["Properties"]["LogGroupName"] == "/ecs/worker"


def test_iam_task_roles_scope_log_permissions() -> None:
    template = load_template("iam.yaml")
    api_logs = template["Resources"]["EcsApiTaskRole"]["Properties"]["Policies"][0]["PolicyDocument"]
    worker_logs = template["Resources"]["EcsWorkerTaskRole"]["Properties"]["Policies"][0][
        "PolicyDocument"
    ]
    api_resource = api_logs["Statement"][0]["Resource"]
    worker_resource = worker_logs["Statement"][0]["Resource"]
    assert "/ecs/api" in str(api_resource)
    assert "/ecs/worker" in str(worker_resource)
    assert api_resource != "*"
    assert worker_resource != "*"


def test_master_outputs_include_cloudtrail_contract() -> None:
    master_outputs = set(load_template("master.yaml").get("Outputs", {}))
    contract = yaml.safe_load((INFRA_DIR / "outputs.yaml").read_text(encoding="utf-8"))
    required_outputs = set(contract)
    assert required_outputs <= master_outputs
