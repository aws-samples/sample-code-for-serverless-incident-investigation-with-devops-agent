"""Validate that all resource names comply with production-realistic naming policy.

Scans the CloudFormation template for prohibited words in resource names.
"""

import json
import re
import sys
from pathlib import Path

import yaml

PROHIBITED_WORDS = {"test", "demo", "beta", "sample", "example"}


def check_name(name: str, resource_path: str) -> list[str]:
    """Check a single name for prohibited words."""
    violations = []
    for word in PROHIBITED_WORDS:
        if re.search(rf'\b{word}\b', name, re.IGNORECASE):
            violations.append(f"  VIOLATION: '{name}' in {resource_path} contains prohibited word '{word}'")
    return violations


def validate_template(template_path: str) -> list[str]:
    """Scan a CloudFormation template for naming violations."""
    # Use a custom loader that handles CloudFormation intrinsic functions
    class CFNLoader(yaml.SafeLoader):
        pass

    for tag in ["!Sub", "!Ref", "!GetAtt", "!Select", "!Split", "!Join", "!If", "!Equals", "!Not", "!And", "!Or"]:
        CFNLoader.add_constructor(tag, lambda loader, node: loader.construct_scalar(node) if isinstance(node, yaml.ScalarNode) else loader.construct_sequence(node))

    with open(template_path) as f:
        # CFNLoader subclasses yaml.SafeLoader (it only adds constructors for
        # CloudFormation intrinsic tags such as !Sub/!Ref), so this load is safe
        # and cannot execute arbitrary objects. bandit B506 flags any yaml.load
        # call regardless of the loader, so it is suppressed here with justification.
        template = yaml.load(f, Loader=CFNLoader)  # nosec B506

    violations = []
    resources = template.get("Resources", {})

    for logical_id, resource in resources.items():
        props = resource.get("Properties", {})

        # Check common name fields
        for field in ["Name", "TableName", "ClusterName", "ServiceName",
                      "RepositoryName", "LogGroupName", "TopicName",
                      "AlarmName", "AlarmDescription", "GroupName",
                      "GroupDescription", "RoleName", "Family"]:
            value = props.get(field, "")
            if isinstance(value, str):
                violations.extend(check_name(value, f"{logical_id}.{field}"))

    return violations


def main():
    template_path = Path(__file__).parent.parent / "infra" / "template.yaml"
    if not template_path.exists():
        print(f"ERROR: Template not found at {template_path}")
        sys.exit(1)

    violations = validate_template(str(template_path))

    if violations:
        print("NAMING VALIDATION FAILED:")
        for v in violations:
            print(v)
        sys.exit(1)
    else:
        print("NAMING VALIDATION PASSED: All resource names are production-realistic.")


if __name__ == "__main__":
    main()
