# iac-explain

A command-line tool that reads a Terraform file and tells you — in plain English — what infrastructure it provisions, roughly what it costs, and what security risks it carries.

```
$ iac-explain tests/fixtures/insecure_public_bucket.tf
```

```
╭─────────────────────────── Infrastructure Summary ───────────────────────────╮
│   This infrastructure sets up a publicly accessible storage bucket for       │
│ website files, a firewall rule that allows remote login from anywhere on the │
│ internet, and an access control role with unlimited permissions to all cloud │
│ services. The configuration explicitly disables security protections and     │
│ includes comments warning that it is unsafe for production use. All three    │
│ components have critical security flaws: the storage bucket is open to the   │
│ world without encryption, the firewall allows anyone to attempt SSH login,   │
│ and the role grants full administrative access to any server that uses it.   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭───────────────────────────────── Resources ──────────────────────────────────╮
│   Type                                Name            Purpose                │
│  ──────────────────────────────────────────────────────────────────────────  │
│   aws_s3_bucket                       public_assets   Stores static          │
│                                                       website files like     │
│                                                       images, stylesheets,   │
│                                                       and HTML that anyone   │
│                                                       can download.          │
│   aws_s3_bucket_public_access_block   public_assets   Explicitly allows      │
│                                                       public access to the   │
│                                                       storage bucket by      │
│                                                       disabling all safety   │
│                                                       checks.                │
│   aws_security_group                  open_ssh        Defines firewall       │
│                                                       rules allowing         │
│                                                       remote SSH login       │
│                                                       from any internet      │
│                                                       address.               │
│   aws_iam_role                        admin_role      Creates an identity    │
│                                                       that servers can       │
│                                                       assume to access       │
│                                                       cloud resources.       │
│   aws_iam_role_policy                 admin_policy    Grants the role        │
│                                                       unlimited              │
│                                                       permissions to         │
│                                                       perform any action     │
│                                                       on any cloud           │
│                                                       resource.              │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─────────────────────────────── Cost Estimate ────────────────────────────────╮
│   Monthly estimate   $0.50 – $5.00                                           │
│   Confidence         ▸ LOW                                                   │
│   Caveats            Pricing assumes us-east-1 region                        │
│                      S3 storage cost depends on total data stored            │
│                      Data transfer out from S3 to internet users is not      │
│                      included and can be significant for popular websites    │
│                      IAM roles and security groups have no direct cost       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭──────────────── Security Findings  Overall risk: ✖✖ CRITICAL ────────────────╮
│ ✖✖ CRITICAL  aws_s3_bucket.public_assets                                     │
│ Issue S3 bucket has ACL set to 'public-read', making all contents accessible │
│       to anyone on the internet without authentication.                      │
│ Fix   Remove the 'acl = "public-read"' line. If public access is truly       │
│       required, use a bucket policy with explicit conditions rather than a   │
│       blanket public ACL.                                                    │
│ ──────────────────────────────────────────────────────────────────────────── │
│ ✖✖ CRITICAL  aws_s3_bucket_public_access_block.public_assets                 │
│ Issue All public access block settings are disabled (set to false),          │
│       explicitly removing AWS safety guardrails.                             │
│ Fix   Set block_public_acls, block_public_policy, ignore_public_acls, and   │
│       restrict_public_buckets all to true.                                   │
│ ──────────────────────────────────────────────────────────────────────────── │
│ ✖✖ CRITICAL  aws_security_group.open_ssh                                     │
│ Issue Security group allows SSH (port 22) from 0.0.0.0/0, exposing servers  │
│       to brute-force attacks from any internet address.                      │
│ Fix   Change cidr_blocks to a specific office IP range, or use AWS Systems   │
│       Manager Session Manager instead of direct SSH.                         │
│ ──────────────────────────────────────────────────────────────────────────── │
│ ✖✖ CRITICAL  aws_iam_role_policy.admin_policy                                │
│ Issue IAM policy grants Action '*' and Resource '*', giving unrestricted     │
│       access to all AWS services and resources.                              │
│ Fix   Replace the wildcard policy with specific actions and resources needed │
│       for the role's actual purpose.                                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

---

## Why

Getting reliable, schema-conformant output from an LLM over messy real-world input is the core discipline of production AI engineering. This tool demonstrates the key habit:

**Parse deterministically. Reason with the LLM.**

`python-hcl2` extracts resource types, names, and config as structured data — no LLM involved. Claude is then given both the raw HCL and the structured list and asked only to do what it's uniquely good at: explain purpose in plain English, reason about security posture, and ballpark cost. The output is forced through a Pydantic schema via Anthropic's tool-use API, so the structure is guaranteed — not hoped for.

---

## Install

Requires Python 3.12+ and an [Anthropic API key](https://console.anthropic.com).

```bash
git clone https://github.com/youruser/iac-explainer
cd iac-explainer

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -e ".[dev]"

cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

---

## Usage

```bash
# Pretty terminal output (default)
iac-explain path/to/main.tf

# JSON output — pipe into jq or save to file
iac-explain path/to/main.tf --format json

# Run against the included test fixtures
iac-explain tests/fixtures/insecure_public_bucket.tf
iac-explain tests/fixtures/multi_resource.tf
iac-explain tests/fixtures/ec2_with_sg.tf
iac-explain tests/fixtures/simple_s3.tf
```

---

## How it works

```
.tf file
   │
   ▼
[ python-hcl2 (deterministic) ] ──► [{type, name, config}, ...]
   │                                           │
   │  raw HCL text                             │
   └──────────────────────────────► [ Claude — forced tool-use ]
                                               │
                                    [ Pydantic validates output ]
                                               │
                                               ▼
                                    [ Rich terminal | JSON ]
```

1. **`parser.py`** loads the `.tf` file with `python-hcl2` and flattens every `resource` block into a list of `{type, name, config}` dicts. No LLM, no guessing.

2. **`analyzer.py`** sends both the raw HCL and the structured list to Claude using Anthropic's [tool-use API](https://docs.anthropic.com/en/docs/tool-use) with `tool_choice` forced to `submit_analysis`. Claude is structurally required to return the exact schema — it cannot return free prose.

3. **`schemas.py`** defines the output contract as Pydantic models. The JSON Schema is generated automatically and passed as the tool's `input_schema`. Pydantic validates the response again on the way out.

4. **`formatter.py`** renders the validated `Analysis` object as Rich panels with per-finding issue/fix layout, or as indented JSON with `--format json`.

---

## Output schema

```python
class Analysis(BaseModel):
    summary: str                           # one paragraph, plain English
    resources: list[ResourceExplanation]   # one entry per resource block
    cost: CostEstimate                     # monthly USD range + caveats
    security_findings: list[SecurityFinding]
    overall_risk: Severity                 # info | low | medium | high | critical
```

---

## Tests

```bash
pytest          # 36 tests, no API key required
```

Parser tests are fully deterministic. Analyzer tests mock the Anthropic client with `unittest.mock`.

---

## Limitations

- **Single-file only.** Multi-file modules, `terraform plan` output, and variable files are not supported in v1.
- **AWS-first.** AWS resources are explained and priced well. GCP and Azure resources will be described but cost estimates will be less accurate.
- **Cost is a rough LLM estimate.** No live pricing API. Treat ranges as order-of-magnitude guidance, not quotes. Enable [Infracost](https://www.infracost.io) for real numbers.
- **Variables not resolved.** Values defined in `variables.tf` or `terraform.tfvars` appear as interpolation strings in the analysis.

---

## License

MIT - [Christopher Mbaike](mailto:christophermbaike@gmail.com)
