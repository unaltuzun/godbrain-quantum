# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN MLflow Configuration
Experiment tracking and model registry for DNA versioning.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from functools import lru_cache

# Project root
ROOT = Path(__file__).parent.parent


class MLflowConfig:
    """MLflow configuration and utilities."""
    
    # Default experiment name
    DEFAULT_EXPERIMENT = "godbrain-genetics"
    
    # Tracking URI (local SQLite)
    TRACKING_URI = f"sqlite:///{ROOT / 'mlruns' / 'mlflow.db'}"
    
    # Artifact location
    ARTIFACT_LOCATION = str(ROOT / "mlruns" / "artifacts")
    
    @classmethod
    def setup(cls, experiment_name: Optional[str] = None) -> None:
        """
        Initialize MLflow with local tracking.
        
        Args:
            experiment_name: Experiment name (default: godbrain-genetics)
        """
        try:
            import mlflow
            
            # Create directories
            mlruns_dir = ROOT / "mlruns"
            mlruns_dir.mkdir(parents=True, exist_ok=True)
            (mlruns_dir / "artifacts").mkdir(exist_ok=True)
            
            # Set tracking URI
            mlflow.set_tracking_uri(cls.TRACKING_URI)
            
            # Set or create experiment
            exp_name = experiment_name or cls.DEFAULT_EXPERIMENT
            experiment = mlflow.get_experiment_by_name(exp_name)
            
            if experiment is None:
                mlflow.create_experiment(
                    exp_name,
                    artifact_location=cls.ARTIFACT_LOCATION
                )
            
            mlflow.set_experiment(exp_name)
            print(f"[MLFLOW] Initialized: {exp_name}")
            print(f"[MLFLOW] Tracking URI: {cls.TRACKING_URI}")
            
        except ImportError:
            print("[MLFLOW] mlflow not installed. Run: pip install mlflow")
    
    @classmethod
    def get_client(cls):
        """Get MLflow client."""
        try:
            import mlflow
            mlflow.set_tracking_uri(cls.TRACKING_URI)
            return mlflow.tracking.MlflowClient()
        except ImportError:
            return None


def log_dna_run(
    dna: list,
    metrics: Dict[str, float],
    generation: int = 0,
    tags: Optional[Dict[str, str]] = None,
    artifacts: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Log a DNA evolution run to MLflow.
    
    Args:
        dna: DNA values [gene1, gene2, ...]
        metrics: {"sharpe": x, "pnl": y, "max_dd": z, ...}
        generation: Evolution generation number
        tags: Additional tags {"lab": "blackjack", ...}
        artifacts: Files to log {"equity_curve.csv": dataframe, ...}
    
    Returns:
        Run ID if successful, None otherwise
    """
    try:
        import mlflow
        
        MLflowConfig.setup()
        
        with mlflow.start_run() as run:
            # Log DNA as parameters
            for i, gene in enumerate(dna):
                mlflow.log_param(f"dna_{i}", gene)
            
            mlflow.log_param("dna_full", str(dna))
            mlflow.log_param("generation", generation)
            
            # Log metrics
            for name, value in metrics.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(name, value)
            
            # Log tags
            if tags:
                for key, value in tags.items():
                    mlflow.set_tag(key, value)
            
            # Log artifacts
            if artifacts:
                import tempfile
                with tempfile.TemporaryDirectory() as tmpdir:
                    for name, data in artifacts.items():
                        path = Path(tmpdir) / name
                        if hasattr(data, "to_csv"):
                            data.to_csv(path, index=False)
                        elif hasattr(data, "to_json"):
                            data.to_json(path)
                        else:
                            with open(path, "w") as f:
                                f.write(str(data))
                        mlflow.log_artifact(str(path))
            
            return run.info.run_id
            
    except ImportError:
        print("[MLFLOW] mlflow not installed")
        return None
    except Exception as e:
        print(f"[MLFLOW] Error logging run: {e}")
        return None


def register_production_dna(
    run_id: str,
    model_name: str = "production-dna",
    stage: str = "Production"
) -> bool:
    """
    Register a DNA configuration to the Model Registry.
    
    Args:
        run_id: MLflow run ID containing the DNA
        model_name: Registry model name
        stage: Model stage (Staging, Production, Archived)
    
    Returns:
        True if successful
    """
    try:
        import mlflow
        from mlflow.tracking import MlflowClient
        
        MLflowConfig.setup()
        client = MlflowClient()
        
        # Create or get model
        try:
            client.create_registered_model(model_name)
        except Exception:
            pass  # Already exists
        
        # Create version from run
        model_uri = f"runs:/{run_id}/dna"
        version = mlflow.register_model(model_uri, model_name)
        
        # Transition to stage
        client.transition_model_version_stage(
            name=model_name,
            version=version.version,
            stage=stage
        )
        
        print(f"[MLFLOW] Registered {model_name} v{version.version} -> {stage}")
        return True
        
    except Exception as e:
        print(f"[MLFLOW] Registration error: {e}")
        return False


def get_production_dna(model_name: str = "production-dna") -> Optional[list]:
    """
    Get the current production DNA from Model Registry.
    
    Returns:
        DNA list or None if not found
    """
    try:
        import mlflow
        from mlflow.tracking import MlflowClient
        
        MLflowConfig.setup()
        client = MlflowClient()
        
        # Get production version
        versions = client.get_latest_versions(model_name, stages=["Production"])
        if not versions:
            return None
        
        # Get run
        run = client.get_run(versions[0].run_id)
        
        # Extract DNA from params
        dna_str = run.data.params.get("dna_full", "[]")
        dna = eval(dna_str)  # Safe since we control the data
        
        return dna
        
    except Exception as e:
        print(f"[MLFLOW] Error getting production DNA: {e}")
        return None


def compare_runs(
    experiment_name: str = "godbrain-genetics",
    metric: str = "sharpe",
    top_n: int = 10
) -> list:
    """
    Get top runs by metric.
    
    Returns:
        List of (run_id, dna, metrics) tuples
    """
    try:
        import mlflow
        
        MLflowConfig.setup(experiment_name)
        
        runs = mlflow.search_runs(
            experiment_names=[experiment_name],
            order_by=[f"metrics.{metric} DESC"],
            max_results=top_n
        )
        
        results = []
        for _, row in runs.iterrows():
            dna_str = row.get("params.dna_full", "[]")
            try:
                dna = eval(dna_str)
            except:
                dna = []
            
            metrics = {
                col.replace("metrics.", ""): row[col]
                for col in runs.columns
                if col.startswith("metrics.")
            }
            
            results.append({
                "run_id": row["run_id"],
                "dna": dna,
                "metrics": metrics,
            })
        
        return results
        
    except Exception as e:
        print(f"[MLFLOW] Error comparing runs: {e}")
        return []


if __name__ == "__main__":
    print("MLflow Setup Demo")
    print("=" * 50)
    
    # Initialize
    MLflowConfig.setup()
    
    # Demo log
    run_id = log_dna_run(
        dna=[10, 10, 242, 331, 354, 500],
        metrics={
            "sharpe": 1.5,
            "pnl": 1234.56,
            "max_dd": 0.12,
            "win_rate": 0.55,
        },
        generation=42,
        tags={"lab": "blackjack", "version": "v4.6"}
    )
    
    if run_id:
        print(f"[DEMO] Logged run: {run_id}")
        print(f"[DEMO] View at: mlflow ui --port 5001")
