# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN NEURAL CORTEX
The brain of the cyber organism - LSTM/Transformer for price prediction.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    print("⚠️ PyTorch not installed. Neural features disabled.")


ROOT = Path(__file__).parent.parent


# =============================================================================
# NEURAL NETWORK ARCHITECTURES
# =============================================================================

if HAS_TORCH:
    
    class PriceLSTM(nn.Module):
        """
        LSTM network for price prediction.
        
        Input: Sequence of [open, high, low, close, volume]
        Output: Predicted next close price
        """
        
        def __init__(
            self,
            input_size: int = 5,
            hidden_size: int = 128,
            num_layers: int = 2,
            dropout: float = 0.2
        ):
            super().__init__()
            
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            
            self.lstm = nn.LSTM(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0
            )
            
            self.fc = nn.Sequential(
                nn.Linear(hidden_size, 64),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(64, 1)
            )
        
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # x shape: (batch, seq_len, features)
            lstm_out, _ = self.lstm(x)
            # Take last timestep
            last_hidden = lstm_out[:, -1, :]
            return self.fc(last_hidden)
    
    
    class PriceTransformer(nn.Module):
        """
        Transformer network for price prediction.
        More powerful than LSTM for capturing long-range dependencies.
        """
        
        def __init__(
            self,
            input_size: int = 5,
            d_model: int = 64,
            nhead: int = 4,
            num_layers: int = 2,
            dropout: float = 0.1
        ):
            super().__init__()
            
            self.input_projection = nn.Linear(input_size, d_model)
            
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=nhead,
                dim_feedforward=d_model * 4,
                dropout=dropout,
                batch_first=True
            )
            
            self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
            
            self.fc = nn.Sequential(
                nn.Linear(d_model, 32),
                nn.ReLU(),
                nn.Linear(32, 1)
            )
        
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # Project input to d_model dimensions
            x = self.input_projection(x)
            # Transform
            x = self.transformer(x)
            # Take mean across sequence
            x = x.mean(dim=1)
            return self.fc(x)
    
    
    class TrendClassifier(nn.Module):
        """
        Neural network to classify market trend.
        Output: [DOWN, NEUTRAL, UP] probabilities
        """
        
        def __init__(self, input_size: int = 5, seq_len: int = 60):
            super().__init__()
            
            self.conv = nn.Sequential(
                nn.Conv1d(input_size, 32, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.MaxPool1d(2),
                nn.Conv1d(32, 64, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.MaxPool1d(2),
            )
            
            conv_out_size = seq_len // 4 * 64
            
            self.fc = nn.Sequential(
                nn.Linear(conv_out_size, 128),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(128, 3),
                nn.Softmax(dim=1)
            )
        
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # x shape: (batch, seq_len, features)
            x = x.permute(0, 2, 1)  # (batch, features, seq_len)
            x = self.conv(x)
            x = x.view(x.size(0), -1)
            return self.fc(x)


# =============================================================================
# NEURAL CORTEX - THE BRAIN
# =============================================================================

@dataclass
class NeuralPrediction:
    """Prediction from neural cortex."""
    symbol: str
    timestamp: datetime
    predicted_price: float
    confidence: float
    trend: str  # "UP", "DOWN", "NEUTRAL"
    trend_probabilities: Dict[str, float]
    horizon_minutes: int = 15


class NeuralCortex:
    """
    The neural brain of GODBRAIN.
    
    Components:
    - Price LSTM: Short-term price prediction
    - Price Transformer: Long-term price prediction  
    - Trend Classifier: Market direction
    
    Features:
    - Continuous learning from new data
    - Model checkpointing
    - Ensemble predictions
    
    Usage:
        cortex = NeuralCortex()
        cortex.load_models()
        
        prediction = cortex.predict(symbol="DOGE/USDT", data=price_data)
        print(f"Predicted: {prediction.predicted_price}, Trend: {prediction.trend}")
    """
    
    MODEL_DIR = ROOT / "models" / "neural"
    SEQUENCE_LENGTH = 60  # 60 candles input
    
    def __init__(self, device: str = "auto"):
        if not HAS_TORCH:
            raise ImportError("PyTorch required for NeuralCortex")
        
        # Auto-detect device
        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        
        # Initialize models
        self.lstm = PriceLSTM().to(self.device)
        self.transformer = PriceTransformer().to(self.device)
        self.trend_classifier = TrendClassifier(seq_len=self.SEQUENCE_LENGTH).to(self.device)
        
        # Training state
        self.lstm_optimizer = optim.Adam(self.lstm.parameters(), lr=0.001)
        self.transformer_optimizer = optim.Adam(self.transformer.parameters(), lr=0.0001)
        self.criterion = nn.MSELoss()
        
        # Stats
        self.predictions_made = 0
        self.training_steps = 0
        
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    def preprocess(self, data: np.ndarray) -> torch.Tensor:
        """
        Preprocess price data for neural network.
        
        Args:
            data: Array of shape (seq_len, 5) with [open, high, low, close, volume]
        
        Returns:
            Normalized tensor
        """
        # Normalize prices relative to first close
        price_cols = data[:, :4]
        base_price = price_cols[0, 3]  # First close
        normalized_prices = (price_cols - base_price) / base_price * 100
        
        # Normalize volume
        volume = data[:, 4:5]
        volume_mean = volume.mean()
        volume_std = volume.std() + 1e-8
        normalized_volume = (volume - volume_mean) / volume_std
        
        # Combine
        normalized = np.hstack([normalized_prices, normalized_volume])
        
        return torch.FloatTensor(normalized).unsqueeze(0).to(self.device)
    
    def predict(self, symbol: str, data: np.ndarray) -> NeuralPrediction:
        """
        Make a prediction for a symbol.
        
        Args:
            symbol: Trading symbol
            data: Price data array (seq_len, 5)
        
        Returns:
            NeuralPrediction with price and trend
        """
        self.lstm.eval()
        self.transformer.eval()
        self.trend_classifier.eval()
        
        with torch.no_grad():
            x = self.preprocess(data)
            
            # Get predictions from each model
            lstm_pred = self.lstm(x).item()
            transformer_pred = self.transformer(x).item()
            
            # Ensemble: average LSTM and Transformer
            base_price = data[-1, 3]  # Last close
            predicted_change = (lstm_pred + transformer_pred) / 2 / 100
            predicted_price = base_price * (1 + predicted_change)
            
            # Get trend probabilities
            trend_probs = self.trend_classifier(x).squeeze().cpu().numpy()
            trends = ["DOWN", "NEUTRAL", "UP"]
            trend = trends[np.argmax(trend_probs)]
            
            # Calculate confidence
            confidence = float(np.max(trend_probs))
        
        self.predictions_made += 1
        
        return NeuralPrediction(
            symbol=symbol,
            timestamp=datetime.now(),
            predicted_price=predicted_price,
            confidence=confidence,
            trend=trend,
            trend_probabilities={
                "DOWN": float(trend_probs[0]),
                "NEUTRAL": float(trend_probs[1]),
                "UP": float(trend_probs[2])
            }
        )
    
    def train_step(self, data: np.ndarray, target: float) -> float:
        """
        Single training step.
        
        Args:
            data: Input sequence
            target: Actual next price (normalized change)
        
        Returns:
            Loss value
        """
        self.lstm.train()
        self.transformer.train()
        
        x = self.preprocess(data)
        target_tensor = torch.FloatTensor([[target]]).to(self.device)
        
        # Train LSTM
        self.lstm_optimizer.zero_grad()
        lstm_pred = self.lstm(x)
        lstm_loss = self.criterion(lstm_pred, target_tensor)
        lstm_loss.backward()
        self.lstm_optimizer.step()
        
        # Train Transformer
        self.transformer_optimizer.zero_grad()
        trans_pred = self.transformer(x)
        trans_loss = self.criterion(trans_pred, target_tensor)
        trans_loss.backward()
        self.transformer_optimizer.step()
        
        self.training_steps += 1
        
        return (lstm_loss.item() + trans_loss.item()) / 2
    
    def save_models(self, tag: str = "latest"):
        """Save all models to disk."""
        save_path = self.MODEL_DIR / tag
        save_path.mkdir(parents=True, exist_ok=True)
        
        torch.save(self.lstm.state_dict(), save_path / "lstm.pt")
        torch.save(self.transformer.state_dict(), save_path / "transformer.pt")
        torch.save(self.trend_classifier.state_dict(), save_path / "trend.pt")
        
        # Save metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "predictions_made": self.predictions_made,
            "training_steps": self.training_steps,
            "device": str(self.device)
        }
        with open(save_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        print(f"💾 Models saved to {save_path}")
    
    def load_models(self, tag: str = "latest") -> bool:
        """Load models from disk."""
        load_path = self.MODEL_DIR / tag
        
        if not load_path.exists():
            print(f"⚠️ No saved models found at {load_path}")
            return False
        
        try:
            self.lstm.load_state_dict(torch.load(load_path / "lstm.pt", map_location=self.device))
            self.transformer.load_state_dict(torch.load(load_path / "transformer.pt", map_location=self.device))
            self.trend_classifier.load_state_dict(torch.load(load_path / "trend.pt", map_location=self.device))
            
            if (load_path / "metadata.json").exists():
                with open(load_path / "metadata.json") as f:
                    metadata = json.load(f)
                self.predictions_made = metadata.get("predictions_made", 0)
                self.training_steps = metadata.get("training_steps", 0)
            
            print(f"🧠 Models loaded from {load_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to load models: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cortex statistics."""
        return {
            "device": str(self.device),
            "predictions_made": self.predictions_made,
            "training_steps": self.training_steps,
            "models": {
                "lstm": sum(p.numel() for p in self.lstm.parameters()),
                "transformer": sum(p.numel() for p in self.transformer.parameters()),
                "trend_classifier": sum(p.numel() for p in self.trend_classifier.parameters())
            }
        }


# Global instance
_cortex: Optional[NeuralCortex] = None


def get_neural_cortex() -> NeuralCortex:
    """Get or create global neural cortex."""
    global _cortex
    if _cortex is None:
        _cortex = NeuralCortex()
    return _cortex


if __name__ == "__main__":
    if HAS_TORCH:
        print("Neural Cortex Demo")
        print("=" * 60)
        
        cortex = NeuralCortex()
        print(f"Device: {cortex.device}")
        print(f"Stats: {cortex.get_stats()}")
        
        # Create dummy data
        dummy_data = np.random.randn(60, 5) * 0.01 + 0.32
        dummy_data[:, 4] = np.abs(dummy_data[:, 4]) * 1000000
        
        # Make prediction
        pred = cortex.predict("DOGE/USDT", dummy_data)
        print(f"\nPrediction:")
        print(f"  Price: {pred.predicted_price:.6f}")
        print(f"  Trend: {pred.trend} ({pred.confidence:.2%})")
    else:
        print("PyTorch not installed. Run: pip install torch")
