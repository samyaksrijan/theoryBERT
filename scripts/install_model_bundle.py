"""Explicit deployment installer. The demo profile never downloads a model."""
import argparse,os
from pathlib import Path
from theorybert.deployment import install_bundle

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile',choices=['demo','bert'],default=os.environ.get('THEORYBERT_RUNTIME','demo'))
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--manifest',type=Path,default=Path('deploy/model-bundle.json'))
    parser.add_argument('--archive',type=Path)
    args=parser.parse_args()
    if args.profile=='demo':print('Explicit reference-demo runtime; no neural model downloaded.')
    else:print('Installed verified inference files:',install_bundle(args.manifest,args.root,args.archive))
