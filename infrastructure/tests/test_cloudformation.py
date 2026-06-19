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


def test_security_stack_receives_vpc_id_from_network_stack() -> None:
    template = load_template("master.yaml")
    security_params = template["Resources"]["SecurityStack"]["Properties"]["Parameters"]
    assert security_params["VpcId"] == {"Fn::GetAtt": ["NetworkStack", "Outputs.VpcId"]}
