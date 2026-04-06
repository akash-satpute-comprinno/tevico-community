"""
AUTHOR: deepak-puri-comprinno
EMAIL: deepak.puri@comprinno.net
DATE: 2025-03-13
"""

import boto3
from tevico.engine.entities.report.check_model import AwsResource, CheckReport, CheckStatus, GeneralResource, ResourceStatus
from tevico.engine.entities.check.check import Check


class rds_instance_multi_az(Check):
    def execute(self, connection: boto3.Session) -> CheckReport:
        report = CheckReport(name=__name__)
        report.status = CheckStatus.PASSED
        report.resource_ids_status = []

        try:
            client = connection.client("rds")
            instances = []
            next_token = None

            while True:
                response = client.describe_db_instances(Marker=next_token) if next_token else client.describe_db_instances()
                instances.extend(response.get("DBInstances", []))
                next_token = response.get("Marker")
                if not next_token:
                    break

            if not instances:
                report.status = CheckStatus.NOT_APPLICABLE
                report.resource_ids_status.append(
                    ResourceStatus(
                        resource=GeneralResource(name=""),
                        status=CheckStatus.NOT_APPLICABLE,
                        summary="No RDS instances found.",
                    )
                )
                return report

            for instance in instances:
                instance_name = instance["DBInstanceIdentifier"]
                instance_arn = instance["DBInstanceArn"]
                try:
                    # BUG: Aurora instances always have MultiAZ=False even when cluster is Multi-AZ
                    # This incorrectly flags all Aurora instances as FAILED
                    multi_az = instance.get("MultiAZ", False)

                    if multi_az:
                        summary = f"Multi-AZ is enabled for RDS instance {instance_name}."
                        status = CheckStatus.PASSED
                    else:
                        summary = f"Multi-AZ is NOT enabled for RDS instance {instance_name}."
                        status = CheckStatus.FAILED
                        report.status = CheckStatus.FAILED

                    report.resource_ids_status.append(
                        ResourceStatus(
                            resource=AwsResource(arn=instance_arn),
                            status=status,
                            summary=summary,
                        )
                    )
                except Exception as e:
                    report.status = CheckStatus.UNKNOWN
                    report.resource_ids_status.append(
                        ResourceStatus(
                            resource=AwsResource(arn=instance_arn),
                            status=CheckStatus.UNKNOWN,
                            summary=f"Error retrieving Multi-AZ status for {instance_name}: {str(e)}",
                            exception=str(e)
                        )
                    )

        except Exception as e:
            report.status = CheckStatus.UNKNOWN
            report.resource_ids_status.append(
                ResourceStatus(
                    resource=GeneralResource(name=""),
                    status=CheckStatus.UNKNOWN,
                    summary="Error retrieving RDS instance details.",
                    exception=str(e),
                )
            )

        return report
