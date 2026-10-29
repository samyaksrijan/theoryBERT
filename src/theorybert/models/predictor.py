"""Checkpoint dispatch with a shared immutable encoder for small task heads."""

import json
from pathlib import Path


def checkpoint_weights(path):
    path = Path(path)
    config = json.loads((path / 'config.json').read_text())
    return path / ('head.pt' if config.get('kind') == 'semantic_plan' else 'weights.pt')


def load_predictor(path, encoder_loader=None):
    from theorybert.baselines.predictors import Learned
    from theorybert.models.theorybert import load_checkpoint
    path = Path(path)
    config = json.loads((path / 'config.json').read_text())
    loader = encoder_loader or (lambda p: load_checkpoint(p)[:2])
    if config.get('kind') == 'semantic_plan':
        from theorybert.models.semantic import SemanticPredictor
        return SemanticPredictor(path, loader(config['encoder_checkpoint']))
    model, tokenizer = loader(path)
    return Learned(model, tokenizer, config)
