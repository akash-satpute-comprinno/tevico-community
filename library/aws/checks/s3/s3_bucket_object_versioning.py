"""
AUTHOR: Sheikh Aafaq Rashid
EMAIL: aafaq.rashid@comprinno.net
DATE: 2025-03-28
"""

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from tevico.engine.entities.report.check_model import (
    CheckReport, CheckStatus, AwsResource, GeneralResource, ResourceStatus
)
from tevico.engine.entities.check.check import Check


class s3_bucket_object_versioning(Check):
    def execute(self, connection: boto3.Session) -> CheckReport:
        s3_client = connection.client('s3')
        report = CheckReport(name=__name__)
        report.resource_ids_status = []

        try:
            paginator = s3_client.get_paginator("list_buckets")
            bucket_list = []

            for page in paginator.paginate():
                bucket_list.extend(page.get("Buckets", []))

            if not bucket_list:
                report.status = CheckStatus.NOT_APPLICABLE
                report.resource_ids_status.append(
                    ResourceStatus(
                        resource=GeneralResource(name=""),
                        status=CheckStatus.NOT_APPLICABLE,
                        summary="No S3 buckets found."
                    )
                )
                return report

            # FIX: track if any bucket fails
            has_failure = False

            for bucket in bucket_list:
                bucket_name = bucket["Name"]
                bucket_arn = f"arn:aws:s3:::{bucket_name}"

                try:
                    versioning_response = s3_client.get_bucket_versioning(Bucket=bucket_name)
                    versioning_status = versioning_response.get('Status')

                    if versioning_status == 'Enabled':
                        report.resource_ids_status.append(
                            ResourceStatus(
                                resource=AwsResource(arn=bucket_arn),
                                status=CheckStatus.PASSED,
                                summary=f"S3 bucket {bucket_name} has object versioning enabled."
                            )
                        )
                    elif versioning_status == 'Suspended':
                        has_failure = True
                        report.resource_ids_status.append(
                            ResourceStatus(
                                resource=AwsResource(arn=bucket_arn),
                                status=CheckStatus.FAILED,
                                summary=f"S3 bucket {bucket_name} has object versioning suspended."
                            )
                        )
                    else:
                        has_failure = True
                        report.resource_ids_status.append(
                            ResourceStatus(
                                resource=AwsResource(arn=bucket_arn),
                                status=CheckStatus.FAILED,
                                summary=f"S3 bucket {bucket_name} does not have object versioning enabled."
                            )
                        )

                except (BotoCoreError, ClientError) as e:
                    has_failure = True
                    report.resource_ids_status.append(
                        ResourceStatus(
                            resource=AwsResource(arn=bucket_arn),
                            status=CheckStatus.UNKNOWN,
                            summary=f"Failed to retrieve versioning settings for S3 bucket {bucket_name}.",
                            exception=str(e)
                        )
                    )

            # FIX: set final status based on results
            report.status = CheckStatus.FAILED if has_failure else CheckStatus.PASSED

        except (BotoCoreError, ClientError) as e:
            report.status = CheckStatus.UNKNOWN
            report.resource_ids_status.append(
                ResourceStatus(
                    resource=GeneralResource(name=""),
                    status=CheckStatus.UNKNOWN,
                    summary="Encountered an error while retrieving S3 buckets.",
                    exception=str(e)
                )
            )

        return report
