# IAM Permissions

Every permission in this skill is read-only. No pass requires a write action, and the
skill must not perform one.

## Pass 1 — Inventory

| Domain | Actions |
|---|---|
| Compute | `ec2:DescribeInstances`, `ec2:DescribeVolumes`, `ssm:DescribeInstanceInformation`, `lambda:ListFunctions` |
| Containers | `ecr:DescribeRepositories`, `ecs:ListClusters`, `ecs:ListServices`, `ecs:DescribeServices`, `eks:ListClusters`, `eks:DescribeCluster`, `eks:ListFargateProfiles`, `eks:ListNodegroups` |
| Data | `s3:ListAllMyBuckets`, `s3:GetBucketLocation`, `rds:DescribeDBClusters`, `rds:DescribeDBInstances` |
| Network | `cloudfront:ListDistributions`, `elasticloadbalancing:DescribeLoadBalancers`, `apigateway:GET`, `ec2:DescribeVpcs`, `ec2:DescribeFlowLogs` |
| Logging | `cloudtrail:DescribeTrails`, `cloudtrail:GetEventSelectors` |
| Org | `organizations:DescribeOrganization`, `organizations:ListDelegatedAdministrators`, `account:ListRegions` |

## Pass 2 — Enablement checks

| Service | Actions |
|---|---|
| GuardDuty | `guardduty:ListDetectors`, `guardduty:GetDetector`, `guardduty:ListCoverage`, `guardduty:ListOrganizationAdminAccounts`, `guardduty:DescribeOrganizationConfiguration`, `guardduty:ListMembers` |
| Security Hub | `securityhub:DescribeHub`, `securityhub:GetEnabledStandards`, `securityhub:ListFindingAggregators`, `securityhub:GetFindingAggregator`, `securityhub:ListConfigurationPolicies`, `securityhub:ListOrganizationAdminAccounts`, `securityhub:DescribeOrganizationConfiguration` |
| Inspector | `inspector2:BatchGetAccountStatus`, `inspector2:ListCoverage`, `inspector2:GetConfiguration`, `inspector2:GetEc2DeepInspectionConfiguration`, `inspector2:ListDelegatedAdminAccounts`, `inspector2:DescribeOrganizationConfiguration`, `inspector2:ListMembers` |
| Macie | `macie2:GetMacieSession`, `macie2:GetAutomatedDiscoveryConfiguration`, `macie2:GetClassificationExportConfiguration`, `macie2:ListOrganizationAdminAccounts`, `macie2:DescribeOrganizationConfiguration` |
| Detective | `detective:ListGraphs`, `detective:ListOrganizationAdminAccounts`, `detective:DescribeOrganizationConfiguration`, `detective:ListMembers` |
| Security Lake | `securitylake:ListDataLakes`, `securitylake:GetDataLakeSources`, `securitylake:ListLogSources`, `securitylake:GetDataLakeOrganizationConfiguration`, `securitylake:GetDataLakeExceptionSubscription` |
| Access Analyzer | `accessanalyzer:ListAnalyzers`, `accessanalyzer:ListFindings` |
| Config | `config:DescribeConfigurationRecorders`, `config:DescribeConfigurationRecorderStatus`, `config:DescribeDeliveryChannels`, `config:DescribeConfigurationAggregators` |

## Diagnosing gaps

`AccessDenied` and "not enabled" are different answers, and several of these APIs return
the same error for both. Distinguish them before reporting:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <caller-arn> \
  --action-names macie2:GetMacieSession \
  --query 'EvaluationResults[].EvalDecision'
```

If the decision is `allowed` and the call still fails, the service is not enabled. If the
decision is a denial, report the check as unknown.

## Managed policies

`SecurityAudit` and `ViewOnlyAccess` cover most of the above. Neither is complete for
this skill — `SecurityAudit` omits some newer `inspector2` and `securitylake` read
actions. Verify with `simulate-principal-policy` rather than assuming coverage.

The service-specific admin policies (`AWSSecurityHubFullAccess`,
`AmazonMacieFullAccess`, `AmazonSecurityLakeAdministrator`,
`AmazonDetectiveInvestigatorAccess`) grant far more than this skill needs. They are the
right starting point for a user who accepts a recommendation and moves to enablement, but
not for running the assessment.

## Organization scope

Member accounts cannot read `describe-organization-configuration` for these services. Run
pass 2's org checks from the delegated administrator account, or the management account to
identify who the delegated admins are. From a member account, report the scope limitation
explicitly rather than presenting single-account results as organization-wide.
