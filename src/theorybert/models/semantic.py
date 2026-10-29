"""BERT semantic plans with learned literal-span copying and typed decoding."""

import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import time

import numpy as np
import torch
from torch import nn

from theorybert.formal.plan import LanguagePlan, SCHEMA, compile_plan
from theorybert.models.grammar import file_sha256
from theorybert.models.theorybert import load_checkpoint
from theorybert.training.resources import ResourceGuard

VOCAB = ["<PAD>", "<EOS>", "COPY", "P0", "P1", "S0", "S1"] + [f"N{i}" for i in range(17)] + list(SCHEMA)
MAX_PLAN_LENGTH = 24


def pattern_spans(text, offsets):
    result = []
    for start, (a, b) in enumerate(offsets):
        if a == b or (a and text[a-1] in "01"):
            continue
        for end in range(start, min(len(offsets), start+12)):
            c, d = offsets[end]
            if c == d or d <= a:
                continue
            value = text[a:d]
            if len(value) > 32:
                break
            if not set(value) - set("01") and (d == len(text) or text[d] not in "01"):
                result.append((start, end, value))
    return result


def targets(plan, text, offsets):
    tokens, starts, ends = [], [], []
    spans = pattern_spans(text, offsets)
    def emit(token, span=None):
        tokens.append(VOCAB.index(token))
        starts.append(span[0] if span else -100)
        ends.append(span[1] if span else -100)
    def visit(p):
        emit(p.op)
        for kind, arg in zip(SCHEMA[p.op], p.args):
            if kind == "expr":
                visit(arg)
            elif kind == "pattern":
                if len(arg) == 1:
                    emit("P"+arg)
                else:
                    options = [s for s in spans if s[2] == arg]
                    if not options:
                        raise ValueError(f"No token-aligned literal span for {arg!r}")
                    emit("COPY", options[0])
            elif kind == "symbol":
                emit("S"+arg)
            else:
                emit("N"+str(arg))
    visit(plan)
    emit("<EOS>")
    if len(tokens) > MAX_PLAN_LENGTH:
        raise ValueError("Plan exceeds its token budget")
    padding = MAX_PLAN_LENGTH-len(tokens)
    return tokens+[0]*padding, starts+[-100]*padding, ends+[-100]*padding


class PlanHead(nn.Module):
    def __init__(self, hidden_size=768):
        super().__init__()
        self.projection = nn.Linear(hidden_size, 128)
        self.queries = nn.Parameter(torch.randn(MAX_PLAN_LENGTH,128)*.02)
        self.decoder = nn.TransformerDecoder(nn.TransformerDecoderLayer(128,4,256,.1,batch_first=True),2)
        self.output = nn.Linear(128,len(VOCAB))
        self.start_query, self.end_query = nn.Linear(128,128), nn.Linear(128,128)

    def forward(self, features, mask):
        memory = self.projection(features)
        query = self.queries.unsqueeze(0).expand(len(features),-1,-1)
        decoded = self.decoder(query,memory,memory_key_padding_mask=~mask.bool())
        start = self.start_query(decoded) @ memory.transpose(1,2) / 128**.5
        end = self.end_query(decoded) @ memory.transpose(1,2) / 128**.5
        start = start.masked_fill(~mask.bool()[:,None,:],-1e9)
        end = end.masked_fill(~mask.bool()[:,None,:],-1e9)
        return {"tokens":self.output(decoded),"start":start,"end":end}


def parse_prefix(values):
    at = 0
    def visit():
        nonlocal at
        op = values[at]
        at += 1
        args = []
        for kind in SCHEMA[op]:
            if kind == "expr":
                args.append(visit())
            else:
                value = values[at]
                at += 1
                args.append(value)
        return LanguagePlan(op,tuple(args))
    plan = visit()
    if at != len(values):
        raise ValueError("Trailing tokens in the predicted plan")
    return plan


def decode(out, text, offsets, budget=5):
    """Bounded grammar search using only neural scores and literal types.

    There is no English keyword matching, lookup, or reference feedback. Score
    gaps, rather than unnormalised sequence likelihood, avoid short-plan bias.
    """
    logits = out["tokens"][0].detach().cpu().log_softmax(-1)
    start = out["start"][0].detach().cpu().log_softmax(-1)
    end = out["end"][0].detach().cpu().log_softmax(-1)
    spans = pattern_spans(text,offsets)
    beam, completed = [(0.0,[],[("expr",0)])], []
    for position in range(MAX_PLAN_LENGTH):
        next_beam = []
        for cost, values, stack in beam:
            if not stack:
                c = cost + float(logits[position].max()-logits[position,VOCAB.index("<EOS>")])
                try:
                    plan = parse_prefix(values)
                    machine = compile_plan(plan)
                    completed.append((c,plan,machine))
                except (ValueError, IndexError, KeyError):
                    pass
                continue
            kind, depth = stack[-1]
            remaining = stack[:-1]
            if kind == "expr":
                allowed = [op for op in SCHEMA if depth<3 or op not in ("AND","OR","NOT")]
            elif kind == "pattern":
                allowed = ["P0","P1"] + (["COPY"] if spans else [])
            elif kind == "symbol":
                allowed = ["S0","S1"]
            else:
                allowed = [f"N{i}" for i in range(17)]
            ranked = sorted(allowed,key=lambda t:float(logits[position,VOCAB.index(t)]),reverse=True)[:3]
            for token in ranked:
                penalty = float(logits[position].max()-logits[position,VOCAB.index(token)])
                if token == "COPY":
                    ranked_spans = sorted(spans,key=lambda s:float(start[position,s[0]]+end[position,s[1]]),reverse=True)[:2]
                    best_score = float(start[position,ranked_spans[0][0]]+end[position,ranked_spans[0][1]])
                    for a,b,value in ranked_spans:
                        gap = best_score-float(start[position,a]+end[position,b])
                        next_beam.append((cost+penalty+gap,values+[value],remaining))
                else:
                    value = token if kind=="expr" else int(token[1:]) if kind=="number" else token[1:]
                    tail = remaining + [(k,depth+1) for k in reversed(SCHEMA[token])] if kind=="expr" else remaining
                    next_beam.append((cost+penalty,values+[value],tail))
        beam = sorted(next_beam,key=lambda state:state[0])[:8]
        if not beam:
            break
    seen, result = set(), []
    for cost,plan,machine in sorted(completed,key=lambda v:v[0]):
        identity = json.dumps(machine.to_dict(),sort_keys=True)
        if identity in seen:
            continue
        seen.add(identity)
        result.append({"cost":cost,"plan":plan,"dfa":machine})
        if len(result)>=budget:
            break
    return result


class SemanticPredictor:
    def __init__(self, path, encoder=None):
        path = Path(path)
        self.config = json.loads((path/"config.json").read_text())
        if self.config["encoder_weights_sha256"] != file_sha256(Path(self.config["encoder_checkpoint"])/"weights.pt"):
            raise ValueError("Semantic decoder and BERT encoder fingerprints differ")
        if encoder is None:
            encoder = load_checkpoint(self.config["encoder_checkpoint"])[:2]
        self.model,self.tokenizer = encoder
        self.head = PlanHead(self.model.backbone.config.hidden_size)
        self.head.load_state_dict(torch.load(path/"head.pt",weights_only=True,map_location="cpu"))
        self.head.eval()
        self.source = "google-bert/bert-base-uncased · BERT semantic plan decoder · learned literal copying · exact DFA construction"
        self.trainable_parameters = sum(p.numel() for p in self.head.parameters())

    def predict_with_plans(self,description,budget=5):
        if not description.strip() or len(self.tokenizer.encode(description))>self.config["max_length"]:
            raise ValueError("This description exceeds the BERT plan model's input limit; no requirement is silently truncated.")
        encoded = self.tokenizer(description,return_tensors="pt",return_offsets_mapping=True)
        offsets = encoded.pop("offset_mapping")[0].tolist()
        encoded = {k:v for k,v in encoded.items() if k in ("input_ids","attention_mask")}
        with torch.inference_mode():
            features = self.model(**encoded)["token_features"]
            out = self.head(features,encoded["attention_mask"])
        predictions = decode(out,description,offsets,budget)
        if not predictions:
            raise ValueError("BERT produced no valid typed language plan within the decoding budget. No replacement machine was supplied.")
        return predictions

    def predict(self,description,budget=5):
        return iter(p["dfa"] for p in self.predict_with_plans(description,budget))


def train(dataset,output,encoder_checkpoint,epochs=60):
    torch.set_num_threads(2)
    torch.manual_seed(64)
    random.seed(64)
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    guard = ResourceGuard(output,min_disk_gb=3,max_swap_growth_gb=.75)
    records = [json.loads(l) for l in Path(dataset).read_text().splitlines()]
    # No test examples are used for gradients, selection, or training features.
    records = [r for r in records if r["split"] in ("train","validation")]
    model,tokenizer,base_config = load_checkpoint(encoder_checkpoint)
    model.eval()
    encoded = tokenizer([r["description"] for r in records],padding=True,return_tensors="pt",return_offsets_mapping=True)
    if encoded["input_ids"].shape[1]>96:
        raise ValueError("Training description exceeds the explicit 96-token limit")
    offsets = encoded.pop("offset_mapping").tolist()
    labels = [targets(LanguagePlan.from_dict(r["plan"]),r["description"],offset) for r,offset in zip(records,offsets)]
    target_tokens = torch.tensor([l[0] for l in labels])
    target_start = torch.tensor([l[1] for l in labels])
    target_end = torch.tensor([l[2] for l in labels])
    mask = encoded["attention_mask"]
    lengths = mask.sum(-1).tolist()
    boundaries = np.cumsum([0]+lengths)
    hidden_size = model.backbone.config.hidden_size
    cache = output/"features.npy"
    try:
        required = int(boundaries[-1])*hidden_size*2/2**30
        guard.check("cache_reserve", reserve_gb=required)
        hidden = np.lib.format.open_memmap(cache,mode="w+",dtype=np.float16,
                                          shape=(int(boundaries[-1]),hidden_size))
        began = time.perf_counter()
        with torch.inference_mode():
            for at in range(0,len(records),8):
                batch = {k:v[at:at+8] for k,v in encoded.items() if k in ("input_ids","attention_mask")}
                features = model(**batch)["token_features"].half().numpy()
                for j in range(len(features)):
                    index = at+j
                    hidden[boundaries[index]:boundaries[index+1]] = features[j,:lengths[index]]
                del features
                if at%400==0:
                    print(json.dumps({"phase":"BERT_features","done":at+len(batch["input_ids"]),"total":len(records),"resources":guard.check("encoding")}),flush=True)
        hidden.flush()
        del model,encoded,hidden
        hidden = np.load(cache,mmap_mode="r")
        def feature_batch(ids):
            length = max(lengths[i] for i in ids)
            features = torch.zeros(len(ids),length,hidden_size)
            for j,index in enumerate(ids):
                features[j,:lengths[index]] = torch.from_numpy(hidden[boundaries[index]:boundaries[index+1]].copy()).float()
            return features,mask[ids,:length]
        head = PlanHead(hidden_size)
        optimizer = torch.optim.AdamW(head.parameters(),lr=.001,weight_decay=.001)
        split = {s:[i for i,r in enumerate(records) if r["split"]==s] for s in ("train","validation")}
        def loss_for(out,ids):
            loss = nn.functional.cross_entropy(out["tokens"].flatten(0,1),target_tokens[ids].flatten(),ignore_index=0)
            if (target_start[ids]>=0).any():
                loss += .6*nn.functional.cross_entropy(out["start"].flatten(0,1),target_start[ids].flatten(),ignore_index=-100)
                loss += .6*nn.functional.cross_entropy(out["end"].flatten(0,1),target_end[ids].flatten(),ignore_index=-100)
            return loss
        history,best,stale = [],(-1,float("-inf")),0
        for epoch in range(epochs):
            head.train()
            random.shuffle(split["train"])
            train_loss,seen = 0,0
            for at in range(0,len(split["train"]),32):
                ids = split["train"][at:at+32]
                optimizer.zero_grad(set_to_none=True)
                out = head(*feature_batch(ids))
                loss = loss_for(out,ids)
                if not torch.isfinite(loss):
                    raise RuntimeError("Non-finite semantic plan loss")
                loss.backward()
                nn.utils.clip_grad_norm_(head.parameters(),1)
                optimizer.step()
                train_loss += float(loss.detach())*len(ids)
                seen += len(ids)
            head.eval()
            val_loss,exact,count = 0,0,0
            with torch.no_grad():
                for at in range(0,len(split["validation"]),32):
                    ids = split["validation"][at:at+32]
                    out = head(*feature_batch(ids))
                    val_loss += float(loss_for(out,ids))*len(ids)
                    predicted = out["tokens"].argmax(-1)
                    success = ((predicted==target_tokens[ids]) | (target_tokens[ids]==0)).all(-1)
                    ps,pe = out["start"].argmax(-1),out["end"].argmax(-1)
                    for j,index in enumerate(ids):
                        if not success[j]:
                            continue
                        good = True
                        for pos in (target_start[index]>=0).nonzero().flatten().tolist():
                            a,b = int(ps[j,pos]),int(pe[j,pos])
                            actual = records[index]["description"][offsets[index][a][0]:offsets[index][b][1]] if a<=b else ""
                            gold = records[index]["description"][offsets[index][int(target_start[index,pos])][0]:offsets[index][int(target_end[index,pos])][1]]
                            good &= actual==gold
                        exact += good
                    count += len(ids)
            log = {"epoch":epoch,"train_loss":train_loss/seen,"validation_loss":val_loss/count,"validation_plan_and_copy_exact":exact/count,"seconds":time.perf_counter()-began}
            history.append(log)
            score = (log["validation_plan_and_copy_exact"],-log["validation_loss"])
            if score>best:
                best,stale = score,0
                torch.save(head.state_dict(),output/"head.pt")
            else:
                stale += 1
            if epoch%5==0:
                print(json.dumps({**log,"resources":guard.check("training")}),flush=True)
            if stale>=10:
                break
        config = {"kind":"semantic_plan","variant":"BERT semantic plan","backbone":base_config["backbone"],"pretrained_source":base_config["pretrained_source"],"encoder_checkpoint":str(encoder_checkpoint),"encoder_weights_sha256":file_sha256(Path(encoder_checkpoint)/"weights.pt"),"max_length":96,"max_states":64,"dataset_sha256":file_sha256(dataset),"training_status":"trained semantic decoder over immutable evaluated pretrained BERT token features","schema_version":"plan-1","vocabulary":VOCAB}
        (output/"config.json").write_text(json.dumps(config,indent=2))
        summary = {"examples":len(records),"splits":{s:len(ids) for s,ids in split.items()},"trainable_parameters":sum(p.numel() for p in head.parameters()),"encoder_updated":False,"best_validation_plan_and_copy_exact":best[0],"training_seconds":time.perf_counter()-began,"dataset_sha256":config["dataset_sha256"],"architecture":"Frozen evaluated BERT, two 128-wide cross-attention decoder layers, token head and learned literal start/end pointers, typed prefix-plan decoding and formal DFA compilation","resources":guard.check("complete")}
        (output/"history.json").write_text(json.dumps(history,indent=2))
        (output/"summary.json").write_text(json.dumps(summary,indent=2))
        del hidden
        cache.unlink()
        print(json.dumps(summary,indent=2),flush=True)
    finally:
        cache.unlink(missing_ok=True)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset",default="data/generated/english-plan-v1.jsonl")
    parser.add_argument("--output",default="artifacts/bert-plan/best")
    parser.add_argument("--encoder",default="artifacts/bert-v3/best")
    parser.add_argument("--epochs",type=int,default=60)
    args = parser.parse_args()
    train(args.dataset,args.output,args.encoder,args.epochs)
