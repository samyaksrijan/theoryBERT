"""exBERT-inspired residual adapter, not an exact exBERT reproduction."""

import json
import os
from contextlib import nullcontext
from pathlib import Path
import torch
from torch import nn
from torch.nn import functional as F
from transformers import AutoConfig, AutoModel, AutoTokenizer

DOMAIN_TOKENS = [
    "δ",
    "Σ",
    "ε",
    "q0",
    "q1",
    "q2",
    "DFA",
    "CFG",
    "→",
    "≡",
    "modulo",
    "nonterminal",
]


class SplitEmbedding(nn.Module):
    """Separate tables make weight decay unable to change original rows."""

    def __init__(self, original, added, copy=True):
        super().__init__()
        original = original.detach().clone() if copy else original.detach()
        added = added.detach().clone() if copy else added.detach()
        self.original = nn.Embedding.from_pretrained(original, freeze=True)
        self.extra = nn.Embedding.from_pretrained(added, freeze=False)
        self.n_original = len(original)
        self.num_embeddings = len(original) + len(added)
        self.embedding_dim = original.shape[1]

    def forward(self, ids):
        old = self.original(ids.clamp(max=self.n_original - 1))
        new = self.extra(
            (ids - self.n_original).clamp(min=0, max=self.extra.num_embeddings - 1)
        )
        return torch.where((ids >= self.n_original).unsqueeze(-1), new, old)


def extend_tokenizer(tokenizer, backbone, tokens, strategy="subword_mean", seed=42):
    original = backbone.get_input_embeddings().weight.detach()
    vocab = tokenizer.get_vocab()
    # Audit using the unmodified tokenizer, before adding anything.
    normalizer = getattr(
        getattr(tokenizer, "backend_tokenizer", None), "normalizer", None
    )
    new = list(
        dict.fromkeys(
            t
            for t in tokens
            if t not in vocab
            and (normalizer.normalize_str(t) if normalizer else t) not in vocab
        )
    )
    if not new:
        raise ValueError(
            "No new tokens to add; choose a domain vocabulary outside the original vocabulary."
        )
    decomposed = [tokenizer.encode(t, add_special_tokens=False) for t in new]
    rng = torch.Generator(device="cpu").manual_seed(seed)
    added = torch.randn(len(new), original.shape[1], generator=rng) * float(
        original.std()
    )
    audit = []
    for i, (token, ids) in enumerate(zip(new, decomposed)):
        usable = [j for j in ids if j != tokenizer.unk_token_id and j < len(original)]
        fallback = not usable
        if strategy in ("subword_mean", "subword_mean_plus_one") and usable:
            added[i] = original[usable].mean(0).cpu()
        if strategy == "subword_mean_plus_one":
            added[i] += 1.0
        if strategy not in ("random", "subword_mean", "subword_mean_plus_one"):
            raise ValueError("Unknown initialisation strategy.")
        audit.append(
            {
                "token": token,
                "original_subwords": ids,
                "random_fallback": fallback,
                "initial_norm": float(added[i].norm()),
            }
        )
    if tokenizer.add_tokens(new) != len(new):
        raise ValueError("Extension tokens must have distinct, new token IDs.")
    backbone.set_input_embeddings(SplitEmbedding(original, added.to(original.device)))
    return audit


class StructuredModel(nn.Module):
    def __init__(self, backbone, max_states=8, variant="theorybert", dropout=0.1, fine_tune_layers=0):
        super().__init__()
        self.backbone = backbone
        self.max_states, self.variant = max_states, variant
        h = backbone.config.hidden_size
        # Both variants use a frozen backbone for matched limited-resource comparisons.
        for p in backbone.parameters():
            p.requires_grad_(False)
        emb = backbone.get_input_embeddings()
        if isinstance(emb, SplitEmbedding):
            emb.extra.weight.requires_grad_(True)
        self.fine_tune_layers = fine_tune_layers
        if fine_tune_layers:
            if not hasattr(backbone, "encoder") or not 1 <= fine_tune_layers <= len(backbone.encoder.layer):
                raise ValueError("fine_tune_layers requires a supported BERT encoder.")
            for layer in backbone.encoder.layer[-fine_tune_layers:]:
                layer.requires_grad_(True)
            # Caching the immutable lower encoder requires immutable embeddings.
            backbone.embeddings.requires_grad_(False)
        self.extension = (
            nn.TransformerEncoderLayer(
                h,
                nhead=4,
                dim_feedforward=h * 2,
                dropout=dropout,
                batch_first=True,
                norm_first=True,
            )
            if variant == "theorybert"
            else nn.Identity()
        )
        self.norm = nn.LayerNorm(h)
        self.dropout = nn.Dropout(dropout)
        self.count_head = nn.Linear(h, max_states)
        self.accept_head = nn.Linear(h, max_states)
        self.transition_head = nn.Linear(h, max_states * 2 * max_states)

    def train(self, mode=True):
        super().train(mode)
        # Keep encoder dropout deterministic for full/cache parity. Autograd
        # still updates explicitly unfrozen encoder blocks or added embeddings.
        self.backbone.eval()
        return self

    def forward(self, input_ids, attention_mask, **kwargs):
        hidden = self.backbone(
            input_ids=input_ids, attention_mask=attention_mask
        ).last_hidden_state
        return self.forward_hidden(hidden, attention_mask)

    def encode_lower(self, input_ids, attention_mask):
        """Cache only frozen BERT layers; upper pretrained layers still train."""
        if not self.fine_tune_layers:
            raise ValueError("Lower-layer caching requires fine_tune_layers.")
        hidden = self.backbone.embeddings(input_ids=input_ids)
        mask = self.backbone.get_extended_attention_mask(attention_mask, input_ids.shape)
        for layer in self.backbone.encoder.layer[:-self.fine_tune_layers]:
            hidden = layer(hidden, attention_mask=mask)[0]
        return hidden

    def forward_cached(self, hidden, attention_mask):
        mask = self.backbone.get_extended_attention_mask(attention_mask, attention_mask.shape)
        for layer in self.backbone.encoder.layer[-self.fine_tune_layers:]:
            hidden = layer(hidden, attention_mask=mask)[0]
        return self.forward_hidden(hidden, attention_mask)

    def forward_hidden(self, hidden, attention_mask):
        if self.variant == "theorybert":
            hidden = hidden + self.extension(
                hidden, src_key_padding_mask=~attention_mask.bool()
            )
        pooled = self.norm(
            (hidden * attention_mask.unsqueeze(-1)).sum(1)
            / attention_mask.sum(1, keepdim=True).clamp(min=1)
        )
        pooled = self.dropout(pooled)
        b = len(hidden)
        out = {
            "token_features": hidden,
            "features": pooled,
            "count": self.count_head(pooled),
            "accept": self.accept_head(pooled),
            "transition": self.transition_head(pooled).reshape(
                b, self.max_states, 2, self.max_states
            ),
        }
        assert out["transition"].shape == (b, self.max_states, 2, self.max_states)
        return out


def targets(dfas, max_states, device):
    counts = torch.tensor([len(d.states) for d in dfas], device=device)
    if any(n > max_states for n in counts):
        raise ValueError("Target exceeds configured state bound.")
    accept = torch.zeros(len(dfas), max_states, device=device)
    trans = torch.zeros(len(dfas), max_states, 2, dtype=torch.long, device=device)
    for b, d in enumerate(dfas):
        if d.alphabet != ["0", "1"] or d.start_state != "q0":
            raise ValueError("Targets must be binary and canonical.")
        ids = {s: i for i, s in enumerate(d.states)}
        for s in d.accept_states:
            accept[b, ids[s]] = 1
        for s, row in d.transitions.items():
            for a, t in row.items():
                trans[b, ids[s], int(a)] = ids[t]
    return counts, accept, trans


def structured_loss(out, target, weights=None):
    counts, accept, trans = target
    b, m = out["accept"].shape
    active = torch.arange(m, device=counts.device)[None, :] < counts[:, None]
    logits = out["transition"].masked_fill(
        torch.arange(m, device=counts.device)[None, None, None, :]
        >= counts[:, None, None, None],
        -1e9,
    )
    losses = {
        "count": F.cross_entropy(out["count"], counts - 1),
        "accept": F.binary_cross_entropy_with_logits(
            out["accept"], accept, reduction="none"
        )[active].mean(),
        "transition": F.cross_entropy(
            logits.reshape(-1, m), trans.reshape(-1), reduction="none"
        )
        .reshape(b, m, 2)[active]
        .mean(),
    }
    total = sum(v * (weights or {}).get(k, 1.0) for k, v in losses.items())
    return total, losses


def build(config, tiny=False):
    from transformers import BertConfig, BertModel, BertTokenizerFast

    if tiny:
        vocab = Path(config["output"]) / "tiny_vocab.txt"
        vocab.parent.mkdir(parents=True, exist_ok=True)
        vocab.write_text(
            "\n".join(
                [
                    "[PAD]",
                    "[UNK]",
                    "[CLS]",
                    "[SEP]",
                    "[MASK]",
                    "binary",
                    "strings",
                    "that",
                    "end",
                    "in",
                    "0",
                    "1",
                    "count",
                    "even",
                    "of",
                    ".",
                    "with",
                    "an",
                ]
            )
        )
        tokenizer = BertTokenizerFast(vocab_file=str(vocab), do_lower_case=True)
        backbone = BertModel(
            BertConfig(
                vocab_size=len(tokenizer),
                hidden_size=32,
                num_hidden_layers=1,
                num_attention_heads=4,
                intermediate_size=64,
            )
        )
    else:
        tokenizer = AutoTokenizer.from_pretrained(
            config.get("backbone", "bert-base-uncased")
        )
        backbone = AutoModel.from_pretrained(
            config.get("backbone", "bert-base-uncased")
        )
    audit = []
    if config.get("variant", "theorybert") == "theorybert":
        audit = extend_tokenizer(
            tokenizer,
            backbone,
            config.get("domain_tokens", DOMAIN_TOKENS),
            config.get("initialisation", "subword_mean"),
            config.get("seed", 42),
        )
    model = StructuredModel(
        backbone, config.get("max_states", 8), config.get("variant", "theorybert"),
        config.get("dropout", 0.1), config.get("fine_tune_layers", 0),
    )
    return model, tokenizer, audit


def save_checkpoint(path, model, tokenizer, config, audit, optimizer=None, epoch=0):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    model.backbone.config.save_pretrained(path / "backbone_config")
    tokenizer.save_pretrained(path / "tokenizer")
    (path / "config.json").write_text(
        json.dumps(
            {**config, "schema_version": "1.0", "embedding_audit": audit}, indent=2
        )
    )
    temporary = path / "weights.pt.partial"
    torch.save(
        {
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict() if optimizer else None,
            "epoch": epoch,
        },
        temporary,
    )
    temporary.replace(path / "weights.pt")


def load_checkpoint(path, device="cpu", memory_efficient=None):
    """Load identical FP32 tensors, optionally retaining file-backed CPU storage.

    The mapped path uses meta initialization and assign=True, avoiding an
    anonymous full-model allocation and copy. It never quantizes parameters.
    """
    path = Path(path)
    config = json.loads((path / "config.json").read_text())
    if config.get("schema_version") != "1.0":
        raise ValueError("Unsupported checkpoint schema.")
    if memory_efficient is None:
        memory_efficient = os.environ.get("THEORYBERT_MMAP_WEIGHTS") == "1"
    if memory_efficient and str(device) != "cpu":
        raise ValueError("File-backed checkpoint loading requires CPU inference.")
    state = torch.load(path / "weights.pt", map_location="cpu", weights_only=True, mmap=True)
    tokenizer = AutoTokenizer.from_pretrained(path / "tokenizer", local_files_only=True)
    with torch.device("meta") if memory_efficient else nullcontext():
        backbone = AutoModel.from_config(AutoConfig.from_pretrained(path / "backbone_config", local_files_only=True))
        key = "backbone.embeddings.word_embeddings."
        if key + "original.weight" in state["model"]:
            backbone.set_input_embeddings(SplitEmbedding(
                state["model"][key + "original.weight"],
                state["model"][key + "extra.weight"], copy=not memory_efficient))
        model = StructuredModel(backbone, config["max_states"], config["variant"], config.get("dropout", 0.1), config.get("fine_tune_layers", 0))
    model.load_state_dict(state["model"], assign=bool(memory_efficient))
    if memory_efficient:
        # These BERT buffers are deliberately nonpersistent and absent from a
        # state_dict. Recreate their ordinary integer values after meta init.
        embeddings = model.backbone.embeddings
        if hasattr(embeddings, "position_ids") and embeddings.position_ids.is_meta:
            embeddings.position_ids = torch.arange(model.backbone.config.max_position_embeddings).expand((1, -1))
        if hasattr(embeddings, "token_type_ids") and embeddings.token_type_ids.is_meta:
            embeddings.token_type_ids = torch.zeros((1, model.backbone.config.max_position_embeddings), dtype=torch.long)
        if any(b.is_meta for b in model.buffers()):
            raise ValueError("Unsupported nonpersistent meta buffer in this checkpoint.")
    model.to(device).eval()
    return model, tokenizer, config
