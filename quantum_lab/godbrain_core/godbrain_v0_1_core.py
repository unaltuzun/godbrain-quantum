# GODBRAIN v0.1 - CANONICAL CORE ARTIFACT
# STATUS: FROZEN / LOCKED
# AUTHOR: CODE-21 / UNAL TUZUN
# DESC: Continuous-time dynamical evolution under structural noise.
# NOTE: No ML, No RL. Pure stochastic physical selection.

import numpy as np

# --- 0. CONSTANTS & CONFIGURATION ---
DIM = 3
DT = 0.01
T_HORIZON_STEPS = 5000
R_MAX = 10.0
VAR_MIN = 1e-3

# Ornstein–Uhlenbeck Noise Parameters
TAU_NOISE = 0.5
SIGMA_LEVELS = [0.05, 0.15, 0.30]

# --- 1. GENOME DEFINITION ---
class Genome:
    def __init__(self):
        self.A = np.random.randn(DIM, DIM) * 0.1
        ev = np.linalg.eigvals(self.A)
        if np.any(np.real(ev) > 0):
            self.A -= np.eye(DIM) * (np.max(np.real(ev)) + 0.1)

        self.alpha = np.random.randn(DIM, DIM) * 0.1
        self.beta = np.random.randn(DIM, DIM, DIM) * 0.1
        self.b = np.random.randn(DIM) * 0.1

    def mutate(self, p_struct=0.01):
        mutation_scale = 0.02
        self.A += np.random.randn(*self.A.shape) * mutation_scale
        self.alpha += np.random.randn(*self.alpha.shape) * mutation_scale
        self.beta += np.random.randn(*self.beta.shape) * mutation_scale
        self.b += np.random.randn(*self.b.shape) * mutation_scale

        if np.random.rand() < p_struct:
            i, j = np.random.randint(0, DIM, 2)
            self.A[i, j] = 0.0

# --- 2. DYNAMICAL SYSTEM ---
def compute_dynamics(x, genome, eta):
    term_linear = genome.A @ x
    term_quad = np.zeros(DIM)

    for i in range(DIM):
        self_sq = np.sum(genome.alpha[i, :] * (x ** 2))
        cross = 0.0
        for j in range(DIM):
            for k in range(j + 1, DIM):
                cross += genome.beta[i, j, k] * x[j] * x[k]
        term_quad[i] = self_sq + cross

    return term_linear + term_quad + genome.b + eta

# --- 3. SIMULATION CORE ---
def simulate(genome, sigma_noise):
    x = np.random.randn(DIM) * 0.1
    eta = np.zeros(DIM)

    trajectory = np.zeros((T_HORIZON_STEPS, DIM))
    velocities = np.zeros((T_HORIZON_STEPS, DIM))

    valid = True

    for t in range(T_HORIZON_STEPS):
        dW = np.random.randn(DIM) * np.sqrt(DT)
        d_eta = -(1.0 / TAU_NOISE) * eta * DT + sigma_noise * np.sqrt(2.0 / TAU_NOISE) * dW
        eta += d_eta

        dxdt = compute_dynamics(x, genome, eta)
        velocities[t] = dxdt
        x += dxdt * DT
        trajectory[t] = x

        if np.linalg.norm(x) > R_MAX:
            valid = False
            break

    return trajectory, velocities, valid

# --- 4. FITNESS / SURVIVAL CHECK ---
def evaluate_genome(genome):
    traj, vels, valid = simulate(genome, sigma_noise=SIGMA_LEVELS[1])

    if not valid:
        return None

    variances = np.var(traj, axis=0)
    if not np.any(variances >= VAR_MIN):
        return None

    half = T_HORIZON_STEPS // 2
    f_stab = np.mean(np.var(traj[half:], axis=0))
    f_energy = np.mean(np.linalg.norm(vels, axis=1) ** 2)

    return (f_stab, f_energy)

# --- EXECUTION BLOCK ---
if __name__ == "__main__":
    print("GODBRAIN v0.1 CORE LOADED.")
    genome = Genome()
    result = evaluate_genome(genome)

    if result:
        print("ALIVE | Metrics:", result)
    else:
        print("DEAD | Genome failed constraints.")
