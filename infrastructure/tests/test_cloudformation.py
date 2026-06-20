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


CloudFormationLoader.add_constructor("!Ref", _construct_ref)
CloudFormationLoader.add_constructor("!GetAtt", _construct_getatt)
CloudFormationLoader.add_constructor("!Sub", _construct_sub)
CloudFormationLoader.add_constructor("!Join", _construct_sequence_intrinsic("Fn::Join"))
CloudFormationLoader.add_constructor("!Select", _construct_sequence_intrinsic("Fn::Select"))
CloudFormationLoader.add_constructor("!Split", _construct_sequence_intrinsic("Fn::Split"))
CloudFormationLoader.add_constructor("!Cidr", _construct_sequence_intrinsic("Fn::Cidr"))


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
    assert {"EcrStack", "RdsStack", "S3Stack", "EcsApiStack"} <= set(nested)
    assert nested["EcrStack"]["Properties"]["TemplateURL"] == "ecr.yaml"
    assert nested["RdsStack"]["Properties"]["TemplateURL"] == "rds.yaml"
    assert nested["S3Stack"]["Properties"]["TemplateURL"] == "s3.yaml"
    assert nested["EcsApiStack"]["Properties"]["TemplateURL"] == "ecs-api.yaml"


def test_ecs_api_receives_media_bucket_from_s3_stack() -> None:
    template = load_template("api-master.yaml")
    ecs_params = template["Resources"]["EcsApiStack"]["Properties"]["Parameters"]
    assert ecs_params["MediaBucketName"] == {"Fn::GetAtt": ["S3Stack", "Outputs.MediaBucketName"]}


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
