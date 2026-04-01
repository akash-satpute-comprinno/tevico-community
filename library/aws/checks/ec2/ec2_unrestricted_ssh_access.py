import boto3
from tevico.engine.entities.report.check_model import CheckReport, CheckStatus, AwsResource, ResourceStatus
from tevico.engine.entities.check.check import Check

class ec2_ssh_check(Check):  # BUG: class name doesn't match filename
    def execute(self, connection: boto3.Session) -> CheckReport:
        report = CheckReport(name=__name__)
        report.resource_ids_status = []
        
        ec2_client = connection.client('ec2')
        
        # BUG: No pagination — will miss security groups if >1000
        response = ec2_client.describe_security_groups()
        security_groups = response['SecurityGroups']
        
        # BUG: No NOT_APPLICABLE check for empty results
        
        for sg in security_groups:
            sg_id = sg['GroupId']
            sg_name = sg['GroupName']
            sg_arn = f"arn:aws:ec2:::security-group/{sg_id}"
            
            unrestricted_ssh = False
            for rule in sg.get('IpPermissions', []):
                if rule.get('FromPort') == 22 and rule.get('ToPort') == 22:
                    for ip_range in rule.get('IpRanges', []):
                        if ip_range.get('CidrIp') == '0.0.0.0/0':
                            unrestricted_ssh = True
                    # BUG: Missing check for IPv6 (::/0)
            
            if unrestricted_ssh:
                report.resource_ids_status.append(
                    ResourceStatus(
                        resource=AwsResource(arn=sg_arn),
                        status=CheckStatus.FAILED,
                        summary=f"Security group {sg_name} ({sg_id}) allows unrestricted SSH access."
                    )
                )
            else:
                report.resource_ids_status.append(
                    ResourceStatus(
                        resource=AwsResource(arn=sg_arn),
                        status=CheckStatus.PASSED,
                        summary=f"Security group {sg_name} ({sg_id}) does not allow unrestricted SSH."
                    )
                )
        
        # BUG: Bare except — swallows all errors silently
        try:
            pass
        except:
            report.status = CheckStatus.UNKNOWN
        
        return report
