import hashlib
import json

import pytest
import torch

from theorybert.models.grammar import GrammarHead, GrammarPredictor, grammar_identity, grammar_tokens


def predictor_fixture(tmp_path, grammar):
    encoder = tmp_path / "encoder"
    encoder.mkdir()
    (encoder / "weights.pt").write_bytes(b"fixture encoder identity")
    vocab = ["<PAD>", "<EOS>"] + sorted(set(grammar_tokens(grammar)))
    ids = [vocab.index(t) for t in grammar_tokens(grammar)] + [1]
    head = GrammarHead(4, len(ids), len(vocab))
    with torch.no_grad():
        for p in head.parameters():
            p.zero_()
        for position, index in enumerate(ids):
            head.bias[position, index] = 10
    torch.save(head.state_dict(), tmp_path / "head.pt")
    (tmp_path / "config.json").write_text(json.dumps({"encoder_checkpoint": str(encoder), "encoder_weights_sha256": hashlib.sha256((encoder / "weights.pt").read_bytes()).hexdigest(), "hidden_size": 4, "length": len(ids), "vocabulary": vocab, "max_length": 64}))
    calls = []
    class Encoder:
        def __call__(self, **encoded):
            calls.append(encoded)
            return {"token_features": torch.zeros(1, 3, 4)}
    class Tokenizer:
        def encode(self, text):
            return text.split()
        def __call__(self, text, **kwargs):
            return {"input_ids": torch.ones(1, 3, dtype=torch.long), "attention_mask": torch.ones(1, 3, dtype=torch.long)}
    return GrammarPredictor(tmp_path, (Encoder(), Tokenizer())), calls


def test_grammar_tokens_come_from_neural_decoder_after_encoder_analysis(tmp_path):
    predictor, calls = predictor_fixture(tmp_path, "S -> 'a' S 'b' |")
    result = predictor.predict("Make a grammar for equal counts of a then b")
    assert grammar_identity(result) == grammar_identity("S -> 'a' S 'b' |")
    assert len(calls) == 1


def test_bad_generated_grammar_fails_without_template_substitution(tmp_path):
    predictor, calls = predictor_fixture(tmp_path, "S 'a'")
    with pytest.raises(ValueError, match="no template or rule fallback") as rejected:
        predictor.predict("A grammar request")
    assert rejected.value.candidate_grammar == "S 'a'"
    assert len(calls) == 1
