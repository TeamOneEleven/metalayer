---
type: source
tool: "./utils/scripts/run-query.sh \"${SQL}\""
---

# OneEleven Production Database

SQL Server (RDS) accessed via SSM tunnel through an EC2 bastion host. The tunnel is managed automatically — the bastion starts on demand and shuts down when idle.

- **Engine**: SQL Server
- **Database**: invibedprod
- **Access**: Read-only credentials from AWS Secrets Manager
- **Tunnel**: SSM port forwarding on localhost:1433
