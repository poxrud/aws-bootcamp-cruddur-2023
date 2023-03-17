# Week 4 — Postgres and RDS

## Create RDS Postgres Instance

I used the AWS ClI to run the following command:

```sh
aws rds create-db-instance \
  --db-instance-identifier cruddur-db-instance \
  --db-instance-class db.t4g.micro \
  --engine postgres \
  --engine-version  14.6 \
  --master-username cruddurroot \
  --master-user-password <secret> \
  --allocated-storage 20 \
  --availability-zone ca-central-1a \
  --backup-retention-period 0 \
  --port 5432 \
  --no-multi-az \
  --db-name cruddur \
  --storage-type gp3 \
  --publicly-accessible \
  --storage-encrypted \
  --enable-performance-insights \
  --performance-insights-retention-period 7 \
  --no-deletion-protection
```

This created an RDS database called `crudder-db-instance` with the username of
`crudderroot`.

![crudder RDS instance](/assets/crudder-rds-instance.png)
