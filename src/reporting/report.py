import boto3
import datetime
import yaml
import structlog
import json


class ReportingClient:
    def __init__(self, config='config.yml'):
        self.session = boto3.session.Session()
        self.config_file = config
        self.logger = structlog.get_logger()
        self.config = None

    def handle(self):
        self._load_conf(self.config_file)
        for report in self.config['reports']:
            self.logger.info("handling", customer=report['customer'])
            report_config = ReportingConfig(conf=report)
            report_config.run(session=self.session)

    def _load_conf(self, file):
        self.config = yaml.load(open(file), Loader=yaml.SafeLoader)


class ReportingConfig:
    def __init__(self, conf):
        self.logger = structlog.get_logger()
        self.customer = conf['customer']
        self.bucket = conf['bucket']
        self.role = conf['role']
        self.ssm_filter = conf['ssm_filter']

    def run(self, session):
        sts_client = session.client('sts')
        creds = sts_client.assume_role(
            RoleArn=self.role,
            RoleSessionName="AutomatedPatchingReport"
        )
        payload = self._report(creds=creds)
        self._upload(creds=creds, payload=payload)

    def _get_client(self, client_type, creds):
        return boto3.client(
            client_type,
            aws_access_key_id=creds['Credentials']['AccessKeyId'],
            aws_secret_access_key=creds['Credentials']['SecretAccessKey'],
            aws_session_token=creds['Credentials']['SessionToken'],
        )

    def _report(self, creds):
        ssm = self._get_client(client_type='ssm', creds=creds)
        summary = []
        result = []
        filter_value = self.ssm_filter[0]['Values'][0]
        filter_ssm_res = [{'Key': self.ssm_filter[0]['Key'], 'Values': ['{}'.format(filter_value)], 'Type': self.ssm_filter[0]['Type'][0]}]
        response_ssm_res = ssm.list_resource_compliance_summaries(
            Filters=filter_ssm_res
        )
        for item in response_ssm_res['ResourceComplianceSummaryItems']:
            instance = item['ResourceId']
            #status = item['Status']
            inst_summary = {"InstanceId":instance,"Status": item['Status']}
            summary.append(inst_summary)
            response_ssm_patches_summ = ssm.describe_instance_patches(InstanceId=instance)
            for patch in response_ssm_patches_summ['Patches']:
                patch['InstanceId'] = instance
                patch['InstalledTime'] = str(patch['InstalledTime'])
                result.append(patch)
        return result,summary

    def _upload(self, creds, payload):
        s3 = self._get_client(client_type='s3', creds=creds)
        s3.put_object(
            ACL='bucket-owner-full-control',
            Bucket=self.bucket,
            Body=json.dumps(payload[0]),
            Key=f"{self.customer}/detail-{datetime.datetime.utcnow().strftime('%Y-%m-%d-%H-%M-%S-%p')}.json"
        )
        s3.put_object(
            ACL='bucket-owner-full-control',
            Bucket=self.bucket,
            Body=json.dumps(payload[1]),
            Key=f"{self.customer}/summary-{datetime.datetime.utcnow().strftime('%Y-%m-%d-%H-%M-%S-%p')}.json"
        )
