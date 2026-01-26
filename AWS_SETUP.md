# AWS First-Time Setup Guide

Complete walkthrough from creating an AWS account to deploying AGMS.

## Prerequisites

- Credit card (for AWS account verification)
- Email address
- Phone number (for verification)
- ~2 hours for initial setup

---

## Step 1: Create AWS Account

### 1.1 Sign Up

1. Go to [aws.amazon.com](https://aws.amazon.com)
2. Click **"Create an AWS Account"**
3. Enter your email and choose account name (e.g., "AGMS Production")
4. Verify your email with the code sent
5. Create a strong root password

### 1.2 Contact Information

- Choose **"Personal"** or **"Business"** account type
- Fill in your contact details
- Agree to the AWS Customer Agreement

### 1.3 Payment Information

- Add a credit/debit card
- AWS will charge $1 (refunded) to verify the card
- You won't be charged until you use services

### 1.4 Identity Verification

- Choose SMS or voice call verification
- Enter the code received

### 1.5 Select Support Plan

- Choose **"Basic Support - Free"** (sufficient for starting out)

✅ **Account created!** You'll receive a confirmation email.

---

## Step 2: Secure Your Account

> ⚠️ **CRITICAL**: Never use root account for daily work!

### 2.1 Enable MFA on Root Account

1. Sign in to [AWS Console](https://console.aws.amazon.com)
2. Click your account name (top right) → **Security credentials**
3. Under "Multi-factor authentication (MFA)", click **Assign MFA device**
4. Choose **Authenticator app** (use Google Authenticator, Authy, or similar)
5. Scan the QR code and enter two consecutive codes

### 2.2 Create IAM Admin User

1. Go to **IAM** service (search in console)
2. Click **Users** → **Create user**
3. User name: `admin` (or your name)
4. Check ✅ **Provide user access to AWS Management Console**
5. Select **I want to create an IAM user**
6. Set a password
7. Click **Next**
8. Select **Attach policies directly**
9. Check ✅ **AdministratorAccess**
10. Click **Create user**
11. **Save the sign-in URL** (e.g., `https://123456789012.signin.aws.amazon.com/console`)

### 2.3 Sign Out and Sign In as IAM User

1. Sign out of root account
2. Go to your IAM sign-in URL
3. Sign in with your new IAM user

---

## Step 3: Install AWS CLI & SAM CLI

### 3.1 Install AWS CLI

```bash
# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify
aws --version
```

### 3.2 Configure AWS CLI

1. Go to IAM → Users → your admin user → **Security credentials**
2. Click **Create access key**
3. Select **Command Line Interface (CLI)**
4. Download the CSV file (save it securely!)

```bash
aws configure
# Enter:
# AWS Access Key ID: (from CSV)
# AWS Secret Access Key: (from CSV)
# Default region name: ap-southeast-1
# Default output format: json
```

### 3.3 Install SAM CLI

```bash
# Linux
wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install

# Verify
sam --version
```

---

## Step 4: Set Up VPC (Virtual Private Cloud)

Your Lambda functions need a VPC to securely connect to RDS.

### 4.1 Use Default VPC (Easiest)

AWS creates a default VPC in each region. Check if you have one:

1. Go to **VPC** service
2. Click **Your VPCs**
3. Look for a VPC marked as "Default VPC"

If you have a default VPC, note down:

- **VPC ID**: vpc-xxxxxxxx
- **Subnet IDs**: Go to Subnets, note at least 2 subnet IDs

### 4.2 Create VPC (If No Default)

1. Go to **VPC** → **Create VPC**
2. Select **VPC and more** (creates subnets automatically)
3. Name: `agms-vpc`
4. IPv4 CIDR: `10.0.0.0/16`
5. Number of Availability Zones: `2`
6. Number of public subnets: `2`
7. Number of private subnets: `2`
8. NAT gateways: `In 1 AZ` (~$45/month) or `None` (cheaper, but no internet from Lambda)
9. Click **Create VPC**

---

## Step 5: Create RDS Database

### 5.1 Create Database

1. Go to **RDS** service
2. Click **Create database**
3. Choose **Standard create**
4. Engine: **PostgreSQL**
5. Engine version: **15.x** (latest 15)
6. Templates: **Free tier** (for testing) or **Production** (for real use)
7. DB instance identifier: `agms-db`
8. Master username: `postgres`
9. Master password: Create a strong password (SAVE THIS!)
10. Instance class: `db.t3.micro` (Free tier eligible)
11. Storage: 20 GB
12. VPC: Select your VPC
13. Public access: **No** (Lambda will connect via VPC)
14. Create new security group: `agms-db-sg`
15. Initial database name: `agms`
16. Click **Create database**

⏰ **Wait 5-10 minutes** for the database to be created.

### 5.2 Get Database Endpoint

1. Click on your database `agms-db`
2. Copy the **Endpoint** (e.g., `agms-db.xxxxx.ap-southeast-1.rds.amazonaws.com`)

---

## Step 6: Create RDS Proxy

RDS Proxy pools database connections - essential for Lambda.

### 6.1 Store Credentials in Secrets Manager

1. Go to **Secrets Manager** service
2. Click **Store a new secret**
3. Secret type: **Credentials for Amazon RDS database**
4. Username: `postgres`
5. Password: (your RDS password)
6. Database: Select `agms-db`
7. Click **Next**
8. Secret name: `agms/db-credentials`
9. Click **Next** → **Next** → **Store**

### 6.2 Create RDS Proxy

1. Go to **RDS** → **Proxies**
2. Click **Create proxy**
3. Proxy identifier: `agms-proxy`
4. Engine family: **PostgreSQL**
5. Database: Select `agms-db`
6. Connection pool: **100** (max connections)
7. Secrets Manager secret: Select `agms/db-credentials`
8. IAM authentication: **Required** (more secure) or **Not required** (easier)
9. Subnets: Select at least 2 private subnets
10. Additional connectivity: Select the RDS security group
11. Click **Create proxy**

⏰ **Wait 5-10 minutes** for the proxy to be available.

### 6.3 Get Proxy Endpoint

1. Click on your proxy `agms-proxy`
2. Copy the **Proxy endpoint** (e.g., `agms-proxy.proxy-xxxxx.ap-southeast-1.rds.amazonaws.com`)

---

## Step 7: Configure Security Groups

### 7.1 Create Lambda Security Group

1. Go to **VPC** → **Security Groups**
2. Click **Create security group**
3. Name: `agms-lambda-sg`
4. Description: `Security group for AGMS Lambda functions`
5. VPC: Select your VPC
6. Outbound rules: Keep "All traffic" (default)
7. Click **Create**

### 7.2 Update RDS Security Group

1. Find the security group for your RDS (e.g., `agms-db-sg`)
2. Click **Edit inbound rules**
3. Add rule:
   - Type: **PostgreSQL**
   - Source: Select `agms-lambda-sg` (the Lambda security group)
4. Click **Save rules**

---

## Step 8: Deploy with SAM

### 8.1 Prepare Environment Variables

Create a file `samconfig.toml` in your agms folder:

```toml
version = 0.1

[default.deploy.parameters]
stack_name = "agms-prod"
region = "ap-southeast-1"
confirm_changeset = true
capabilities = "CAPABILITY_IAM"

[default.deploy.parameters.parameter_overrides]
Environment = "prod"
DatabaseSecret = "arn:aws:secretsmanager:ap-southeast-1:YOUR_ACCOUNT_ID:secret:agms/db-credentials-XXXXXX"
VpcSubnetIds = "subnet-xxxxx,subnet-yyyyy"
VpcSecurityGroupIds = "sg-zzzzz"
```

Replace:

- `YOUR_ACCOUNT_ID`: Your 12-digit AWS account ID
- `subnet-xxxxx,subnet-yyyyy`: Your private subnet IDs
- `sg-zzzzz`: Your Lambda security group ID

### 8.2 Build and Deploy

```bash
cd agms

# Build the application
sam build

# Deploy (first time)
sam deploy --guided

# Follow the prompts - it will ask for:
# - Stack name: agms-prod
# - Region: ap-southeast-1
# - Parameters (it will read from samconfig.toml)
```

### 8.3 Get Your API URL

After deployment:

```bash
sam list stack-outputs --stack-name agms-prod
```

Look for `ApiEndpoint` - this is your production API URL!

---

## Step 9: Run Database Migrations

### Option A: Local Machine via VPN/Bastion (Complex)

You'd need to set up a bastion host or VPN to access the database.

### Option B: Create a Migration Lambda (Recommended)

Add this to your `template.yaml` and redeploy:

```yaml
MigrationFunction:
  Type: AWS::Serverless::Function
  Properties:
    FunctionName: !Sub 'agms-migrate-${Environment}'
    Handler: lambda_handlers.run_migrations
    Timeout: 300
    VpcConfig:
      SubnetIds: !Ref VpcSubnetIds
      SecurityGroupIds: !Ref VpcSecurityGroupIds
```

Then run:

```bash
aws lambda invoke --function-name agms-migrate-prod output.txt
```

---

## Step 10: Update Frontend

In your `dayung/.env.production`:

```bash
NEXT_PUBLIC_API_URL=https://xxxxxx.execute-api.ap-southeast-1.amazonaws.com
```

Deploy your frontend to Vercel/Netlify with this environment variable.

---

## Cost Summary (First Month Estimate)

| Service | Cost |
|---------|------|
| RDS db.t3.micro | ~$15 (Free tier: $0) |
| RDS Proxy | ~$20 |
| Lambda (light usage) | ~$0-2 |
| API Gateway | ~$1-4 |
| Secrets Manager | ~$0.40 |
| NAT Gateway (if used) | ~$45 |
| **Total (with NAT)** | **~$82/month** |
| **Total (without NAT)** | **~$37/month** |

> 💡 **Free Tier**: If your account is <12 months old, RDS db.t3.micro is free for 750 hours/month.

---

## Troubleshooting

### "Access Denied" errors

```bash
# Check your credentials
aws sts get-caller-identity
```

### Lambda timeout connecting to RDS

- Check Lambda is in the same VPC as RDS
- Check security group allows Lambda → RDS on port 5432
- Check Lambda has a route to RDS (NAT Gateway or VPC endpoint)

### SAM deploy fails

```bash
# View detailed error
sam deploy --debug

# Delete and recreate stack
sam delete --stack-name agms-prod
sam deploy
```

---

## Next Steps

1. ✅ Set up monitoring (CloudWatch Alarms)
2. ✅ Configure custom domain (Route 53 + API Gateway)
3. ✅ Set up CI/CD (GitHub Actions)
4. ✅ Enable backup for RDS
