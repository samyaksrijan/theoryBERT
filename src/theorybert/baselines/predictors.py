import re
from typing import Protocol
from theorybert.data.generators import pattern_dfa, modulo_dfa


class Predictor(Protocol):
    source: str

    def predict(self, description: str, budget: int = 5): ...


class RuleBased:
    source = "Rule-based baseline (limited patterns)"

    def predict(self, description, budget=5):
        text = description.lower().strip().rstrip(".")
        m = re.fullmatch(
            r"binary strings that (start with|end in|contain) ([01]+)", text
        )
        if m:
            return iter(
                [
                    pattern_dfa(
                        m[2],
                        {
                            "start with": "starts",
                            "end in": "ends",
                            "contain": "contains",
                        }[m[1]],
                    )
                ]
            )
        m = re.fullmatch(r"binary strings with an (even|odd) count of ([01])", text)
        if m:
            return iter([modulo_dfa(2, int(m[1] == "odd"), m[2])])
        raise ValueError(
            "Unsupported rule-based description. Use “Binary strings that end in 01.” or an even/odd count example."
        )


class Learned:
    def __init__(self, model, tokenizer, config):
        self.model, self.tokenizer, self.config = model, tokenizer, config
        self.source = f"{config['variant']} · {config.get('pretrained_source', config.get('backbone', 'tiny-random'))} · {config.get('training_status', 'untrained')}"

    def predict(self, description, budget=5):
        import torch
        from theorybert.models.decoding import decode_candidates

        if len(self.tokenizer.encode(description)) > self.config.get("max_length", 96):
            raise ValueError("This description exceeds the trained model's token limit. Shorten it so no requirement is silently truncated.")
        encoded = self.tokenizer(
            description,
            return_tensors="pt",
            truncation=True,
            max_length=self.config.get("max_length", 96),
        )
        device = next(self.model.parameters()).device
        encoded = {
            k: v.to(device)
            for k, v in encoded.items()
            if k in ("input_ids", "attention_mask")
        }
        with torch.inference_mode():
            out = self.model(**encoded)
        return decode_candidates(out, budget)


class OptionalLLM:
    """Explicit opt-in adapter. Caller owns networking and credentials; never automatic."""

    source = "Prompted LLM baseline (external, opt-in)"

    def __init__(self, generate=None, enabled=False):
        self.generate, self.enabled = generate, enabled

    def predict(self, description, budget=1):
        if not self.enabled or self.generate is None:
            raise ValueError(
                "LLM baseline disabled. Supply an explicitly enabled generation callable and credentials."
            )
        from theorybert.contracts import DFA, strict_json

        prompt = (
            "Return only a complete binary DFA JSON with schema_version, states, alphabet, transitions, start_state, accept_states. Request: "
            + description
        )
        return iter([DFA.from_dict(strict_json(self.generate(prompt)))])
