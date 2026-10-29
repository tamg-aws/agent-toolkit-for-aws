"""Read-only Continuum inventory with terminal pagination and stability checks."""

import http.client
import re
import time
from urllib.parse import urlencode

from store import VERSION, now, require, strict_json

MAX_RESPONSE = 16 * 1024 * 1024


def service_id(value: str) -> str:
    require(
        isinstance(value, str) and re.fullmatch(r"[a-z0-9]{1,64}", value),
        "Invalid Continuum identifier",
    )
    return value


class SignedReader:
    def __init__(self, profile: str, region: str, account: str, environment: str):
        require(region == "us-east-1", "This adapter currently supports us-east-1 only")
        require(re.fullmatch(r"\d{12}", account), "Invalid AWS account")
        service_id(environment)
        import boto3
        from botocore.config import Config

        self.session = boto3.Session(profile_name=profile, region_name=region)
        identity = self.session.client(
            "sts",
            config=Config(
                retries={"max_attempts": 0}, connect_timeout=10, read_timeout=30
            ),
        ).get_caller_identity()
        require(identity["Account"] == account, "Credential account mismatch")
        self.identity = identity
        self.environment = environment
        self.region = region
        self.host = f"continuum.{region}.api.aws"
        self.connection = None

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def __call__(self, path: str) -> dict:
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest

        base = f"/environments/{self.environment}"
        route = path.split("?")[0]
        allowed = re.fullmatch(
            re.escape(base) + r"(?:/(?:code-scans|code-findings|code-issues)"
            r"(?:/[a-z0-9]{1,64})?)?",
            route,
        )
        require(bool(allowed), "Request outside read-only environment scope")
        attempts = []
        for index in range(3):
            request = AWSRequest(method="GET", url=f"https://{self.host}{path}")
            credentials = self.session.get_credentials().get_frozen_credentials()
            SigV4Auth(credentials, "continuum", self.region).add_auth(request)
            try:
                if self.connection is None:
                    self.connection = http.client.HTTPSConnection(self.host, timeout=60)
                self.connection.request("GET", path, headers=dict(request.headers))
                response = self.connection.getresponse()
                body = response.read(MAX_RESPONSE + 1)
                require(len(body) <= MAX_RESPONSE, "Continuum response exceeds limit")
                attempt = {
                    "raw": body.decode("utf-8"),
                    "http_status": response.status,
                    "request_id": response.getheader("x-amzn-requestid"),
                    "path": path,
                    "captured_at": now(),
                    "attempt": index + 1,
                }
                attempts.append(attempt)
                if response.status not in (429, 500, 502, 503, 504) or index == 2:
                    return dict(
                        attempt,
                        body=strict_json(body) if response.status == 200 else None,
                        transport_attempts=attempts,
                    )
            except (
                TimeoutError,
                ConnectionError,
                http.client.RemoteDisconnected,
                http.client.IncompleteRead,
            ) as error:
                attempts.append(
                    {
                        "path": path,
                        "attempt": index + 1,
                        "captured_at": now(),
                        "transport_error": type(error).__name__,
                        "error": str(error),
                    }
                )
                if index == 2:
                    return {
                        "path": path,
                        "http_status": 0,
                        "body": None,
                        "raw": "",
                        "transport_attempts": attempts,
                        "captured_at": now(),
                    }
            self.close()
            time.sleep(index + 1)
        raise AssertionError("Unreachable retry exhaustion")


def capture(
    store, reader, account: str, region: str, environment: str, scan: str
) -> dict:
    receipts = []
    try:
        return _capture(store, reader, account, region, environment, scan, receipts)
    except (ValueError, OSError, KeyError, TypeError) as error:
        store.append(
            "capture_failed",
            {
                "account": account,
                "region": region,
                "environment_id": environment,
                "scan_id": scan,
                "receipts": receipts,
                "error": str(error),
                "recorded_at": now(),
            },
        )
        raise
    finally:
        if isinstance(reader, SignedReader):
            reader.close()


def _capture(
    store,
    reader,
    account: str,
    region: str,
    environment: str,
    scan: str,
    receipts: list[str],
) -> dict:
    service_id(environment)
    service_id(scan)
    base = f"/environments/{environment}"
    started = now()

    def get(path):
        response = reader(path)
        receipts.append(store.save(response))
        require(
            response.get("path") == path and response.get("http_status") == 200,
            "Read transport did not bind the exact request",
        )
        require(
            strict_json(response["raw"].encode()) == response["body"],
            "Read transport body differs from retained bytes",
        )
        return response["body"]

    def pages(route, id_key):
        token, seen_tokens, records = None, set(), {}
        for _ in range(10000):
            query = {"maxResults": 100}
            if token:
                query["nextToken"] = token
            page = get(base + "/" + route + "?" + urlencode(query))
            require(isinstance(page.get("items"), list), "Missing inventory items")
            for item in page["items"]:
                key = service_id(item.get(id_key))
                require(key not in records, "Duplicate inventory ID across pages")
                records[key] = item
            token = page.get("nextToken")
            if token is None:
                return records
            require(
                isinstance(token, str)
                and 0 < len(token) <= 2048
                and token not in seen_tokens,
                "Invalid/repeated pagination token",
            )
            seen_tokens.add(token)
        raise ValueError("Pagination bound exceeded")

    environment_record = get(base)
    expected_arn = f"arn:aws:continuum:{region}:{account}:environments/{environment}"
    require(
        environment_record.get("environmentId") == environment
        and environment_record.get("environmentArn") == expected_arn,
        "Environment/account identity mismatch",
    )
    scan_record = get(base + "/code-scans/" + scan)
    require(
        scan_record.get("scan", {}).get("scanRunId") == scan
        and scan_record["scan"].get("environmentId", environment) == environment,
        "Scan identity mismatch",
    )
    require(
        scan_record["scan"].get("status") in ("COMPLETED", "SUCCEEDED"),
        "Select a completed scan",
    )
    first = pages("code-findings", "findingId")
    issues_first = pages("code-issues", "issueId")
    for item in first.values():
        service_id(item.get("scanRunId"))
        require(
            item.get("environmentId", environment) == environment,
            "Finding summary environment mismatch",
        )
    selected = {
        key: value for key, value in first.items() if value.get("scanRunId") == scan
    }
    findings = {}
    linked = set()
    for key in sorted(selected):
        finding = get(base + "/code-findings/" + key)
        require(
            finding.get("findingId") == key
            and finding.get("scanRunId") == scan
            and finding.get("environmentId") == environment,
            "Finding identity mismatch",
        )
        findings[key] = finding
        for field in ("createdIssueId", "duplicateOfIssueId"):
            if finding.get(field):
                linked.add(service_id(finding[field]))
    require(
        linked <= issues_first.keys(), "Linked issue missing from terminal inventory"
    )
    issues = {}
    linked.update(
        key
        for key, item in issues_first.items()
        if set(item.get("findingIds", [])) & findings.keys()
    )
    for key in sorted(linked):
        issue = get(base + "/code-issues/" + key)
        require(
            issue.get("issueId") == key
            and issue.get("environmentId", environment) == environment
            and issue.get("issueArn") == expected_arn + "/code-issues/" + key,
            "Issue identity mismatch",
        )
        members = issue.get("findingIds")
        require(
            isinstance(members, list) and len(set(members)) == len(members),
            "Issue membership missing or duplicated",
        )
        if key in linked or set(members) & findings.keys():
            issues[key] = issue
    require(
        first == pages("code-findings", "findingId")
        and issues_first == pages("code-issues", "issueId"),
        "Inventory changed during capture; start a new observation",
    )
    # Detail comparisons catch updates that did not change a listing summary.
    for key, finding in findings.items():
        require(
            finding == get(base + "/code-findings/" + key),
            "Finding changed during capture",
        )
    for key, issue in issues.items():
        require(
            issue == get(base + "/code-issues/" + key), "Issue changed during capture"
        )
    require(
        environment_record == get(base)
        and scan_record == get(base + "/code-scans/" + scan),
        "Environment or scan changed during capture",
    )
    result = {
        "schema_version": VERSION,
        "evidence_class": "live_service_read",
        "account": account,
        "region": region,
        "environment_id": environment,
        "scan_id": scan,
        "started_at": started,
        "completed_at": now(),
        "environment": environment_record,
        "scan": scan_record,
        "findings": findings,
        "issues": issues,
        "environment_finding_count": len(first),
        "selected_finding_count": len(findings),
        "environment_issue_count": len(issues_first),
        "selected_issue_count": len(issues),
        "receipts": receipts,
        "completeness": "terminal_pages_and_stable_second_read",
        "source_binding": "repository_association_not_service_attested_git_revision",
        "limitations": [
            "Two equal reads do not establish a transactional snapshot.",
            "Proof artifact metadata is retained; artifact downloads are not performed.",
            "Issue membership may reference findings outside the selected scan.",
        ],
    }
    store.append("inventory", result)
    return result


def import_export(store, export: dict) -> dict:
    require(isinstance(export, dict), "Import must use the documented export envelope")
    for key in (
        "account",
        "region",
        "environment_id",
        "scan_id",
        "findings",
        "issues",
        "origin",
        "limitations",
    ):
        require(key in export, f"Missing imported field: {key}")
    service_id(export["environment_id"])
    service_id(export["scan_id"])
    findings = export["findings"]
    issues = export["issues"]
    require(
        isinstance(findings, list) and isinstance(issues, list),
        "Import details must be arrays",
    )
    by_id = {}
    for finding in findings:
        key = service_id(finding.get("findingId"))
        require(
            key not in by_id
            and finding.get("scanRunId") == export["scan_id"]
            and finding.get("environmentId") == export["environment_id"],
            "Imported finding duplicate or identity mismatch",
        )
        by_id[key] = finding
    by_issue = {}
    for issue in issues:
        key = service_id(issue.get("issueId"))
        require(
            key not in by_issue
            and issue.get("environmentId", export["environment_id"])
            == export["environment_id"],
            "Imported issue duplicate or identity mismatch",
        )
        by_issue[key] = issue
    result = dict(
        export,
        schema_version=VERSION,
        evidence_class="imported_service_export",
        findings=by_id,
        issues=by_issue,
        selected_finding_count=len(by_id),
        selected_issue_count=len(by_issue),
        imported_at=now(),
        original_export=store.save(export),
        completeness="not_independently_verified",
        source_binding="operator_supplied_not_service_attested",
    )
    store.append("inventory", result)
    return result
