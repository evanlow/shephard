# AWS Deployment Guide — Shepherd

A comprehensive, step-by-step guide for deploying the Shepherd church attendance management system to AWS using EC2 (application server) and RDS PostgreSQL (database), with a fully automated GitHub Actions continuous deployment pipeline.

---

## Table of Contents

**Part I — One-Time AWS Infrastructure Setup**
1. [Prerequisites](#1-prerequisites)
2. [Architecture Overview](#2-architecture-overview)
3. [Networking — VPC and Subnets](#3-networking--vpc-and-subnets)
4. [Security Groups](#4-security-groups)
5. [Database — RDS PostgreSQL](#5-database--rds-postgresql)
6. [Data File Storage — S3](#6-data-file-storage--s3)
7. [IAM Roles and Policies](#7-iam-roles-and-policies)
8. [Launch and Configure the EC2 Instance](#8-launch-and-configure-the-ec2-instance)
9. [Initialise the Database and Admin User](#9-initialise-the-database-and-admin-user)

**Part II — Continuous Deployment Pipeline**
10. [Pipeline Overview](#10-pipeline-overview)
11. [GitHub ↔ AWS Authentication (OIDC)](#11-github--aws-authentication-oidc)
12. [GitHub Repository Secrets](#12-github-repository-secrets)
13. [Branch Protection Rules](#13-branch-protection-rules)
14. [GitHub Environments and Deployment Protection](#14-github-environments-and-deployment-protection)
15. [The GitHub Actions Workflow](#15-the-github-actions-workflow)
16. [Deployment Notifications](#16-deployment-notifications)
17. [README Status Badge](#17-readme-status-badge)
18. [Deployment Script on the EC2 Instance](#18-deployment-script-on-the-ec2-instance)
19. [First Deployment via the Pipeline](#19-first-deployment-via-the-pipeline)
20. [How Continuous Deployment Works](#20-how-continuous-deployment-works)
21. [Rollback Procedure](#21-rollback-procedure)

**Part III — Common Concerns**
22. [HTTPS and Domain Setup](#22-https-and-domain-setup)
23. [Flask Application Security](#23-flask-application-security)
24. [Nginx Rate Limiting and Abuse Prevention](#24-nginx-rate-limiting-and-abuse-prevention)
25. [Environment Variables Reference](#25-environment-variables-reference)
26. [Data Files Setup](#26-data-files-setup)
27. [Post-Deployment Verification](#27-post-deployment-verification)
28. [Security Hardening — Step-by-Step](#28-security-hardening--step-by-step)
29. [Monitoring and Log Management](#29-monitoring-and-log-management)
30. [Database Backup and Restore](#30-database-backup-and-restore)
31. [Cost Estimates](#31-cost-estimates)
32. [Troubleshooting](#32-troubleshooting)

---

# Part I — One-Time AWS Infrastructure Setup

---

## 1. Prerequisites

### AWS Account

- An AWS account with billing set up ([aws.amazon.com](https://aws.amazon.com)).
- Create a non-root IAM user for your day-to-day work. Never use the root account for infrastructure tasks.
- Install and configure the AWS CLI:

```bash
# Install (macOS/Linux)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Configure with your IAM credentials
aws configure
# AWS Access Key ID: <your-key>
# AWS Secret Access Key: <your-secret>
# Default region name: ap-southeast-1        ← choose the region closest to your users
# Default output format: json
```

### Local tools required

| Tool | Version | Purpose |
|---|---|---|
| AWS CLI | v2 | AWS management from the command line |
| Python | 3.11+ | Matches the production runtime |
| Git | any | Source control |
| SSH client | any | Connect to the EC2 instance |

### Choose a region

Pick the AWS region nearest your primary user base. This guide uses **`ap-southeast-1` (Singapore)** as the example. Replace all region references with your chosen region.

---

## 2. Architecture Overview

```
Internet
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  AWS Region (ap-southeast-1)                            │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  VPC  10.0.0.0/16                               │   │
│  │                                                  │   │
│  │  ┌──────────────────┐  ┌──────────────────────┐ │   │
│  │  │ Public Subnet    │  │ Private Subnet        │ │   │
│  │  │ 10.0.1.0/24      │  │ 10.0.2.0/24          │ │   │
│  │  │ (AZ-a)           │  │ (AZ-a)               │ │   │
│  │  │                  │  │                      │ │   │
│  │  │  ┌────────────┐  │  │  ┌────────────────┐  │ │   │
│  │  │  │  EC2       │  │  │  │  RDS Postgres  │  │ │   │
│  │  │  │  t3.small  │──┼──┼─▶│  db.t3.micro   │  │ │   │
│  │  │  │  (Nginx +  │  │  │  │  shepherd DB   │  │ │   │
│  │  │  │   Gunicorn)│  │  │  └────────────────┘  │ │   │
│  │  │  └────────────┘  │  │                      │ │   │
│  │  └──────────────────┘  └──────────────────────┘ │   │
│  │                                                  │   │
│  │  ┌──────────────────────────────────────────┐   │   │
│  │  │  Private Subnet  10.0.3.0/24  (AZ-b)     │   │   │
│  │  │  (Required for RDS Multi-AZ subnet group) │   │   │
│  │  └──────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  S3 Bucket (shepherd-data-files)                        │
└─────────────────────────────────────────────────────────┘
```

**Traffic flow:**
1. User → EC2 public IP / domain on port 443 (HTTPS)
2. Nginx (reverse proxy on EC2) terminates TLS and proxies to Gunicorn on `127.0.0.1:8000`
3. Gunicorn runs the Flask application
4. Flask connects to RDS PostgreSQL in the private subnet (port 5432, never publicly accessible)
5. Flask reads/writes any static data files via S3 or the EC2 local filesystem

**Key design decisions:**
- RDS lives in a **private subnet** — it is not reachable from the internet.
- EC2 is in a **public subnet** with an Elastic IP — it is the only ingress point.
- Security Groups act as virtual firewalls controlling which ports can communicate with which resources.

---

## 3. Networking — VPC and Subnets

### 3.1 Create a VPC

In the AWS Console → **VPC** → **Create VPC**:

| Field | Value |
|---|---|
| Resources to create | VPC only |
| Name tag | `shepherd-vpc` |
| IPv4 CIDR | `10.0.0.0/16` |
| Tenancy | Default |

Click **Create VPC**.

### 3.2 Create Subnets

You need three subnets: one public (for EC2) and two private (for RDS — RDS subnet groups require at least two AZs).

Go to **VPC → Subnets → Create subnet**. Create each subnet in sequence:

**Subnet 1 — Public (EC2)**

| Field | Value |
|---|---|
| VPC | `shepherd-vpc` |
| Subnet name | `shepherd-public-1a` |
| Availability Zone | `ap-southeast-1a` |
| IPv4 CIDR | `10.0.1.0/24` |

**Subnet 2 — Private (RDS, AZ-a)**

| Field | Value |
|---|---|
| VPC | `shepherd-vpc` |
| Subnet name | `shepherd-private-1a` |
| Availability Zone | `ap-southeast-1a` |
| IPv4 CIDR | `10.0.2.0/24` |

**Subnet 3 — Private (RDS, AZ-b)**

| Field | Value |
|---|---|
| VPC | `shepherd-vpc` |
| Subnet name | `shepherd-private-1b` |
| Availability Zone | `ap-southeast-1b` |
| IPv4 CIDR | `10.0.3.0/24` |

### 3.3 Internet Gateway

1. **VPC → Internet Gateways → Create internet gateway**
   - Name: `shepherd-igw`
2. After creation, select it and click **Actions → Attach to VPC → shepherd-vpc**.

### 3.4 Route Tables

**Public Route Table** (for the EC2 subnet):

1. **VPC → Route Tables → Create route table**
   - Name: `shepherd-public-rt`
   - VPC: `shepherd-vpc`
2. Select the new route table → **Routes → Edit routes → Add route**:
   - Destination: `0.0.0.0/0`
   - Target: `shepherd-igw`
3. **Subnet associations → Edit subnet associations** → select `shepherd-public-1a`.

**Private subnets** use the default (local-only) route table — no changes needed.

### 3.5 Auto-assign Public IPv4

Go to **Subnets → shepherd-public-1a → Actions → Edit subnet settings**:
- ✅ Enable auto-assign public IPv4 address

---

## 4. Security Groups

Security Groups are stateful firewalls. Create three: one for EC2, one for RDS, and one for the deployment pipeline.

### 4.1 EC2 Security Group

**VPC → Security Groups → Create security group**

| Field | Value |
|---|---|
| Name | `shepherd-ec2-sg` |
| VPC | `shepherd-vpc` |

**Inbound rules:**

| Type | Port | Source | Description |
|---|---|---|---|
| SSH | 22 | Your IP only (e.g. `203.0.113.10/32`) | Admin SSH access |
| HTTP | 80 | `0.0.0.0/0` | Let Certbot complete ACME challenge |
| HTTPS | 443 | `0.0.0.0/0` | Public web traffic |

> **Important:** Restrict SSH to your specific IP address. Using `0.0.0.0/0` for SSH is a serious security risk.

**Outbound rules:**

| Type | Port | Destination | Description |
|---|---|---|---|
| All traffic | All | `0.0.0.0/0` | Allow outbound (for package installs, S3, RDS) |

### 4.2 RDS Security Group

| Field | Value |
|---|---|
| Name | `shepherd-rds-sg` |
| VPC | `shepherd-vpc` |

**Inbound rules:**

| Type | Port | Source | Description |
|---|---|---|---|
| PostgreSQL | 5432 | `shepherd-ec2-sg` (security group ID) | Allow EC2 to reach RDS |

> Use the **security group ID** (sg-xxxxxxxxx) of `shepherd-ec2-sg` as the source — not an IP range. This means only the EC2 instance can connect to the database, regardless of its IP address.

**Outbound rules:** Leave default (all outbound allowed) or restrict to VPC CIDR.

### 4.3 GitHub Actions Deployment Security Group (optional — for SSM)

If you later switch to AWS Systems Manager Session Manager instead of SSH for deployments, you can remove the SSH inbound rule entirely. For now, SSH with IP restriction is sufficient.

---

## 5. Database — RDS PostgreSQL

### 5.1 Create a DB Subnet Group

**RDS → Subnet groups → Create DB subnet group**

| Field | Value |
|---|---|
| Name | `shepherd-db-subnet-group` |
| VPC | `shepherd-vpc` |
| Availability Zones | `ap-southeast-1a`, `ap-southeast-1b` |
| Subnets | `shepherd-private-1a`, `shepherd-private-1b` |

### 5.2 Create the RDS Instance

**RDS → Databases → Create database**

| Section | Field | Value |
|---|---|---|
| Creation method | — | Standard create |
| Engine | Engine type | PostgreSQL |
| Engine version | — | PostgreSQL 16.x (latest stable) |
| Templates | — | Free tier (dev) or Production |
| Settings | DB instance identifier | `shepherd-db` |
| Settings | Master username | `shepherd_admin` |
| Settings | Master password | Generate a strong password; save it securely |
| Instance | DB instance class | `db.t3.micro` (free tier) or `db.t3.small` (production) |
| Storage | Storage type | gp3 |
| Storage | Allocated storage | 20 GiB |
| Storage | Enable auto scaling | ✅ (max 100 GiB) |
| Connectivity | VPC | `shepherd-vpc` |
| Connectivity | DB subnet group | `shepherd-db-subnet-group` |
| Connectivity | Public access | **No** |
| Connectivity | VPC security group | `shepherd-rds-sg` |
| Database options | Initial database name | `shepherd` |
| Backups | Automated backups | ✅ Enabled |
| Backups | Backup retention | 7 days |
| Maintenance | Auto minor version upgrade | ✅ Enabled |
| Deletion protection | — | ✅ Enable (strongly recommended) |

Click **Create database**. This takes approximately 5–10 minutes.

### 5.3 Note the RDS Endpoint

Once the instance is available:
- Go to **RDS → Databases → shepherd-db**
- Copy the **Endpoint** (e.g. `shepherd-db.xxxxxxxxxxxx.ap-southeast-1.rds.amazonaws.com`)

Your `DATABASE_URL` will be:
```
postgresql://shepherd_admin:<password>@shepherd-db.xxxxxxxxxxxx.ap-southeast-1.rds.amazonaws.com:5432/shepherd
```

---

## 6. Data File Storage — S3

Even if Shepherd does not currently store file uploads, an S3 bucket is useful for storing backups, exports, and any future file attachments.

### 6.1 Create the S3 Bucket

**S3 → Create bucket**

| Field | Value |
|---|---|
| Bucket name | `shepherd-data-<your-aws-account-id>` (must be globally unique) |
| Region | Same as your EC2/RDS region |
| Object Ownership | ACLs disabled (recommended) |
| Block all public access | ✅ **Block all public access** (important) |
| Versioning | Enable (allows recovering accidentally deleted files) |
| Server-side encryption | SSE-S3 (AES-256, default) |

### 6.2 Bucket Policy

After creation, add a bucket policy that denies unencrypted uploads (**S3 → Bucket → Permissions → Bucket policy**):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnencryptedUploads",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::shepherd-data-<your-account-id>/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "AES256"
        }
      }
    }
  ]
}
```

---

## 7. IAM Roles and Policies

### 7.1 EC2 Instance Profile

The EC2 instance needs an IAM role so it can access S3 without embedding credentials.

**IAM → Roles → Create role**

| Field | Value |
|---|---|
| Trusted entity | AWS service |
| Use case | EC2 |
| Role name | `shepherd-ec2-role` |

Attach these managed policies:
- `AmazonSSMManagedInstanceCore` — enables AWS Systems Manager (optional but recommended for secure shell access without SSH keys in future)

Then attach a custom inline policy for S3 access (**Add permissions → Create inline policy**):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ShepherdS3Access",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::shepherd-data-<your-account-id>",
        "arn:aws:s3:::shepherd-data-<your-account-id>/*"
      ]
    }
  ]
}
```

### 7.2 GitHub Actions Deployment Role (for OIDC)

This role allows GitHub Actions to deploy to EC2 without storing long-lived AWS credentials as GitHub secrets.

**IAM → Roles → Create role**

| Field | Value |
|---|---|
| Trusted entity | Web identity |
| Identity provider | `token.actions.githubusercontent.com` (create this OIDC provider first — see Section 11) |
| Audience | `sts.amazonaws.com` |
| Role name | `shepherd-github-deploy-role` |

Restrict the trust policy to your specific GitHub repository:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<YOUR_ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:evanlow/shepherd:*"
        }
      }
    }
  ]
}
```

Attach a minimal inline policy that only allows SSM SendCommand (to trigger the deploy script on EC2) or EC2 describe (to look up the instance):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowSSMDeployCommand",
      "Effect": "Allow",
      "Action": [
        "ssm:SendCommand",
        "ssm:GetCommandInvocation"
      ],
      "Resource": [
        "arn:aws:ec2:ap-southeast-1:<YOUR_ACCOUNT_ID>:instance/<YOUR_EC2_INSTANCE_ID>",
        "arn:aws:ssm:ap-southeast-1::document/AWS-RunShellScript"
      ]
    },
    {
      "Sid": "AllowDescribeInstances",
      "Effect": "Allow",
      "Action": "ec2:DescribeInstances",
      "Resource": "*"
    }
  ]
}
```

> **Alternatively**, if you prefer SSH-based deployment (simpler setup), the GitHub Actions role needs no AWS permissions — the EC2 private key is stored as a GitHub secret instead. Section 11 and Section 15 cover both approaches.

---

## 8. Launch and Configure the EC2 Instance

### 8.1 Allocate an Elastic IP

Before launching EC2, reserve an Elastic IP so the server's public IP never changes.

**EC2 → Elastic IPs → Allocate Elastic IP address → Allocate**

Note the allocated IP address (e.g. `54.179.x.x`). You will associate it with the instance after launch.

### 8.2 Launch the EC2 Instance

**EC2 → Instances → Launch instances**

| Section | Field | Value |
|---|---|---|
| Name | — | `shepherd-app` |
| AMI | — | Ubuntu Server 24.04 LTS (64-bit x86) |
| Instance type | — | `t3.small` (2 vCPU, 2 GB RAM; upgrade to `t3.medium` for heavier load) |
| Key pair | — | Create a new key pair named `shepherd-key`, download the `.pem` file, store it securely |
| Network | VPC | `shepherd-vpc` |
| Network | Subnet | `shepherd-public-1a` |
| Network | Auto-assign public IP | Enable |
| Network | Security group | `shepherd-ec2-sg` |
| Storage | Root volume | 20 GiB gp3 |
| IAM instance profile | — | `shepherd-ec2-role` |

Click **Launch instance**.

### 8.3 Associate Elastic IP

**EC2 → Elastic IPs → Select your IP → Actions → Associate Elastic IP address**
- Instance: `shepherd-app`

### 8.4 SSH into the Instance

```bash
chmod 400 shepherd-key.pem
ssh -i shepherd-key.pem ubuntu@<your-elastic-ip>
```

### 8.5 Configure the Server

Run all of the following as the `ubuntu` user (using `sudo` where required).

#### Update packages

```bash
sudo apt-get update && sudo apt-get upgrade -y
```

#### Install Python 3.11, pip, venv, and system dependencies

```bash
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev \
    python3-pip git nginx certbot python3-certbot-nginx \
    postgresql-client libpq-dev build-essential
```

#### Install the AWS CLI (optional, for S3 operations from the instance)

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip"
unzip /tmp/awscliv2.zip -d /tmp
sudo /tmp/aws/install
```

#### Create the application user and directory

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin shepherd
sudo mkdir -p /opt/shepherd
sudo chown root:root /opt/shepherd
sudo chmod 755 /opt/shepherd
```

#### Clone the repository

```bash
sudo git clone https://github.com/evanlow/shepherd.git /opt/shepherd/app
sudo chown -R shepherd:shepherd /opt/shepherd/app
cd /opt/shepherd/app
```

#### Create the virtual environment and install dependencies

```bash
cd /opt/shepherd/app
sudo -u shepherd python3.11 -m venv venv
sudo -u shepherd /opt/shepherd/app/venv/bin/pip install --upgrade pip
sudo -u shepherd /opt/shepherd/app/venv/bin/pip install -r requirements.txt
```

#### Create the environment file

```bash
sudo mkdir -p /etc/shepherd
sudo nano /etc/shepherd/env
```

Paste the following content (replace placeholders with real values):

```ini
FLASK_ENV=production
SECRET_KEY=<generate-with-python-secrets-token_hex-32>
DATABASE_URL=postgresql://shepherd_admin:<password>@shepherd-db.xxxxxxxxxxxx.ap-southeast-1.rds.amazonaws.com:5432/shepherd
```

Secure the file:

```bash
sudo chown root:shepherd /etc/shepherd/env
sudo chmod 640 /etc/shepherd/env
```

#### Create the Gunicorn systemd service

```bash
sudo nano /etc/systemd/system/shepherd.service
```

```ini
[Unit]
Description=Shepherd Flask Application (Gunicorn)
After=network.target

[Service]
User=shepherd
Group=shepherd
WorkingDirectory=/opt/shepherd/app
EnvironmentFile=/etc/shepherd/env
ExecStart=/opt/shepherd/app/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/shepherd/access.log \
    --error-logfile /var/log/shepherd/error.log \
    --log-level info \
    run:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Create the log directory:

```bash
sudo mkdir -p /var/log/shepherd
sudo chown shepherd:shepherd /var/log/shepherd
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable shepherd
sudo systemctl start shepherd
sudo systemctl status shepherd
```

#### Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/shepherd
```

```nginx
server {
    listen 80;
    server_name <your-domain.com>;       # or your Elastic IP for testing

    # Redirect all HTTP to HTTPS (uncomment after obtaining TLS cert)
    # return 301 https://$host$request_uri;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90;
        client_max_body_size 10M;
    }
}
```

Enable the site and reload Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/shepherd /etc/nginx/sites-enabled/shepherd
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

---

## 9. Initialise the Database and Admin User

### 9.1 Initialise the Database Schema

SSH into the EC2 instance:

```bash
sudo -u shepherd bash -lc '
cd /opt/shepherd/app
source venv/bin/activate
set -a
. /etc/shepherd/env
set +a
FLASK_APP=run.py flask init-db
'
```

Expected output:
```
Database tables created.
```

### 9.2 Create the First Superuser

```bash
sudo -u shepherd bash -lc '
cd /opt/shepherd/app
source venv/bin/activate
set -a
. /etc/shepherd/env
set +a
FLASK_APP=run.py flask create-admin
'
```

You will be prompted for:
- **Username** — your login username
- **Email** — your email address
- **Password** — minimum 8 characters (enter twice to confirm)

This creates the first superuser account with full access to the admin UI.

### 9.3 Verify the App is Reachable

From your local machine:

```bash
curl http://<your-elastic-ip>/
```

You should receive a redirect to `/login`. Navigate to `http://<your-elastic-ip>/login` in a browser to confirm the login page loads.

---

# Part II — Continuous Deployment Pipeline

---

## 10. Pipeline Overview

The goal is: every push to the `main` branch automatically deploys to the EC2 instance, with smoke tests run before deployment and health checks run after.

```
Developer pushes to main
         │
         ▼
┌─────────────────────────────────────────────┐
│  GitHub Actions Workflow                    │
│                                             │
│  1. checkout code                           │
│  2. set up Python 3.11                      │
│  3. install dependencies                    │
│  4. run smoke tests                         │
│       └── FAIL → stop, notify              │
│  5. optionally assume AWS role via OIDC    │
│  6. SSH into EC2 (or SSM SendCommand)       │
│  7. run /opt/shepherd/deploy.sh             │
│  8. health check — GET /login → 200         │
│       └── FAIL → rollback, notify          │
│  9. notify success                          │
└─────────────────────────────────────────────┘
         │
         ▼
   EC2 Instance (/opt/shepherd/deploy.sh)
         │
         ├── git pull origin main
         ├── pip install -r requirements.txt
         ├── FLASK_APP=run.py flask init-db  (schema initialisation; idempotent)
         └── sudo systemctl reload shepherd
```

---

## 11. GitHub ↔ AWS Authentication (OIDC)

OpenID Connect (OIDC) allows GitHub Actions to obtain short-lived AWS credentials without storing long-lived AWS access keys as secrets.

### 11.1 Create the OIDC Identity Provider in IAM

**IAM → Identity providers → Add provider**

| Field | Value |
|---|---|
| Provider type | OpenID Connect |
| Provider URL | `https://token.actions.githubusercontent.com` |
| Audience | `sts.amazonaws.com` |

Click **Add provider**.

### 11.2 Verify the Trust Relationship

After creating the provider, create (or update) the `shepherd-github-deploy-role` as described in Section 7.2. The `StringLike` condition `repo:evanlow/shepherd:*` ensures only workflows from this specific repository can assume the role.

To restrict further to only the `main` branch:
```json
"token.actions.githubusercontent.com:sub": "repo:evanlow/shepherd:ref:refs/heads/main"
```

### 11.3 Note the Role ARN

**IAM → Roles → shepherd-github-deploy-role → Copy ARN**

It looks like: `arn:aws:iam::<YOUR_ACCOUNT_ID>:role/shepherd-github-deploy-role`

---

## 12. GitHub Repository Secrets

Go to **GitHub → Repository → Settings → Secrets and variables → Actions → New repository secret**.

Add the following secrets:

| Secret name | Value | Description |
|---|---|---|
| `AWS_ROLE_ARN` | `arn:aws:iam::<ACCOUNT_ID>:role/shepherd-github-deploy-role` | OIDC role for AWS auth (optional for SSH-only deploy) |
| `AWS_REGION` | `ap-southeast-1` | AWS region (optional for SSH-only deploy) |
| `EC2_HOST` | `54.179.x.x` (Elastic IP) | EC2 public IP or DNS |
| `EC2_USER` | `ubuntu` | SSH login user |
| `EC2_SSH_KEY` | Contents of `shepherd-key.pem` | Private key for SSH deployment |
| `HEALTH_CHECK_URL` | `https://your-domain.com/login` | URL to check after deployment |

> **Note on `EC2_SSH_KEY`:** Copy the entire contents of the `.pem` file, including the `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----` lines.

---

## 13. Branch Protection Rules

Protect the `main` branch to prevent direct pushes and ensure the CI pipeline always runs before merging.

**GitHub → Repository → Settings → Branches → Add branch protection rule**

| Setting | Value |
|---|---|
| Branch name pattern | `main` |
| Require a pull request before merging | ✅ |
| Require status checks to pass before merging | ✅ |
| Status checks required | `test` (the CI job name from your workflow) |
| Require branches to be up to date | ✅ |
| Do not allow bypassing the above settings | ✅ (even for admins) |
| Restrict who can push to matching branches | ✅ (only yourself or a specific team) |

---

## 14. GitHub Environments and Deployment Protection

Environments add a visual deployment history and allow requiring manual approval for production deployments.

**GitHub → Repository → Settings → Environments → New environment**

| Field | Value |
|---|---|
| Environment name | `production` |

Configure the `production` environment:

| Setting | Value |
|---|---|
| Required reviewers | Add yourself (or a teammate) |
| Wait timer | 0 minutes (or set a delay for calm deployments) |
| Deployment branches | Selected branches → `main` |

In the workflow file, reference this environment:

```yaml
jobs:
  deploy:
    environment: production
```

This means every deployment to `main` will pause for your manual approval in the GitHub UI before the deploy job runs.

---

## 15. The GitHub Actions Workflow

Create the file `.github/workflows/deploy.yml` in your repository:

```yaml
name: Test and Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  id-token: write    # Required only when using the optional OIDC step below
  contents: read

jobs:
  # ─── Job 1: Run smoke tests ────────────────────────────────────────────────
  test:
    name: Smoke Tests
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run smoke tests
        run: python tests/run_all_smoke.py

  # ─── Job 2: Deploy to EC2 (main branch only) ───────────────────────────────
  deploy:
    name: Deploy to Production
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    environment: production

    steps:
      - name: Configure AWS credentials via OIDC (optional for SSH-only deploy)
        if: ${{ secrets.AWS_ROLE_ARN != '' && secrets.AWS_REGION != '' }}
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION }}

      - name: Deploy to EC2 via SSH
        env:
          EC2_HOST: ${{ secrets.EC2_HOST }}
          EC2_USER: ${{ secrets.EC2_USER }}
          SSH_KEY: ${{ secrets.EC2_SSH_KEY }}
        run: |
          # Write the SSH private key to a temporary file
          echo "$SSH_KEY" > /tmp/deploy_key.pem
          chmod 600 /tmp/deploy_key.pem

          # Add host key and enforce strict checking
          mkdir -p ~/.ssh
          ssh-keyscan -H "$EC2_HOST" >> ~/.ssh/known_hosts

          # SSH into EC2 and run the deploy script
          ssh -i /tmp/deploy_key.pem \
              -o StrictHostKeyChecking=yes \
              -o UserKnownHostsFile=~/.ssh/known_hosts \
              -o ConnectTimeout=30 \
              "$EC2_USER@$EC2_HOST" \
              "sudo /opt/shepherd/deploy.sh 2>&1"

          # Clean up key
          rm -f /tmp/deploy_key.pem

      - name: Health check
        env:
          HEALTH_CHECK_URL: ${{ secrets.HEALTH_CHECK_URL }}
        run: |
          echo "Waiting 10s for the app to restart..."
          sleep 10
          STATUS=$(curl --silent --output /dev/null --write-out "%{http_code}" \
                   --max-time 30 "$HEALTH_CHECK_URL")
          echo "Health check returned HTTP $STATUS"
          if [ "$STATUS" -ne 200 ] && [ "$STATUS" -ne 302 ]; then
            echo "❌ Health check failed (HTTP $STATUS). Deployment may be broken."
            exit 1
          fi
          echo "✅ Health check passed."

      - name: Notify deployment success
        if: success()
        run: echo "🚀 Deployment to production succeeded at $(date -u)."

      - name: Notify deployment failure
        if: failure()
        run: echo "❌ Deployment to production FAILED. Check the logs above."
```

> **Alternative: SSM SendCommand** instead of SSH  
> If you configure Systems Manager on the EC2 instance (via `AmazonSSMManagedInstanceCore` IAM policy and the SSM agent), you can replace the SSH step with an SSM SendCommand step. This removes the need for an inbound SSH security group rule entirely — a more secure architecture. See the AWS documentation for `aws ssm send-command`.

---

## 16. Deployment Notifications

### Slack Notifications (optional)

To receive Slack messages on deployment success or failure:

1. Create a Slack Incoming Webhook at [api.slack.com/messaging/webhooks](https://api.slack.com/messaging/webhooks).
2. Add the webhook URL as a GitHub secret: `SLACK_WEBHOOK_URL`.
3. Replace the notification steps in the workflow:

```yaml
      - name: Notify Slack on success
        if: success()
        uses: slackapi/slack-github-action@v1.26.0
        with:
          payload: |
            {
              "text": "✅ *Shepherd* deployed successfully to production by ${{ github.actor }} — commit `${{ github.sha }}` on `${{ github.ref_name }}`"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
          SLACK_WEBHOOK_TYPE: INCOMING_WEBHOOK

      - name: Notify Slack on failure
        if: failure()
        uses: slackapi/slack-github-action@v1.26.0
        with:
          payload: |
            {
              "text": "❌ *Shepherd* deployment FAILED — commit `${{ github.sha }}` by ${{ github.actor }}. <${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|View logs>"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
          SLACK_WEBHOOK_TYPE: INCOMING_WEBHOOK
```

### Email Notifications

GitHub can send email notifications for failed workflows automatically. Enable this at:  
**GitHub → Settings (personal) → Notifications → Actions → Send email for failed workflows**.

---

## 17. README Status Badge

Add a workflow status badge to the top of `README.md`:

```markdown
![Deploy](https://github.com/evanlow/shepherd/actions/workflows/deploy.yml/badge.svg?branch=main)
```

This badge shows green when the latest `main` deployment passed and red when it failed.

---

## 18. Deployment Script on the EC2 Instance

Create the deploy script on the EC2 instance:

```bash
sudo nano /opt/shepherd/deploy.sh
```

```bash
#!/usr/bin/env bash
# /opt/shepherd/deploy.sh
# Pulls the latest code and restarts the application.
# Run as: sudo /opt/shepherd/deploy.sh
set -euo pipefail

APP_DIR="/opt/shepherd/app"
VENV="$APP_DIR/venv"
LOG_FILE="/var/log/shepherd/deploy.log"

echo "=== Deploy started at $(date -u) ===" | tee -a "$LOG_FILE"

cd "$APP_DIR"

# Pull latest code
echo "Pulling latest code..." | tee -a "$LOG_FILE"
git fetch origin main
git reset --hard origin/main

# Install/update Python dependencies
echo "Installing dependencies..." | tee -a "$LOG_FILE"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r requirements.txt

# Initialise database schema (init-db runs db.create_all and is idempotent)
echo "Initialising database schema..." | tee -a "$LOG_FILE"
set -a
. /etc/shepherd/env
set +a
FLASK_APP=run.py "$VENV/bin/flask" init-db

# Gracefully reload the application (zero-downtime with Gunicorn)
echo "Reloading Gunicorn..." | tee -a "$LOG_FILE"
systemctl reload shepherd

echo "=== Deploy complete at $(date -u) ===" | tee -a "$LOG_FILE"
```

Make the script executable:

```bash
sudo chown root:root /opt/shepherd/deploy.sh
sudo chmod 750 /opt/shepherd/deploy.sh
```

Allow the `ubuntu` user to run the deploy script as root without a password:

```bash
sudo visudo
```

Add this line at the bottom:

```
ubuntu ALL=(ALL) NOPASSWD: /opt/shepherd/deploy.sh
```

---

## 19. First Deployment via the Pipeline

With all of the above in place:

1. **Commit and push** the `.github/workflows/deploy.yml` file to the `main` branch.
2. Go to **GitHub → Repository → Actions** and watch the `Test and Deploy` workflow run.
3. The `test` job runs the smoke tests.
4. If tests pass and you have required reviewers configured, you will be prompted to approve the deployment.
5. After approval, the `deploy` job SSHs into EC2 and runs `/opt/shepherd/deploy.sh`.
6. The health check confirms the app is responding.
7. Check the deployment log on EC2:
   ```bash
   tail -f /var/log/shepherd/deploy.log
   ```

---

## 20. How Continuous Deployment Works

After the first deployment, every subsequent push to `main` follows this flow automatically:

1. **Code push** → triggers the `Test and Deploy` workflow.
2. **Smoke tests** run in a clean Python 3.11 environment. If any test fails, the workflow stops — nothing is deployed.
3. **Approval** (if you configured required reviewers in the `production` environment) — you approve in the GitHub Actions UI.
4. **Optional AWS OIDC** — GitHub Actions obtains short-lived AWS credentials when you use AWS APIs (for SSH-only deployment, you can skip this).
5. **SSH deploy** — the workflow SSHs into EC2 and runs `/opt/shepherd/deploy.sh`.
6. **Deploy script** pulls the latest code, updates dependencies, initialises schema (`flask init-db`), and reloads Gunicorn.
7. **Health check** — the workflow verifies the app is responding with HTTP 200/302.
8. **Notification** — success or failure notification is sent.

The entire pipeline typically completes in under 3 minutes.

---

## 21. Rollback Procedure

### Automatic rollback via health check failure

If the health check step in the GitHub Actions workflow detects that the app is not responding after deployment, the workflow fails. At this point you must roll back manually.

### Manual rollback on EC2

```bash
ssh -i shepherd-key.pem ubuntu@<elastic-ip>
cd /opt/shepherd/app

# View recent git log to find a known-good commit
git log --oneline -10

# Roll back to the previous commit (or a specific SHA)
git reset --hard HEAD~1
# OR
git reset --hard <known-good-sha>

# Reinstall dependencies for that commit
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Reload the application
sudo systemctl reload shepherd

# Verify
curl -I http://localhost/login
```

### Roll forward (preferred)

The preferred approach is to push a fix commit to `main` and let the pipeline redeploy. This keeps a complete audit trail in git history.

---

# Part III — Common Concerns

---

## 22. HTTPS and Domain Setup

### 22.1 Point a Domain to the EC2 Elastic IP

With your domain registrar or DNS provider, add an **A record**:

| Type | Name | Value | TTL |
|---|---|---|---|
| A | `@` (or `shepherd.yourdomain.com`) | `<your-elastic-ip>` | 300 |

### 22.2 Obtain a TLS Certificate with Certbot (Let's Encrypt)

SSH into EC2:

```bash
sudo certbot --nginx -d your-domain.com
```

Certbot will:
1. Automatically edit `/etc/nginx/sites-available/shepherd` to add HTTPS configuration.
2. Create a cronjob (or systemd timer) to auto-renew the certificate every 60 days.

After running Certbot, your Nginx config will automatically include:
- Port 80 → 443 redirect
- Port 443 with your certificate
- HTTP/2 and HSTS support

### 22.3 Verify Auto-Renewal

```bash
sudo certbot renew --dry-run
```

This should report `Congratulations, all simulated renewals succeeded.`

### 22.4 Update the Nginx Config for Gunicorn (After Certbot)

Certbot modifies the config automatically. Verify it looks correct:

```bash
sudo cat /etc/nginx/sites-available/shepherd
sudo nginx -t
sudo systemctl reload nginx
```

### 22.5 Update the Health Check URL

Update the `HEALTH_CHECK_URL` GitHub secret to use `https://`:

```
https://your-domain.com/login
```

---

## 23. Flask Application Security

### 23.1 Production Config Validation

Shepherd's `config.py` includes a `ProductionConfig.validate()` method that raises an error on startup if `DATABASE_URL` is not set or `SECRET_KEY` has not been changed from the development default. This means a misconfigured production deployment will fail fast and visibly.

### 23.2 Session Security

In production, explicitly set `SESSION_COOKIE_SECURE = True` so session cookies are only sent over HTTPS. Ensure:

```python
# config.py — ProductionConfig
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
```

Add these to `ProductionConfig` in `config.py` if not already present.

### 23.3 CSRF Protection

Consider adding Flask-WTF to enable CSRF protection on all form submissions:

```bash
pip install Flask-WTF
```

```python
# app/__init__.py
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)
```

### 23.4 Security Headers

Add the following headers to the Nginx config inside the `server` block:

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';" always;
```

---

## 24. Nginx Rate Limiting and Abuse Prevention

### 24.1 Rate Limiting

Add rate limiting to the Nginx config to protect against brute-force and DoS attacks:

```nginx
# Place in /etc/nginx/nginx.conf inside the http {} block:
limit_req_zone $binary_remote_addr zone=shepherd_general:10m rate=20r/s;
limit_req_zone $binary_remote_addr zone=shepherd_login:10m rate=5r/m;
```

Apply in the site config:

```nginx
server {
    ...

    location / {
        limit_req zone=shepherd_general burst=40 nodelay;
        proxy_pass http://127.0.0.1:8000;
        ...
    }

    location /login {
        limit_req zone=shepherd_login burst=10 nodelay;
        proxy_pass http://127.0.0.1:8000;
        ...
    }
}
```

### 24.2 Block Common Attack Patterns

```nginx
# Block common exploit paths
location ~* \.(php|asp|aspx|jsp)$ {
    return 404;
}

# Block access to hidden files (e.g. .git, .env)
location ~ /\. {
    deny all;
    return 404;
}
```

### 24.3 Connection Limits

```nginx
# In the http {} block:
limit_conn_zone $binary_remote_addr zone=shepherd_conn:10m;

# In the server {} block:
limit_conn shepherd_conn 20;
```

### 24.4 Reload Nginx After Changes

```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## 25. Environment Variables Reference

All environment variables for Shepherd are set in `/etc/shepherd/env` on the EC2 instance.

| Variable | Required | Example Value | Description |
|---|---|---|---|
| `FLASK_ENV` | ✅ | `production` | Selects the `ProductionConfig` class. Must be `production` in production. |
| `SECRET_KEY` | ✅ | `a3f8...` (64-char hex) | Flask session signing key. Must be a strong random value. Never reuse. |
| `DATABASE_URL` | ✅ | `postgresql://shepherd_admin:pass@hostname:5432/shepherd` | Full PostgreSQL connection URL. |

**How to generate `SECRET_KEY`:**

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

After editing `/etc/shepherd/env`, restart the app:

```bash
sudo systemctl restart shepherd
```

---

## 26. Data Files Setup

If Shepherd is extended to store uploaded files (e.g. member photos, import spreadsheets), use the S3 bucket created in Section 6.

The EC2 instance profile (`shepherd-ec2-role`) already grants the necessary S3 permissions. Access S3 from within the Flask application using the `boto3` library:

```bash
pip install boto3
```

```python
import boto3
s3 = boto3.client("s3", region_name="ap-southeast-1")
# The client automatically uses the EC2 instance profile — no credentials needed in code.
```

For bulk data file uploads (e.g. initial member data), use the AWS CLI directly on the EC2 instance:

```bash
aws s3 cp /path/to/local/file.csv s3://shepherd-data-<account-id>/uploads/file.csv --sse AES256
```

---

## 27. Post-Deployment Verification

Run through this checklist after every deployment:

```
□ 1. App loads:       curl -I https://your-domain.com/login  → HTTP 200
□ 2. Redirect works:  curl -I https://your-domain.com/       → HTTP 302 to /login
□ 3. Login works:     Log in with the admin credentials in a browser
□ 4. Dashboard loads: Navigate to /dashboard after login
□ 5. API works:       curl -s -b cookie.txt https://your-domain.com/api/members/ → JSON array
□ 6. TLS cert valid:  Check the padlock in the browser; no cert warnings
□ 7. HTTPS enforced:  curl -I http://your-domain.com/ → 301 to https://
□ 8. DB reachable:    sudo systemctl status shepherd → "active (running)"
□ 9. Gunicorn logs:   tail /var/log/shepherd/error.log → no recent errors
□ 10. Nginx logs:     tail /var/log/nginx/error.log → no recent errors
```

---

## 28. Security Hardening — Step-by-Step

### Generate a Production SECRET_KEY

On any machine with Python:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and set it as `SECRET_KEY` in `/etc/shepherd/env`. Never commit this value to git.

### SSH Hardening

Edit `/etc/ssh/sshd_config` on the EC2 instance:

```bash
sudo nano /etc/ssh/sshd_config
```

Set the following values:

```ini
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
MaxAuthTries 3
LoginGraceTime 30
AllowUsers ubuntu
X11Forwarding no
```

Restart SSH (make sure you can still connect before doing this!):

```bash
sudo sshd -t            # test config syntax
sudo systemctl restart sshd
```

### AWS WAF — Web Application Firewall

AWS WAF sits in front of your EC2 instance and blocks common web attack patterns at the network edge.

> **Note:** WAF is not available directly for EC2. You need to put the EC2 behind an **Application Load Balancer (ALB)** to use WAF. If budget allows, consider:

1. Create an ALB in front of the EC2 instance.
2. Attach an **AWS WAF Web ACL** to the ALB.
3. Enable AWS Managed Rule groups:
   - `AWSManagedRulesCommonRuleSet` — OWASP Top 10 protections
   - `AWSManagedRulesKnownBadInputsRuleSet` — known bad inputs and exploits
   - `AWSManagedRulesSQLiRuleSet` — SQL injection protection
4. Set the EC2 security group to only accept traffic from the ALB security group (removing direct internet access to port 443).

**Approximate additional cost:** ALB ≈ $16/month + WAF ≈ $6/month + $0.60 per million requests.

For a small church system, WAF is optional. Nginx rate limiting (Section 24) and Security Groups provide reasonable protection without this cost.

### VPC Flow Logs

Enable VPC Flow Logs to record all network traffic in and out of your VPC for security auditing and incident investigation.

**VPC → Your VPC → Flow logs → Create flow log**

| Field | Value |
|---|---|
| Filter | All |
| Maximum aggregation interval | 1 minute |
| Destination | CloudWatch Logs |
| Destination log group | `/aws/vpc/shepherd-flow-logs` |
| IAM role | Create a new role or use an existing VPC Flow Logs role |

**Create a CloudWatch log group first:**

```bash
aws logs create-log-group --log-group-name /aws/vpc/shepherd-flow-logs --region ap-southeast-1
```

### Secrets Rotation Procedure

Rotate secrets periodically (every 90 days recommended) or immediately if a compromise is suspected:

1. **Rotate `SECRET_KEY`:**
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
   Update `/etc/shepherd/env` on the EC2 instance. **Note:** rotating `SECRET_KEY` invalidates all active login sessions — all users will be logged out.
   ```bash
   sudo systemctl restart shepherd
   ```

2. **Rotate the RDS password:**
   - **RDS → Databases → shepherd-db → Modify → New master password**
   - Update `DATABASE_URL` in `/etc/shepherd/env` on EC2.
   - Restart the application: `sudo systemctl restart shepherd`

3. **Rotate EC2 SSH key pair:**
   - Generate a new key pair locally: `ssh-keygen -t ed25519 -f shepherd-key-new`
   - Add the new public key to `/home/ubuntu/.ssh/authorized_keys` on EC2.
   - Update the `EC2_SSH_KEY` GitHub secret with the new private key.
   - Test that the new key works, then remove the old public key from `authorized_keys`.

4. **Revoke and reissue GitHub Actions OIDC role** if the AWS account is compromised — update the IAM role trust policy.

### IAM Least-Privilege Review

Review IAM permissions periodically using **IAM Access Analyzer** and **IAM Access Advisor**:

```bash
# View last-used timestamps for each permission in the role
aws iam generate-service-last-accessed-details \
    --arn arn:aws:iam::<ACCOUNT_ID>:role/shepherd-ec2-role

aws iam get-service-last-accessed-details --job-id <job-id>
```

Remove any permissions that have not been used in the past 90 days.

### Security Hardening Summary Checklist

```
□ SECRET_KEY is a strong random value (64+ hex chars), not the dev default
□ DATABASE_URL password is strong (20+ chars, mixed case, numbers, symbols)
□ RDS is in a private subnet — no public access
□ RDS deletion protection is enabled
□ EC2 SSH access is restricted to specific IP(s) only
□ SSH root login is disabled (PermitRootLogin no)
□ SSH password authentication is disabled (PasswordAuthentication no)
□ Nginx security headers are configured (HSTS, X-Frame-Options, CSP, etc.)
□ Nginx rate limiting is enabled on /login
□ Session cookies use Secure, HttpOnly, SameSite flags
□ TLS certificate is valid and auto-renews
□ /etc/shepherd/env file has restricted permissions (640, root:ubuntu)
□ Git repository does not contain .env files (check .gitignore)
□ S3 bucket blocks all public access
□ VPC Flow Logs are enabled
□ CloudTrail is enabled (audit log of all AWS API calls)
□ IAM users use MFA
□ Root account uses MFA and access keys are deactivated
```

---

## 29. Monitoring and Log Management

### 29.1 Application Logs

| Log file | Contents |
|---|---|
| `/var/log/shepherd/access.log` | All HTTP requests handled by Gunicorn |
| `/var/log/shepherd/error.log` | Application errors and exceptions |
| `/var/log/shepherd/deploy.log` | History of all deployments |
| `/var/log/nginx/access.log` | All requests received by Nginx (before proxying) |
| `/var/log/nginx/error.log` | Nginx errors |
| `journalctl -u shepherd` | systemd service logs |

```bash
# Live-tail the application error log
tail -f /var/log/shepherd/error.log

# View recent systemd service events
journalctl -u shepherd -n 100 --no-pager

# Nginx access log
tail -f /var/log/nginx/access.log
```

### 29.2 Log Rotation

Configure logrotate to prevent logs from filling the disk:

```bash
sudo nano /etc/logrotate.d/shepherd
```

```ini
/var/log/shepherd/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        systemctl reload shepherd > /dev/null 2>&1 || true
    endscript
}
```

### 29.3 AWS CloudWatch Metrics

Basic EC2 metrics (CPU, network, disk I/O) are available in CloudWatch automatically. For application-level monitoring:

**Install the CloudWatch agent on EC2:**

```bash
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb
```

**Create a config file at `/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json`:**

```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/shepherd/error.log",
            "log_group_name": "/shepherd/app/error",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/nginx/error.log",
            "log_group_name": "/shepherd/nginx/error",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  },
  "metrics": {
    "metrics_collected": {
      "mem": { "measurement": ["mem_used_percent"] },
      "disk": { "measurement": ["disk_used_percent"], "resources": ["/"] }
    },
    "append_dimensions": { "InstanceId": "${aws:InstanceId}" }
  }
}
```

Start the agent:

```bash
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config -m ec2 \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s
```

### 29.4 CloudWatch Alarms

Set up alarms for important metrics:

**CPU utilisation:**

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "Shepherd-CPU-High" \
  --alarm-description "EC2 CPU > 80% for 5 minutes" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=InstanceId,Value=<YOUR_INSTANCE_ID> \
  --alarm-actions arn:aws:sns:ap-southeast-1:<ACCOUNT_ID>:shepherd-alerts \
  --region ap-southeast-1
```

Create an SNS topic for email alerts:

```bash
aws sns create-topic --name shepherd-alerts --region ap-southeast-1
aws sns subscribe \
  --topic-arn arn:aws:sns:ap-southeast-1:<ACCOUNT_ID>:shepherd-alerts \
  --protocol email \
  --notification-endpoint your@email.com \
  --region ap-southeast-1
```

Confirm the subscription email you receive.

### 29.5 RDS Monitoring

In the AWS Console:
- **RDS → Databases → shepherd-db → Monitoring** tab shows CPU, connections, read/write IOPS, free storage.
- Enable **Enhanced Monitoring** for per-second metrics (small additional cost).
- Set an alarm for **FreeStorageSpace < 2 GB** to avoid the database running out of disk.

---

## 30. Database Backup and Restore

### 30.1 Automated RDS Backups

RDS automatically creates daily snapshots with a 7-day retention window (configured when creating the instance in Section 5). These are stored in AWS-managed S3 and are invisible to you unless you need to restore.

### 30.2 Manual Snapshot (Before Major Changes)

Before any significant deployment or schema change, take a manual snapshot:

```bash
aws rds create-db-snapshot \
  --db-instance-identifier shepherd-db \
  --db-snapshot-identifier shepherd-db-pre-deploy-$(date +%Y%m%d) \
  --region ap-southeast-1
```

This takes 1–3 minutes. The snapshot is stored indefinitely until you delete it.

### 30.3 Restore from Snapshot

1. **RDS → Snapshots → Select snapshot → Actions → Restore DB Instance**
2. Provide a new DB instance identifier (e.g. `shepherd-db-restored`).
3. Use the same VPC, subnet group, and security group as the original.
4. After the restore completes, update `DATABASE_URL` in `/etc/shepherd/env` with the new endpoint.
5. Restart Gunicorn: `sudo systemctl restart shepherd`

> **Note:** Restore creates a *new* DB instance — it does not overwrite the existing one. This is intentional, giving you time to verify data before switching over.

### 30.4 Export a SQL Dump

For portable backups or migrating data to a new RDS instance:

```bash
# On EC2 (has access to RDS via the private subnet)
pg_dump -h shepherd-db.xxxxxxxxxxxx.ap-southeast-1.rds.amazonaws.com \
        -U shepherd_admin \
        -d shepherd \
        -F c \
        -f /tmp/shepherd-$(date +%Y%m%d).dump

# Upload to S3 for long-term storage
aws s3 cp /tmp/shepherd-$(date +%Y%m%d).dump \
    s3://shepherd-data-<account-id>/backups/shepherd-$(date +%Y%m%d).dump \
    --sse AES256
```

### 30.5 Restore from a SQL Dump

```bash
# Download from S3
aws s3 cp s3://shepherd-data-<account-id>/backups/shepherd-20250101.dump /tmp/

# Restore to the database
pg_restore -h <rds-endpoint> -U shepherd_admin -d shepherd \
           --clean --if-exists /tmp/shepherd-20250101.dump
```

### 30.6 Scheduled Backup Script

Create `/opt/shepherd/backup.sh` on EC2 for daily scheduled exports:

```bash
sudo nano /opt/shepherd/backup.sh
```

```bash
#!/usr/bin/env bash
set -euo pipefail

DB_HOST="shepherd-db.xxxxxxxxxxxx.ap-southeast-1.rds.amazonaws.com"
DB_USER="shepherd_admin"
DB_NAME="shepherd"
S3_BUCKET="shepherd-data-<account-id>"
DATE=$(date +%Y%m%d-%H%M%S)
DUMP_FILE="/tmp/shepherd-${DATE}.dump"

export PGPASSWORD="<your-db-password>"

pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -F c -f "$DUMP_FILE"
aws s3 cp "$DUMP_FILE" "s3://${S3_BUCKET}/backups/shepherd-${DATE}.dump" --sse AES256
rm -f "$DUMP_FILE"

echo "Backup shepherd-${DATE}.dump uploaded to S3."
```

```bash
sudo chown root:root /opt/shepherd/backup.sh
sudo chmod 750 /opt/shepherd/backup.sh
```

Add a daily crontab entry (as ubuntu user):

```bash
crontab -e
```

```cron
0 2 * * * /opt/shepherd/backup.sh >> /var/log/shepherd/backup.log 2>&1
```

This runs a backup every day at 02:00 UTC.

---

## 31. Cost Estimates

All prices are approximate, in USD, and based on **ap-southeast-1 (Singapore)** on-demand pricing as of early 2025. Actual costs depend on usage.

### Minimum viable setup (free tier eligible in first 12 months)

| Resource | Specification | Monthly cost |
|---|---|---|
| EC2 | t3.micro (1 vCPU, 1 GB) | ~$8.50 (or free if in free tier) |
| RDS | db.t3.micro, 20 GB gp3, single-AZ | ~$14 (or free if in free tier) |
| Elastic IP | 1 address (free while associated) | $0 |
| S3 | 5 GB storage + minimal requests | ~$0.12 |
| Data transfer | ~1 GB outbound | ~$0.09 |
| **Total** | | **~$22–$23/month** |

### Small production setup

| Resource | Specification | Monthly cost |
|---|---|---|
| EC2 | t3.small (2 vCPU, 2 GB) | ~$17 |
| RDS | db.t3.small, 20 GB gp3, single-AZ | ~$28 |
| Elastic IP | 1 address | $0 |
| S3 | 20 GB storage | ~$0.46 |
| CloudWatch | Custom metrics + logs (5 GB) | ~$3 |
| Data transfer | ~5 GB outbound | ~$0.45 |
| **Total** | | **~$49/month** |

### Cost optimisation tips

- Use **Reserved Instances** (1-year commitment) for ~40% savings on EC2 and RDS.
- Schedule EC2 stop/start for non-production environments to avoid charges outside business hours.
- Enable **S3 Intelligent-Tiering** if backup files grow large.
- Enable **RDS Auto Pause** for dev/test instances (Serverless v2 only) to stop billing when idle.
- Set a **AWS Budgets alert** at your monthly threshold:
  ```bash
  aws budgets create-budget --account-id <ACCOUNT_ID> --budget '{
    "BudgetName": "ShepherdMonthly",
    "BudgetLimit": {"Amount": "60", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' --notifications-with-subscribers '[{
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 80
    },
    "Subscribers": [{"SubscriptionType": "EMAIL", "Address": "your@email.com"}]
  }]'
  ```

---

## 32. Troubleshooting

### App not starting / systemd service fails

```bash
# Check the service status
sudo systemctl status shepherd

# View full logs
journalctl -u shepherd -n 50 --no-pager

# Test running Gunicorn manually
cd /opt/shepherd/app
source venv/bin/activate
set -a
. /etc/shepherd/env
set +a
gunicorn --workers 1 --bind 127.0.0.1:8000 run:app
```

Common causes:
- `DATABASE_URL` is incorrect or RDS is not reachable from EC2.
- `SECRET_KEY` is missing or is still the dev default.
- Python dependency not installed (run `pip install -r requirements.txt` again).
- Database tables not created (run `FLASK_APP=run.py flask init-db`).

### Nginx 502 Bad Gateway

Nginx is running but cannot reach Gunicorn.

```bash
# Check if Gunicorn is running on port 8000
ss -tlnp | grep 8000

# Check Gunicorn logs
tail -20 /var/log/shepherd/error.log

# Check Nginx error log
tail -20 /var/log/nginx/error.log

# Restart the application
sudo systemctl restart shepherd
```

### Cannot connect to RDS

```bash
# Test PostgreSQL connection from EC2
psql -h shepherd-db.xxxxxxxxxxxx.ap-southeast-1.rds.amazonaws.com \
     -U shepherd_admin -d shepherd

# Check network connectivity
nc -zv shepherd-db.xxxxxxxxxxxx.ap-southeast-1.rds.amazonaws.com 5432
```

If `nc` times out:
- Verify the EC2 instance is in `shepherd-public-1a`.
- Verify the RDS security group inbound rule references `shepherd-ec2-sg` (not an IP).
- Verify the EC2 security group is attached to the EC2 instance.
- Verify the RDS is in `shepherd-private-1a` or `shepherd-private-1b`.

### GitHub Actions deployment SSH fails

```
ssh: connect to host xx.xx.xx.xx port 22: Connection refused
```

- Verify the `EC2_HOST` secret is the current Elastic IP.
- Verify port 22 is allowed in `shepherd-ec2-sg` inbound rules for the GitHub Actions runner IP range. GitHub publishes their IP ranges at [api.github.com/meta](https://api.github.com/meta) — however this is a large range. For more security, consider switching to AWS SSM.
- Verify the `EC2_SSH_KEY` secret contains the full contents of the `.pem` file.

### Health check fails after deployment

```
❌ Health check failed (HTTP 000)
```

- HTTP 000 means no response — check if Gunicorn restarted correctly.
- SSH into EC2 and check: `sudo systemctl status shepherd` and `tail /var/log/shepherd/error.log`.

### Database schema initialisation fails on deploy

```
Error: FLASK_APP must be set
```

- The deploy script sources `/etc/shepherd/env` to load environment variables. Verify the file exists and is readable by the `shepherd` user.

### `flask init-db` creates tables but app still fails

- Check that `DATABASE_URL` in `/etc/shepherd/env` is correct and that the database `shepherd` exists in RDS.
- Connect to RDS with `psql` and verify: `\dt` should list `users`, `members`, `groups`, `events`, `attendance`.

### TLS certificate not renewing

```bash
sudo certbot renew --dry-run
# If this fails, check:
sudo systemctl status certbot.timer
sudo journalctl -u certbot -n 30 --no-pager
```

Ensure port 80 is still open in the EC2 security group so the ACME HTTP-01 challenge can complete.

### Disk space full on EC2

```bash
df -h /           # check disk usage
du -sh /var/log/* # find large log files
```

Large log files are the most common cause. Configure logrotate (Section 29.2) to prevent this.

---

*Guide written for Shepherd v1.x — Flask 3, Python 3.11, PostgreSQL 16.*
