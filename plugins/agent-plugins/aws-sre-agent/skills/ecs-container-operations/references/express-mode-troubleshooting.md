# ECS Express Mode & ECS Service Connect Troubleshooting Reference

## 1. ECS Express Mode (`DescribeExpressGatewayService`)

ECS Express Mode provisions a simplified gateway service with managed load balancing and auto-scaling.

### Inspection via `ecs` MCP (`ecs_resource_management`)
1. List Express Gateway Services or call `DescribeExpressGatewayService`:
   - `ecs_resource_management(api_operation="DescribeExpressGatewayService", api_params={"serviceArn": "..."})`
2. Inspect `activeConfigurations` vs `status`:
   - Verify `healthCheckPath`, `cpu`, `memory`, `scalingTarget`, and `networkConfiguration`.
   - If status is `FAILED` or `DEGRADED`, run `ecs_troubleshooting_tool` (`fetch_task_failures` and `fetch_task_logs`) on the backing ECS cluster and service.

---

## 2. ECS Service Connect (`aws-appmesh-envoy` Sidecar) Triage

ECS Service Connect injects an Envoy proxy sidecar into each task to handle service discovery, mTLS, outlier detection, and retries across namespaces.

### Key CloudWatch Metrics (`AWS/ECS/ManagedScaling` & `AWS/ECS`)
- `RequestCountPerTarget`, `TargetResponseTime`, `HTTPCode_Target_5XX_Count`
- `ActiveConnectionCount`, `NewConnectionCount`

### Common Service Connect Failure Modes
1. **Connection Refused Between Client and Upstream Service**:
   - Verify both services belong to the same **Cloud Map Namespace** (`serviceConnectConfiguration.namespace`) and that the client service defines `clientAliases` while the server service exports `portName` in `serviceConnectConfiguration.services`.
2. **Envoy Proxy OOM / High CPU Overhead**:
   - On high-RPS services (>2,000 RPS per task), ensure the Task Definition allocates sufficient task-level CPU/memory to accommodate both the application container and the injected Service Connect Envoy container (`ecs-service-connect-*`).
