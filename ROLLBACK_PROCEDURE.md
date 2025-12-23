# GODBRAIN v5.0 - ROLLBACK PROCEDURE

In the event of critical instability or unforeseen logic failure in the simplified v5.0 architecture, follow these steps to restore the legacy v4.x state.

---

## 🛑 Step 1: Immediate Emergency Halt
If the system is actively losing capital or misbehaving:
```bash
# Stop the orchestrator and genetics labs
kubectl scale deployment voltran genetics --replicas=0 -n godbrain
```

## 🔄 Step 2: Restore Legacy Code
The legacy `agg.py` and modular components are preserved in the following locations:
1.  **Git:** Revert to commit `c8f4a726` (Pre-Simplification).
    ```bash
    git checkout c8f4a726 -- agg.py
    ```
2.  **Archive:** The non-modular versions of the labs are in `/archive`.

## 📦 Step 3: Deployment Rollback (Kubernetes)
To roll back the K8s deployment to the previous stable state:
```bash
# View rollout history
kubectl rollout history deployment/voltran -n godbrain

# Rollback to the previous version
kubectl rollout undo deployment/voltran -n godbrain
```

## 🧹 Step 4: Redis State Reset (Optional)
If namespacing caused data corruption (highly unlikely):
1.  Connect to Redis.
2.  Rename keys back to legacy format (remove `genetics:` prefix).
3.  Restart the pods.

---

## 📞 Support
If the automated rollback fails, check the logs:
```bash
kubectl logs -f deployment/voltran -n godbrain --tail=100
```
> [!WARNING]
> Rolling back will lose the new `/health` monitoring and error boundary protections. Only use as a last resort.
