# Pass 1 — Infrastructure Inventory

Read-only discovery of resource types. Every recommendation must trace to something found
here. Run with `--region <region>` for each region being assessed.

## Compute

```bash
# EC2 instances (running only — stopped instances still incur Inspector scanning)
aws ec2 describe-instances \
  --filters 'Name=instance-state-name,Values=running,stopped' \
  --query 'Reservations[].Instances[].{Id:InstanceId,State:State.Name,Platform:PlatformDetails}' \
  --region <region>

# SSM-managed status — required for Inspector agent-based scanning and GuardDuty
# Runtime Monitoring on EC2. Instances absent here cannot run either agent.
aws ssm describe-instance-information \
  --query 'InstanceInformationList[].{Id:InstanceId,Ping:PingStatus,Agent:AgentVersion}' \
  --region <region>

# EBS volumes — GuardDuty Malware Protection and Inspector agentless scanning
aws ec2 describe-volumes \
  --query 'Volumes[].{Id:VolumeId,Encrypted:Encrypted,State:State}' \
  --region <region>

# Lambda functions
aws lambda list-functions \
  --query 'Functions[].{Name:FunctionName,Runtime:Runtime}' \
  --region <region>
```

## Containers

```bash
# ECR repositories — Inspector ECR scanning
aws ecr describe-repositories \
  --query 'repositories[].{Name:repositoryName,ScanOnPush:imageScanningConfiguration.scanOnPush}' \
  --region <region>

# ECS clusters
aws ecs list-clusters --region <region>

# ECS launch type per service — Fargate vs EC2 changes the GuardDuty Runtime
# Monitoring path. Fargate requires platform 1.4.0 or LATEST.
aws ecs list-services --cluster <cluster-arn> --region <region>
aws ecs describe-services --cluster <cluster-arn> --services <service> \
  --query 'services[].{Name:serviceName,LaunchType:launchType,Platform:platformVersion}' \
  --region <region>

# EKS clusters
aws eks list-clusters --region <region>

# EKS compute type — Fargate profiles mean Runtime Monitoring is NOT supported for
# those workloads. An empty fargateProfileNames list means EKS on EC2.
aws eks list-fargate-profiles --cluster-name <cluster> --region <region>
aws eks list-nodegroups --cluster-name <cluster> --region <region>

# EKS audit logging — GuardDuty EKS Protection reads these
aws eks describe-cluster --name <cluster> \
  --query 'cluster.logging.clusterLogging' --region <region>
```

## Data

```bash
# S3 buckets — Macie, GuardDuty S3 Protection, S3 Malware Protection.
# s3api list-buckets is global; filter by region if assessing one region.
aws s3api list-buckets --query 'Buckets[].Name'
aws s3api get-bucket-location --bucket <name>

# RDS and Aurora — GuardDuty RDS Protection covers Aurora login activity
aws rds describe-db-clusters \
  --query 'DBClusters[].{Id:DBClusterIdentifier,Engine:Engine}' --region <region>
aws rds describe-db-instances \
  --query 'DBInstances[].{Id:DBInstanceIdentifier,Engine:Engine}' --region <region>
```

## Network and edge

```bash
# CloudFront distributions (global service — no --region)
aws cloudfront list-distributions \
  --query 'DistributionList.Items[].{Id:Id,Domain:DomainName,WebACL:WebACLId}'

# Load balancers — ALBs are WAF-associable, NLBs are not
aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[].{Name:LoadBalancerName,Type:Type,Scheme:Scheme}' \
  --region <region>

# API Gateway
aws apigateway get-rest-apis --query 'items[].{Id:id,Name:name}' --region <region>
aws apigatewayv2 get-apis --query 'Items[].{Id:ApiId,Name:Name,Protocol:ProtocolType}' \
  --region <region>

# VPCs — Security Lake VPC flow log source, Route 53 Resolver DNS Firewall
aws ec2 describe-vpcs --query 'Vpcs[].VpcId' --region <region>
aws ec2 describe-flow-logs \
  --query 'FlowLogs[].{Id:FlowLogId,Resource:ResourceId,Status:FlowLogStatus}' \
  --region <region>
```

## Foundational logging

```bash
# CloudTrail — prerequisite for Security Lake CloudTrail management events, which
# requires a multi-region organization trail capturing read and write management events
aws cloudtrail describe-trails \
  --query 'trailList[].{Name:Name,MultiRegion:IsMultiRegionTrail,Org:IsOrganizationTrail,Home:HomeRegion}'

aws cloudtrail get-event-selectors --trail-name <name> --region <trail-home-region>
```

## Organization context

```bash
# Standalone accounts raise AWSOrganizationsNotInUseException — treat as standalone
aws organizations describe-organization

# Which security services already have a delegated admin registered
aws organizations list-delegated-administrators \
  --query 'DelegatedAdministrators[].{Id:Id,Email:Email}'

# Enabled regions — every service here except IAM Access Analyzer is regional
aws account list-regions \
  --region-opt-status-contains ENABLED ENABLED_BY_DEFAULT \
  --query 'Regions[].RegionName'
```

## Recording the inventory

Produce a table before moving to pass 2. Absent types matter as much as present ones —
they are what keeps the report from recommending services the account cannot use.

| Resource type | Count | Notes |
|---|---|---|
| EC2 instances | | how many SSM-managed |
| EBS volumes | | |
| ECR repositories | | |
| ECS clusters | | Fargate vs EC2 per service |
| EKS clusters | | Fargate profiles present? audit logs on? |
| Lambda functions | | |
| S3 buckets | | which take untrusted uploads |
| RDS / Aurora | | Aurora engines specifically |
| CloudFront distributions | | WebACL attached? |
| ALBs | | internet-facing vs internal |
| API Gateway APIs | | |
| VPCs | | flow logs enabled? |
