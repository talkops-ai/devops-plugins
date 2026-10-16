# AWS Fargate, Capacity Providers, and Role Separation Reference

## 1. `executionRoleArn` vs. `taskRoleArn` Separation of Duties

Confusing these two IAM roles is one of the top causes of ECS production incidents:

| Attribute | Task Execution Role (`executionRoleArn`) | Task Role (`taskRoleArn`) |
|---|---|---|
| **Who assumes it?** | The **ECS Container Agent / Fargate infrastructure** before the container starts. | The **Application code** running inside the container at runtime (`AWS_CONTAINER_CREDENTIALS_RELATIVE_URI`). |
| **When is it used?** | Image pull (`ecr:*`), CloudWatch `awslogs` stream creation (`logs:*`), and injecting `secrets` from Secrets Manager / SSM Parameter Store at container boot. | Runtime AWS SDK calls made by your application (`s3:GetObject`, `dynamodb:PutItem`, `sqs:SendMessage`, `bedrock:InvokeModel`). |
| **Symptom when missing permissions** | Task fails to start (`TaskFailedToStart` / `ResourceInitializationError`). | Container starts healthy (`RUNNING`), but application throws `AccessDeniedException` in runtime logs. |

---

## 2. Fargate vs. Fargate Spot Resiliency Pattern

- **Never run 100% `FARGATE_SPOT` for latency-sensitive production APIs.**
- Use a mixed **Capacity Provider Strategy** on the ECS Service:
  ```json
  "capacityProviderStrategy": [
    {
      "capacityProvider": "FARGATE",
      "base": 2,
      "weight": 1
    },
    {
      "capacityProvider": "FARGATE_SPOT",
      "base": 0,
      "weight": 3
    }
  ]
  ```
  This guarantees at least `2` baseline tasks always run on standard `FARGATE` while burst capacity scales 3:1 onto `FARGATE_SPOT`.
- Set `stopTimeout` to `120` seconds on containers running on `FARGATE_SPOT` so they catch `SIGTERM` and drain connections during the 2-minute Spot interruption window.

---

## 3. Fargate Ephemeral Storage Exhaustion (`No space left on device`)

- Default Fargate ephemeral storage is **20 GiB** (shared across container root filesystems, `/tmp`, and bind mounts).
- Check `EphemeralStorageUtilized` and `EphemeralStorageReserved` in `AWS/ECS/ContainerInsights`.
- If ML models, large temp files, or unrotated local logs fill 20 GiB, increase `ephemeralStorage.sizeInGiB` up to **200 GiB** in the Task Definition.
