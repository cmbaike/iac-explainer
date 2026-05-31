# Sample output

Real output captured from running the tool against the included test fixtures.

---

## `insecure_public_bucket.tf` — terminal

```
$ iac-explain tests/fixtures/insecure_public_bucket.tf

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
│                      (estimated 1 GB to 100 GB range)                        │
│                      Data transfer out from S3 to internet users is not      │
│                      included and can be significant for popular websites    │
│                      ($0.09/GB after first 100 GB/month)                     │
│                      S3 request costs (GET, PUT) excluded                    │
│                      IAM roles and security groups have no direct cost       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭──────────────── Security Findings  Overall risk: ✖✖ CRITICAL ────────────────╮
│ ✖✖ CRITICAL  aws_s3_bucket.public_assets                                     │
│ Issue S3 bucket has ACL set to 'public-read', making all contents accessible │
│       to anyone on the internet without authentication.                      │
│ Fix   Remove the 'acl = "public-read"' line and use a CloudFront             │
│       distribution or signed URLs to control access.                         │
│ ──────────────────────────────────────────────────────────────────────────── │
│ ✖✖ CRITICAL  aws_s3_bucket.public_assets                                     │
│ Issue S3 bucket has no encryption configured, meaning data is stored         │
│       unencrypted at rest.                                                   │
│ Fix   Add an 'aws_s3_bucket_server_side_encryption_configuration' resource   │
│       with 'sse_algorithm = "AES256"' or 'aws:kms'.                          │
│ ──────────────────────────────────────────────────────────────────────────── │
│ ✖✖ CRITICAL  aws_s3_bucket_public_access_block.public_assets                 │
│ Issue All public access block settings are disabled (set to false),          │
│       explicitly removing AWS safety guardrails against accidental public    │
│       exposure.                                                              │
│ Fix   Set block_public_acls, block_public_policy, ignore_public_acls, and   │
│       restrict_public_buckets all to true.                                   │
│ ──────────────────────────────────────────────────────────────────────────── │
│ ✖✖ CRITICAL  aws_security_group.open_ssh                                     │
│ Issue Security group allows SSH (port 22) from 0.0.0.0/0, exposing servers  │
│       to brute-force attacks from any internet address.                      │
│ Fix   Change cidr_blocks to a specific office IP range, or use AWS Systems   │
│       Manager Session Manager instead of direct SSH access.                  │
│ ──────────────────────────────────────────────────────────────────────────── │
│ ✖✖ CRITICAL  aws_iam_role_policy.admin_policy                                │
│ Issue IAM policy grants Action '*' and Resource '*', giving unrestricted     │
│       access to all AWS services and resources.                              │
│ Fix   Replace the wildcard policy with specific actions and resources needed │
│       for the role's actual purpose.                                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

---

## `multi_resource.tf` — JSON (`--format json`)

```
$ iac-explain tests/fixtures/multi_resource.tf --format json
```

```json
{
  "summary": "This configuration sets up a production application environment in Amazon's cloud with three main components: a database for storing data, a server running the application itself, and a caching layer to speed up repeated requests. All of these run inside a private network with controlled access rules. The database is a PostgreSQL instance with high availability (it automatically replicates to a second data center), encrypted storage, and daily backups kept for a week. The application server is a single medium-sized virtual machine also with encrypted storage. A Redis cache helps reduce load on the database. The network is divided into private and public sections, though currently only the private section is actively used by the application components.",
  "resources": [
    {
      "resource_type": "aws_vpc",
      "name": "main",
      "purpose": "Creates an isolated private network where all the application components can communicate securely."
    },
    {
      "resource_type": "aws_subnet",
      "name": "private",
      "purpose": "A private network segment that hosts the application server, database, and cache without direct internet access."
    },
    {
      "resource_type": "aws_subnet",
      "name": "public",
      "purpose": "A network segment configured for internet-facing resources, though not currently used by any components."
    },
    {
      "resource_type": "aws_db_subnet_group",
      "name": "main",
      "purpose": "Groups network segments together so the database can be placed in approved private areas."
    },
    {
      "resource_type": "aws_security_group",
      "name": "rds",
      "purpose": "Acts as a firewall for the database, only allowing connections from the application server."
    },
    {
      "resource_type": "aws_db_instance",
      "name": "postgres",
      "purpose": "A managed PostgreSQL database with automatic backups, high availability across data centers, and encrypted storage."
    },
    {
      "resource_type": "aws_security_group",
      "name": "app",
      "purpose": "Acts as a firewall for the application server, allowing traffic on port 8080 only from within the private network."
    },
    {
      "resource_type": "aws_instance",
      "name": "app",
      "purpose": "A virtual server running the main application with encrypted storage."
    },
    {
      "resource_type": "aws_elasticache_subnet_group",
      "name": "main",
      "purpose": "Groups network segments together so the cache can be placed in approved private areas."
    },
    {
      "resource_type": "aws_elasticache_cluster",
      "name": "redis",
      "purpose": "A Redis cache that stores frequently accessed data in memory to speed up the application."
    }
  ],
  "cost": {
    "low_usd_monthly": 220.0,
    "high_usd_monthly": 280.0,
    "confidence": "medium",
    "caveats": [
      "Pricing assumes us-east-1 region",
      "RDS db.t3.medium Multi-AZ costs approximately $120-150/month depending on I/O usage",
      "EC2 t3.medium on-demand costs approximately $30/month; reserved instances would be 40-60% cheaper",
      "ElastiCache cache.t3.micro costs approximately $12-15/month",
      "50 GB gp3 storage for RDS costs approximately $6/month",
      "30 GB gp3 storage for EC2 costs approximately $2.50/month",
      "Outbound data transfer and backup storage beyond the 7-day retention are excluded"
    ]
  },
  "security_findings": [
    {
      "severity": "high",
      "resource": "aws_db_instance.postgres",
      "issue": "Database password is hardcoded in the Terraform configuration as a plain text string.",
      "recommendation": "Use 'manage_master_user_password = true' to let AWS store the password in Secrets Manager, or reference a Terraform variable marked as sensitive."
    },
    {
      "severity": "medium",
      "resource": "aws_elasticache_cluster.redis",
      "issue": "Redis cache cluster does not have encryption at rest enabled.",
      "recommendation": "Add 'at_rest_encryption_enabled = true' to the aws_elasticache_cluster configuration."
    },
    {
      "severity": "medium",
      "resource": "aws_elasticache_cluster.redis",
      "issue": "Redis cache cluster does not have encryption in transit enabled.",
      "recommendation": "Add 'transit_encryption_enabled = true' to the aws_elasticache_cluster configuration."
    }
  ],
  "overall_risk": "high"
}
```
