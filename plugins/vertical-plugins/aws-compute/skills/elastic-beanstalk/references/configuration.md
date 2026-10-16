# Configuration and Customization

Retrieve authoritative namespace and option-setting specifications using the bound `awsknowledge` or `awsiac` MCP servers (never rely on unvalidated external URLs).

## Configuration Hierarchy

Option settings are applied in this precedence order (later overrides earlier):

1. Platform defaults (managed by AWS)
2. Saved configurations (reusable templates)
3. `.ebextensions/*.config` files (in source bundle)
4. Environment properties and option settings (set via CLI/API/IaC)

Platform hooks (`/platform/hooks/prebuild/`, `predeploy/`, `postdeploy/`) run executable shell scripts (`chmod +x`) during the deployment lifecycle on Amazon Linux 2023. Prefer `/platform/hooks/` for shell commands and `.ebextensions/` strictly for option settings and CloudFormation resource declarations.

## Option Settings JSON Format (`--option-settings`)

```json
[
  {
    "Namespace": "aws:autoscaling:launchconfiguration",
    "OptionName": "InstanceType",
    "Value": "t3.small"
  },
  {
    "Namespace": "aws:autoscaling:launchconfiguration",
    "OptionName": "IamInstanceProfile",
    "Value": "app-eb-ec2-instance-profile"
  },
  {
    "Namespace": "aws:autoscaling:launchconfiguration",
    "OptionName": "DisableIMDSv1",
    "Value": "true"
  },
  {
    "Namespace": "aws:elasticbeanstalk:environment",
    "OptionName": "ServiceRole",
    "Value": "aws-elasticbeanstalk-service-role"
  },
  {
    "Namespace": "aws:elasticbeanstalk:environment",
    "OptionName": "LoadBalancerType",
    "Value": "application"
  },
  {
    "Namespace": "aws:elasticbeanstalk:environment:process:default",
    "OptionName": "HealthCheckPath",
    "Value": "/health"
  },
  {
    "Namespace": "aws:elasticbeanstalk:healthreporting:system",
    "OptionName": "SystemType",
    "Value": "enhanced"
  }
]
```

## Key Patterns

### Run Leader-Only Migrations on Deploy

```yaml
container_commands:
  01_migrate:
    command: "python manage.py migrate --noinput"
    leader_only: true
```

### Procfile

```procfile
web: gunicorn myapp.wsgi --bind 0.0.0.0:5000 --workers 2
```

For Worker environments, the `Procfile` defines the HTTP server listening on `localhost` that receives POST requests from the local EB SQS daemon.

## Environment Properties and Native Secrets Manager Integration

Use `aws:elasticbeanstalk:application:environment` for non-sensitive configuration and `aws:elasticbeanstalk:application:environmentsecrets` to inject AWS Secrets Manager or SSM Parameter Store `SecureString` ARNs at runtime without exposing secrets in `.ebextensions/` or plaintext environment variables:

```yaml
option_settings:
  aws:elasticbeanstalk:application:environment:
    APP_ENV: production
    PORT: "5000"
  aws:elasticbeanstalk:application:environmentsecrets:
    DATABASE_URL: arn:aws:secretsmanager:us-east-1:111122223333:secret:myapp/prod/db-AbCdEf
```

## Reverse Proxy Port & Dedicated Health Check

1. Amazon Linux 2023 platforms run `nginx` forwarding to port `5000` by default. Either bind the app to `0.0.0.0:5000` or set the `PORT` environment property to match the app's port.
2. Always expose a lightweight `/health` route returning HTTP `200 OK` without querying downstream databases on every poll.

## Heroku / Render / Railway Migration Checklist

- `DATABASE_URL` -> Provision Aurora Serverless v2 or RDS separately; pass secret ARN via `environmentsecrets`
- `REDIS_URL` -> Provision ElastiCache Serverless; pass endpoint via environment properties
- Third-party API keys -> Store in AWS Secrets Manager; reference via `environmentsecrets`
- `Procfile` -> Supported natively on AL2023 platforms
- Static AWS keys (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`) -> Remove completely; grant permissions via the EC2 IAM Instance Profile
