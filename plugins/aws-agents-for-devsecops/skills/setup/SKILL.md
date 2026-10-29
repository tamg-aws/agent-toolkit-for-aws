---
name: setup
description: Set up the AWS DevOps Agent and AWS Security Agent connections. Use when the user says "set up", "configure", "connect", or when MCP tools are missing.
---

# Setup

Run these skills in order:

1. Invoke the `setup-devops-agent` skill to configure the DevOps Agent MCP connection.
2. Invoke the `setup-security-agent` skill to configure the Security Agent workspace (agent space, IAM role, S3 bucket).

If the user only needs one agent, run only the relevant skill.

For **Continuum remediation**, invoke `remediating-with-continuum` instead of configuring an unrelated agent connection. Its optional backend uses Python 3.11+, the user's existing AWS profile for signed read-only intake, and a local Docker daemon for isolated application tests. Prepare the application contract described in [the runtime guide](../../runtime/README.md). This does not require an MCP server or changes to global permissions. Preserve any existing DevOps/Security Agent setup.
