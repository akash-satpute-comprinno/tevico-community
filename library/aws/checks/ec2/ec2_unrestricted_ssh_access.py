"""
AUTHOR: Akash Satpute
EMAIL: akash.satpute@comprinno.net
DATE: 2026-04-02
"""

import boto3
from tevico.engine.entities.report.check_model import CheckReport, CheckStatus, AwsResource, GeneralResource, ResourceStatus
from tevico.engine.entities.check.check import Check


class ec2_unrestricted_ssh_access(Check):

    def execute(self, connection: boto3.Session) -> CheckReport:
        report = CheckReport(name=__name__)
        report.status = CheckStatus.PASSED
        report.resource_ids_status = []

        try:
            sts_client = connection.client('sts')
            account_id = sts_client.get_caller_identity()['Account']
            region = connection.region_name
            ec2_client = connection.client("ec2", region_name=region)

            # Pagination to get all security groups
            security_groups = []
            next_token = None

            while True:
                response = ec2_client.describe_security_groups(NextToken=next_token) if next_token else ec2_client.describe_security_groups()
                security_groups += response["SecurityGroups"]
                next_token = response.get('NextToken')
                if not next_token:
                    break

            # NOT_APPLICABLE if no security groups found
            if not security_groups:
                report.status = CheckStatus.NOT_APPLICABLE
                report.resource_ids_status.append(
                    ResourceStatus(
                        resource=GeneralResource(name=""),
                        status=CheckStatus.NOT_APPLICABLE,
                        summary="No security groups found in the account."
                    )
                )
                return report

            for sg in security_groups:
                sg_id = sg['GroupId']
                sg_name = sg['GroupName']
                sg_arn = f"arn:aws:ec2:{region}:{account_id}:security-group/{sg_id}"

                unrestricted_ssh = False
                for rule in sg.get('IpPermissions', []):
                    if rule.get('FromPort') == 22 and rule.get('ToPort') == 22:
                        # Check IPv4
                        for ip_range in rule.get('IpRanges', []):
                            if ip_range.get('CidrIp') == '0.0.0.0/0':
                                unrestricted_ssh = True
                        # Check IPv6
                        for ip_range in rule.get('Ipv6Ranges', []):
                            if ip_range.get('CidrIpv6') == '::/0':
                                unrestricted_ssh = True

                if unrestricted_ssh:
                    report.resource_ids_status.append(
                        ResourceStatus(
                            resource=AwsResource(arn=sg_arn),
                            status=CheckStatus.FAILED,
                            summary=f"Security group {sg_name} ({sg_id}) allows unrestricted SSH access."
                        )
                    )
                    report.status = CheckStatus.FAILED
                else:
                    report.resource_ids_status.append(
                        ResourceStatus(
                            resource=AwsResource(arn=sg_arn),
                            status=CheckStatus.PASSED,
                            summary=f"Security group {sg_name} ({sg_id}) does not allow unrestricted SSH."
                        )
                    )

        except Exception as e:
            report.status = CheckStatus.UNKNOWN
            report.resource_ids_status.append(
                ResourceStatus(
                    resource=GeneralResource(name=""),
                    status=CheckStatus.UNKNOWN,
                    summary=f"Error fetching security groups: {str(e)}",
                    exception=str(e)
                )
            )

        return report
