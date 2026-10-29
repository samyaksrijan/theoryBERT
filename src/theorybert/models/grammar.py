"""BERT language analysis with a trained direct grammar-token decoder.

No English pattern matching or grammar-library retrieval occurs at inference.
The evaluated DFA encoder is immutable; this separately evaluated production
decoder is trained on English/CFG supervision, with a bounded output vocabulary.
"""

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import random
import re
import time

import torch
from torch import nn
from nltk import CFG

from theorybert.formal.compiler import ARITHMETIC_GRAMMAR
from theorybert.models.theorybert import load_checkpoint


def grammar_tokens(text):
    return re.findall(r"'[^']*'|->|\||\n|[A-Za-z_]\w*", text)


def grammar_identity(text):
    grammar = CFG.fromstring(text)
    return str(grammar.start()), sorted(str(p) for p in grammar.productions())


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def examples():
    templates = [
        "Build a context-free grammar for {condition}.",
        "I need a CFG that generates {condition}.",
        "Construct a grammar whose language is {condition}.",
        "Generate productions for {condition}.",
        "Give the context free grammar accepting {condition}.",
        "The grammar should describe {condition}.",
        "Find a CFG for {condition}.",
        "Write grammar rules for {condition}.",
        "Create a grammar that recognizes {condition}.",
        "My language consists of {condition}. Produce a CFG.",
    ]
    for a, b in itertools.permutations("abxy01", 2):
        cases = [
            ("balanced_count", f"S -> '{a}' S '{b}' |", [f"equal numbers of {a} followed by {b}, including the empty string", f"strings of the form {a}^n {b}^n for n >= 0", f"n copies of {a} followed by n copies of {b}, where n can be zero"]),
            ("balanced_delimiters", f"S -> '{a}' S '{b}' S |", [f"balanced nested delimiters with opening {a} and closing {b}", f"well-balanced parentheses using {a} to open and {b} to close", f"arbitrarily nested and concatenated matching {a} and {b} brackets"]),
            ("ordered_blocks", f"S -> '{a}' S | B\nB -> '{b}' B |", [f"zero or more {a} symbols followed by zero or more {b} symbols", f"strings of the form {a}*{b}*", f"all {a} symbols before all {b} symbols, either block possibly empty"]),
        ]
        if a < b:
            cases += [
                ("palindrome", f"S -> '{a}' S '{a}' | '{b}' S '{b}' | '{a}' | '{b}' |", [f"palindromes over the alphabet {{{a},{b}}}, including the empty string", f"strings over {a} and {b} that read the same forwards and backwards", f"all even and odd length palindromes using symbols {a} and {b}"]),
                ("all_words", f"S -> '{a}' S | '{b}' S |", [f"all strings over alphabet {{{a},{b}}}, including the empty word", f"any sequence of {a} and {b} symbols", f"arbitrary words made from {a} and {b}, allowing empty input"]),
            ]
        for family, grammar, descriptions in cases:
            for i, template in enumerate(templates):
                yield family, grammar, template.format(condition=descriptions[i % len(descriptions)])
    constants = [
        ("arithmetic", "E -> E '+' T | T\nT -> T '*' F | F\nF -> '(' E ')' | 'id'", ["arithmetic expressions with identifiers, plus and multiplication, using standard precedence", "expressions using id, +, *, and parentheses with multiplication before addition", "addition and multiplication of identifiers with parentheses and normal operator precedence"]),
        ("ambiguous", "E -> E '+' E | 'id'", ["ambiguous expressions with id and addition and no operator associativity", "identifier additions using the ambiguous rule E expands to E plus E or id", "addition expressions with identifiers and every possible binary grouping"]),
        ("expression_compiler", ARITHMETIC_GRAMMAR, ["arithmetic expressions with identifiers and numbers, plus, minus, multiplication, division, parentheses, and unary signs; use standard precedence and left associativity", "numeric and identifier expressions with + - * / parentheses and unary plus or minus, using normal precedence", "arithmetic with id and num, binary addition subtraction multiplication division, unary signs, parentheses, and left associative operators"]),
    ]
    for family, grammar, descriptions in constants:
        for template in templates:
            for description in descriptions:
                yield family, grammar, template.format(condition=description)
        for description in descriptions:
            yield family, grammar, description.capitalize() + "."


class GrammarHead(nn.Module):
    def __init__(self, hidden_size, length, vocabulary):
        super().__init__()
        self.length, self.vocabulary = length, vocabulary
        self.projection = nn.Linear(hidden_size, 128)
        self.queries = nn.Parameter(torch.randn(length, 128) * .02)
        self.decoder = nn.TransformerDecoder(nn.TransformerDecoderLayer(128, 4, 256, .1, batch_first=True), 2)
        self.output = nn.Linear(128, vocabulary)
        self.bias = nn.Parameter(torch.zeros(length, vocabulary))

    def forward(self, features, mask=None):
        memory = self.projection(features)
        queries = self.queries.unsqueeze(0).expand(len(features), -1, -1)
        decoded = self.decoder(queries, memory, memory_key_padding_mask=~mask.bool() if mask is not None else None)
        return self.output(decoded) + self.bias


class GrammarPredictionError(ValueError):
    kind = "MODEL_OUTPUT_INVALID"

    def __init__(self, message, candidate):
        super().__init__(message)
        self.candidate_grammar = candidate


class GrammarPredictor:
    def __init__(self, path, encoder=None):
        path = Path(path)
        self.config = json.loads((path / "config.json").read_text())
        encoder_path = Path(self.config["encoder_checkpoint"])
        if file_sha256(encoder_path / "weights.pt") != self.config["encoder_weights_sha256"]:
            raise ValueError("The grammar decoder belongs to different BERT weights. Retrain it for this encoder; no fallback is used.")
        if encoder is None:
            encoder = load_checkpoint(self.config["encoder_checkpoint"])[:2]
        self.model, self.tokenizer = encoder
        self.head = GrammarHead(self.config["hidden_size"], self.config["length"], len(self.config["vocabulary"]))
        self.head.load_state_dict(torch.load(path / "head.pt", weights_only=True, map_location="cpu"))
        self.head.eval()
        self.source = "BERT language encoder · learned grammar-production decoder"

    def predict(self, description):
        if not description.strip() or len(self.tokenizer.encode(description)) > self.config["max_length"]:
            raise ValueError("Describe the grammar in 1–64 BERT tokens; no requirement will be silently truncated.")
        encoded = self.tokenizer(description, return_tensors="pt")
        encoded = {k: v for k, v in encoded.items() if k in ("input_ids", "attention_mask")}
        with torch.inference_mode():
            features = self.model(**encoded)["token_features"]
            ids = self.head(features, encoded["attention_mask"]).argmax(-1)[0].tolist()
        vocabulary, tokens = self.config["vocabulary"], []
        for index in ids:
            token = vocabulary[index]
            if token == "<EOS>":
                break
            if token == "<PAD>":
                raise GrammarPredictionError("BERT produced an incomplete grammar. Refine the description; no reference grammar was substituted.", " ".join(tokens))
            tokens.append(token)
        else:
            raise GrammarPredictionError("BERT grammar exceeded its output-token budget.", " ".join(tokens))
        grammar = " ".join(tokens)
        try:
            grammar_identity(grammar)
        except (ValueError, IndexError) as exc:
            raise GrammarPredictionError("BERT produced a malformed grammar. Refine the description; no template or rule fallback was used.", grammar) from exc
        return grammar


def train(encoder_checkpoint, output, extra_dataset=None, initialize=None, epochs=200, patience=25):
    from theorybert.training.resources import ResourceGuard
    torch.set_num_threads(2)
    torch.manual_seed(42)
    random.seed(42)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    guard = ResourceGuard(output, min_disk_gb=2, max_swap_growth_gb=.75)
    rows = []
    for family, grammar, description in examples():
        language = hashlib.sha256(json.dumps(grammar_identity(grammar)).encode()).hexdigest()
        bucket = int(language[:8], 16) % 100
        split = "train" if family in ("arithmetic", "ambiguous", "expression_compiler") or bucket < 75 else "validation" if bucket < 88 else "test"
        rows.append({"family": family, "grammar": grammar, "description": description, "language_id": language, "split": split})
    if extra_dataset:
        extra = [json.loads(line) for line in Path(extra_dataset).read_text().splitlines() if line.strip()]
        from theorybert.data.challenges import grammar_key
        protected = {grammar_key(r["grammar"]): r["split"] for r in extra if r["split"] != "train"}
        challenge_path = Path("data/challenges/toc-compiler-v1.jsonl")
        challenge_rows = [json.loads(line) for line in challenge_path.read_text().splitlines()]
        heldout = {r["description"] for r in challenge_rows if r["partition"] != "development"}
        for row in challenge_rows:
            if row["mode"] == "cfg" and row["partition"] != "development":
                protected[grammar_key(row["gold_grammar"])] = row["partition"]
        rows = [r for r in rows if r["split"] != "train" or grammar_key(r["grammar"]) not in protected]
        rows.extend(extra)
        assert not {r["description"] for r in rows if r["split"] == "train"} & heldout
        roles = {}
        for row in rows:
            key = grammar_key(row["grammar"])
            if key in roles and roles[key] != row["split"]:
                raise ValueError("A grammar label crosses training/validation/test partitions")
            roles[key] = row["split"]
    (output / "dataset.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    vocab = ["<PAD>", "<EOS>"] + sorted({t for r in rows for t in grammar_tokens(r["grammar"])})
    length = max(len(grammar_tokens(r["grammar"])) + 1 for r in rows)
    model, tokenizer, base_config = load_checkpoint(encoder_checkpoint)
    model.eval()
    texts = [r["description"] for r in rows]
    if any(len(tokenizer.encode(t)) > 64 for t in texts):
        raise ValueError("Grammar training data would be truncated.")
    features = []
    encoded_all = tokenizer(texts, padding=True, return_tensors="pt")
    masks = encoded_all["attention_mask"]
    started = time.perf_counter()
    with torch.inference_mode():
        for start in range(0, len(rows), 8):
            encoded = {k: v[start:start+8] for k, v in encoded_all.items() if k in ("input_ids", "attention_mask")}
            features.append(model(**encoded)["token_features"].half().clone())
            if start % 160 == 0:
                guard.check("BERT grammar encoding")
                print(json.dumps({"phase": "BERT_grammar_features", "done": start+len(features[-1]), "total": len(rows)}), flush=True)
    features = torch.cat(features).clone()
    hidden_size = features.shape[-1]
    del model
    targets = torch.zeros(len(rows), length, dtype=torch.long)
    for i, row in enumerate(rows):
        ids = [vocab.index(t) for t in grammar_tokens(row["grammar"])] + [1]
        targets[i, :len(ids)] = torch.tensor(ids)
    head = GrammarHead(hidden_size, length, len(vocab))
    if initialize:
        previous = json.loads((Path(initialize) / "config.json").read_text())
        if previous["vocabulary"] != vocab or previous["length"] != length:
            raise ValueError("Grammar warm-start output schema differs")
        head.load_state_dict(torch.load(Path(initialize) / "head.pt", weights_only=True, map_location="cpu"))
    optimizer = torch.optim.AdamW(head.parameters(), lr=.0004 if initialize else .001, weight_decay=.001)
    splits = {s: [i for i, r in enumerate(rows) if r["split"] == s] for s in ("train", "validation", "test")}
    def measure(ids):
        head.eval()
        with torch.no_grad():
            logits = head(features[ids].float(), masks[ids])
            loss = nn.functional.cross_entropy(logits.flatten(0, 1), targets[ids].flatten(), ignore_index=0)
            predictions = logits.argmax(-1)
            exact = (((predictions == targets[ids]) | (targets[ids] == 0)).all(-1)).float().mean().item()
        return float(loss), exact
    best, stale, history = (-1, float('-inf')), 0, []
    for epoch in range(epochs):
        head.train()
        random.shuffle(splits["train"])
        for start in range(0, len(splits["train"]), 32):
            ids = splits["train"][start:start+32]
            optimizer.zero_grad(set_to_none=True)
            logits = head(features[ids].float(), masks[ids])
            loss = nn.functional.cross_entropy(logits.flatten(0, 1), targets[ids].flatten(), ignore_index=0)
            loss.backward()
            nn.utils.clip_grad_norm_(head.parameters(), 1)
            optimizer.step()
        val_loss, exact = measure(splits["validation"])
        history.append({"epoch": epoch, "validation_loss": val_loss, "validation_exact_tokens": exact})
        if (exact, -val_loss) > best:
            best, stale = (exact, -val_loss), 0
            torch.save(head.state_dict(), output / "head.pt")
        else:
            stale += 1
        if epoch % 10 == 0:
            guard.check("grammar decoder training", reserve_gb=.1)
            print(json.dumps(history[-1]), flush=True)
        if stale >= patience:
            break
    head.load_state_dict(torch.load(output / "head.pt", weights_only=True))
    test_loss, test_exact = measure(splits["test"])
    config = {"architecture": "two-layer cross-attention production decoder over BERT token features", "encoder_checkpoint": str(encoder_checkpoint), "encoder_weights_sha256": file_sha256(Path(encoder_checkpoint) / "weights.pt"), "encoder_dataset_sha256": base_config["dataset_sha256"], "hidden_size": hidden_size, "length": length, "vocabulary": vocab, "max_length": 64, "training_status": "trained grammar production decoder over immutable fine-tuned pretrained BERT features"}
    config.update(dataset_sha256=file_sha256(output / "dataset.jsonl"), extra_dataset=str(extra_dataset) if extra_dataset else None, extra_dataset_sha256=file_sha256(extra_dataset) if extra_dataset else None, initial_decoder=str(initialize) if initialize else None)
    (output / "config.json").write_text(json.dumps(config, indent=2))
    summary = {"examples": len(rows), "unique_grammars": len({r["language_id"] for r in rows}), "splits": {s: len(ids) for s, ids in splits.items()}, "test_production_token_exact": test_exact, "test_loss": test_loss, "best_validation_token_exact": best[0], "seconds": time.perf_counter()-started, "selection": "validation exact production tokens then loss; test used only after selection", "scope": "Generated balanced counts/delimiters, palindromes, arbitrary words and ordered blocks over six supported terminal symbols. Arithmetic grammars are training fixtures, not held-out accuracy evidence. Grammar equivalence to arbitrary English is unverified; the parser independently checks individual derivations."}
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    (output / "history.json").write_text(json.dumps(history, indent=2))
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--encoder", default="artifacts/bert-v3/best")
    parser.add_argument("--output", default="artifacts/bert-grammar")
    parser.add_argument("--extra-dataset")
    parser.add_argument("--initialize")
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--patience", type=int, default=25)
    args = parser.parse_args()
    train(args.encoder, args.output, args.extra_dataset, args.initialize, args.epochs, args.patience)
