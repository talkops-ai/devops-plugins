---
name: braket-hybrid-jobs-and-algorithms
description: "Design, containerize, and execute Amazon Braket Hybrid Quantum-Classical Jobs (QAOA, VQE, QML, PennyLane, Qiskit-Braket), manage checkpointing and hyperparameters, and select optimal simulators (SV1, DM1, TN1) vs QPUs (IonQ, Rigetti, IQM, QuEra)."
---

# Amazon Braket Hybrid Jobs & Quantum-Classical Algorithms

Use this skill to architect and execute **Amazon Braket Hybrid Jobs** (`CreateJob`), where classical compute containers run tightly coupled variational loops (VQE, QAOA, Quantum Machine Learning) with low-latency priority access to Braket managed simulators (`SV1`, `DM1`, `TN1`) or physical QPUs (`IonQ`, `Rigetti`, `IQM`, `QuEra`).

## 1. Simulator vs. QPU Selection Matrix

| Target Device | Device ARN | Max Qubits / Topology | Ideal Workload |
| :--- | :--- | :--- | :--- |
| **Local Simulator** (`braket_sv` / `braket_dm`) | Local process | ~25 qubits (SV) / ~12 qubits (DM) | Rapid unit testing, zero AWS cost, debugging noise models locally |
| **SV1** (State Vector) | `arn:aws:braket:::device/quantum-simulator/amazon/sv1` | Up to 34 qubits (all-to-all) | Noise-free variational circuits, gradient estimation (adjoint differentiation) |
| **DM1** (Density Matrix) | `arn:aws:braket:::device/quantum-simulator/amazon/dm1` | Up to 17 qubits (all-to-all) | Realistic noise channel simulation (`depolarizing`, `amplitude_damping`, `readout_error`) |
| **TN1** (Tensor Network) | `arn:aws:braket:::device/quantum-simulator/amazon/tn1` | Up to 50 qubits (sparse/shallow circuits) | Structured, low-entanglement or local-connectivity circuits (e.g., QAOA on bounded-degree graphs) |
| **Gate-Based QPUs** (`IonQ`, `IQM`, `Rigetti`) | Regional QPU ARNs (`us-east-1`, `us-west-1`, `eu-north-1`) | Trapped-ion (all-to-all) or Superconducting (lattice) | Hardware execution, error mitigation (ZNE, readout mitigation), Verbatim compilation |
| **Neutral Atom QPU** (`QuEra Aquila`) | `arn:aws:braket:us-east-1::device/qpu/quera/Aquila` | Up to 256 atoms (Analog Hamiltonian Simulation) | Maximum Independent Set (MIS), combinatorial optimization, Rydberg dynamics |

## 2. Authoring a Production Braket Hybrid Job

Use the `@hybrid_job` decorator or `AwsQuantumJob.create()` to package your classical algorithm script:

```python
from braket.aws import AwsQuantumJob
from braket.devices import Devices
from braket.jobs import hybrid_job, save_job_result, load_job_checkpoint, save_job_checkpoint
from braket.jobs.metrics import log_metric

@hybrid_job(
    device=Devices.Amazon.SV1,
    instance_config={"instanceType": "ml.m5.xlarge", "volumeSizeInGb": 30},
    WaitForCompletion=False,
)
def run_vqe(n_iterations: int = 50, learning_rate: float = 0.1):
    for step in range(n_iterations):
        # Execute quantum circuit / gradient evaluation on priority device queue
        energy = evaluate_ansatz(step, learning_rate)
        log_metric(metric_name="energy", value=energy, iteration_number=step)
        if step % 10 == 0:
            save_job_checkpoint({"step": step, "energy": energy})
    save_job_result({"final_energy": energy})
```

### Hybrid Job Best Practices
1. **Priority Queueing**: Tasks launched *inside* a Braket Hybrid Job receive priority scheduling on the target QPU ahead of standalone `CreateQuantumTask` calls, minimizing drift in device calibration between variational steps.
2. **Adjoint Differentiation on SV1**: When training PennyLane (`lightning.qubit` / `braket.aws.qubit`) on `SV1`, set `diff_method="adjoint"` to compute exact analytical gradients in $O(1)$ circuit executions instead of $2P$ parameter-shift tasks!
3. **Checkpointing for QPU Availability Windows**: Physical QPUs have scheduled availability windows. Always call `save_job_checkpoint()` after each iteration so jobs can resume seamlessly across windows.
