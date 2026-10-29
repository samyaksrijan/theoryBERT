"""Package only the activated inference assets, preserving every weight byte."""
from pathlib import Path
import argparse,gzip,hashlib,json,shutil,tarfile
ROOT=Path(__file__).resolve().parents[1]
TAG='bert-plan-2026-10-29'
NAME='theorybert-bert-plan-2026-10-29.tar.gz'

def sha(path):
 with path.open('rb') as handle:return hashlib.file_digest(handle,'sha256').hexdigest()

class DigestSink:
 def __init__(self):self.checksum=hashlib.sha256();self.size=0
 def write(self,data):self.checksum.update(data);self.size+=len(data);return len(data)
 def flush(self):pass

def archive_to(stream,files):
 with gzip.GzipFile(filename="",mode="wb",fileobj=stream,compresslevel=1,mtime=0) as zipped,tarfile.open(fileobj=zipped,mode="w|") as archive:
  for path in files:
   info=archive.gettarinfo(str(path),arcname=path.relative_to(ROOT).as_posix())
   info.uid=info.gid=0;info.uname=info.gname="";info.mtime=0;info.mode=0o644
   with path.open("rb") as handle:archive.addfile(info,handle)

def main():
 parser=argparse.ArgumentParser();parser.add_argument("--manifest-only",action="store_true");args=parser.parse_args()
 destination=ROOT/'artifacts/releases'/NAME
 destination.parent.mkdir(parents=True,exist_ok=True)
 if not args.manifest_only and shutil.disk_usage(ROOT).free < 3.6*2**30:raise RuntimeError('Keep at least 3.6 GiB free before packaging, or use --manifest-only for streamed publication.')
 files=list((ROOT/'artifacts/bert-v3/best').rglob('*'))
 for folder,names in {
  'artifacts/bert-plan/best':['config.json','head.pt','summary.json'],
  'artifacts/grammar-robust':['config.json','head.pt','summary.json'],
  'artifacts':['active-model.json','active-grammar.json','challenge-comparison.json','v3-comparison.json'],
  'artifacts/plan-comparison':['summary.json'],
  'artifacts/bert-v3':['summary.json'],
  'artifacts/pretrained/bert-base-uncased':['source.json','LICENSE','README.md'],
 }.items():files.extend(ROOT/folder/name for name in names)
 files=sorted({p for p in files if p.is_file()})
 records=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]
 sink=DigestSink()
 if args.manifest_only:archive_to(sink,files)
 else:
  with destination.open('wb') as stream:archive_to(stream,files)
  sink.size=destination.stat().st_size
  sink.checksum=None
 manifest={'version':TAG,'url':f'https://github.com/samyaksrijan/theoryBERT/releases/download/{TAG}/{NAME}','bytes':sink.size,'sha256':sink.checksum.hexdigest() if args.manifest_only else sha(destination),'unpacked_bytes':sum(r['bytes'] for r in records),'precision':'Original evaluated FP32 weights, no quantization or retraining','files':records}
 (ROOT/'deploy/model-bundle.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps({k:v for k,v in manifest.items() if k!='files'},indent=2))
 print('Files:',len(records))
if __name__=='__main__':main()
