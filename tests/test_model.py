import json
import torch
from transformers import BertConfig, BertModel
from theorybert.models.theorybert import (
    StructuredModel,
    targets,
    structured_loss,
    build,
    save_checkpoint,
    load_checkpoint,
)
from theorybert.models.decoding import decode_candidates
from theorybert.data.generators import pattern_dfa
from theorybert.formal.dfa import validate


def test_loss_padding_and_shapes():
    torch.manual_seed(42)
    model = StructuredModel(
        BertModel(
            BertConfig(
                vocab_size=20,
                hidden_size=32,
                num_hidden_layers=1,
                num_attention_heads=4,
                intermediate_size=64,
            )
        )
    )
    out = model(
        torch.tensor([[2, 3, 0], [2, 4, 5]]), torch.tensor([[1, 1, 0], [1, 1, 1]])
    )
    assert out["count"].shape == (2, 8) and out["transition"].shape == (2, 8, 2, 8)
    ds = [pattern_dfa("01"), pattern_dfa("0")]
    target = targets(ds, 8, "cpu")
    loss, _ = structured_loss(out, target)
    assert torch.isfinite(loss)
    changed = {k: v.clone() for k, v in out.items()}
    for i, d in enumerate(ds):
        changed["accept"][i, len(d.states) :] = 1000
        changed["transition"][i, len(d.states) :] = 1000
        changed["transition"][i, :, :, len(d.states) :] = 1000
    assert torch.allclose(loss, structured_loss(changed, target)[0])
    loss.backward()
    assert model.extension.linear1.weight.grad.abs().sum() > 0
    candidates = list(decode_candidates({k: v[:1] for k, v in out.items()}, budget=8))
    assert (
        len(candidates) == 8 and len({json.dumps(d.to_dict()) for d in candidates}) == 8
    )
    assert all(not validate(d) for d in candidates)


def test_frozen_updates_checkpoint(tmp_path):
    config = {
        "output": str(tmp_path),
        "variant": "theorybert",
        "max_states": 8,
        "initialisation": "subword_mean_plus_one",
        "seed": 42,
        "training_status": "tiny-random smoke",
    }
    model, tok, audit = build(config, tiny=True)
    assert all(x["initial_norm"] > 3 for x in audit)
    initial = {n: p.detach().clone() for n, p in model.named_parameters()}
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=0.01, weight_decay=0.1
    )
    encoded = tok("binary Σ δ q0", return_tensors="pt")
    encoded = {k: v for k, v in encoded.items() if k in ("input_ids", "attention_mask")}
    model.train()
    loss, _ = structured_loss(model(**encoded), targets([pattern_dfa("01")], 8, "cpu"))
    loss.backward()
    assert model.backbone.get_input_embeddings().extra.weight.grad.abs().sum() > 0
    optimizer.step()
    for n, p in model.named_parameters():
        if not p.requires_grad:
            assert torch.equal(initial[n], p)
    for prefix in (
        "backbone.embeddings.word_embeddings.extra",
        "extension.linear1",
        "count_head",
        "accept_head",
        "transition_head",
    ):
        assert any(
            n.startswith(prefix) and not torch.equal(p, initial[n])
            for n, p in model.named_parameters()
        )
    model.eval()
    save_checkpoint(tmp_path / "ckpt", model, tok, config, audit)
    restored, rtok, _ = load_checkpoint(tmp_path / "ckpt")
    with torch.no_grad():
        a = model(**encoded)
        b = restored(**encoded)
    assert all(torch.equal(a[k], b[k]) for k in a)
    assert tok.encode("Σ δ") == rtok.encode("Σ δ")


def test_first_candidate_count_is_argmax():
    # Conditional joint products must not create a bias towards one-state DFAs.
    out = {
        "count": torch.tensor([[0.0, 1.0, 2.0, 8.0]]),
        "accept": torch.zeros(1, 4),
        "transition": torch.zeros(1, 4, 2, 4),
    }
    assert len(next(decode_candidates(out, 1)).states) == 4


def test_validation_uses_configured_loss_weights(tmp_path):
    from theorybert.training.train import validation

    config = {
        "output": str(tmp_path),
        "variant": "vanilla",
        "max_states": 8,
        "max_length": 48,
    }
    model, tokenizer, _ = build(config, tiny=True)
    records = [
        {
            "description": "binary strings",
            "ground_truth_dfa": pattern_dfa("01").to_dict(),
        }
    ]
    ordinary, _ = validation(model, tokenizer, records, config, "cpu")
    zeroed, _ = validation(
        model,
        tokenizer,
        records,
        {**config, "loss_weights": {"count": 0, "accept": 0, "transition": 0}},
        "cpu",
    )
    assert ordinary > 0 and zeroed == 0


def test_distilbert_update_and_reload(tmp_path):
    from transformers import DistilBertConfig, DistilBertModel
    from theorybert.models.theorybert import extend_tokenizer

    config = {
        "output": str(tmp_path),
        "variant": "vanilla",
        "max_states": 8,
        "seed": 42,
    }
    _, tok, _ = build(config, tiny=True)
    backbone = DistilBertModel(
        DistilBertConfig(
            vocab_size=len(tok), dim=32, hidden_dim=64, n_layers=1, n_heads=4
        )
    )
    audit = extend_tokenizer(tok, backbone, ["q0", "δ"], "random")
    config.update(variant="theorybert", backbone="distilbert-base-uncased")
    model = StructuredModel(backbone)
    model.train()
    frozen = model.backbone.get_input_embeddings().original.weight.detach().clone()
    old = model.backbone.get_input_embeddings().extra.weight.detach().clone()
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=0.01
    )
    encoded = tok("q0 δ", return_tensors="pt")
    encoded = {k: v for k, v in encoded.items() if k in ("input_ids", "attention_mask")}
    loss, _ = structured_loss(model(**encoded), targets([pattern_dfa("0")], 8, "cpu"))
    loss.backward()
    optimizer.step()
    assert torch.equal(frozen, model.backbone.get_input_embeddings().original.weight)
    assert not torch.equal(old, model.backbone.get_input_embeddings().extra.weight)
    model.eval()
    save_checkpoint(tmp_path / "distil", model, tok, config, audit)
    restored, _, _ = load_checkpoint(tmp_path / "distil")
    with torch.no_grad():
        a, b = model(**encoded), restored(**encoded)
    assert all(torch.equal(a[k], b[k]) for k in a)
