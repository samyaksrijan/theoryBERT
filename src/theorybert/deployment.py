"""Install a versioned, hash-checked model bundle without training or fallback."""
import hashlib,json,re,shutil,ssl,tarfile,tempfile
from pathlib import Path,PurePosixPath
from urllib.request import urlopen


def read_manifest(path):
    manifest=json.loads(Path(path).read_text())
    if not manifest.get('files') or len(manifest['files'])>100:
        raise ValueError('Invalid model bundle file inventory.')
    seen=set()
    for record in manifest['files']:
        path=PurePosixPath(record['path'])
        if path.is_absolute() or '..' in path.parts or '\\' in record['path'] or not path.parts or path.parts[0]!='artifacts' or path.as_posix()!=record['path'] or record['path'] in seen:
            raise ValueError('Unsafe or duplicate bundle path.')
        seen.add(record['path'])
        if record['bytes']<0 or record['bytes']>600*2**20 or not re.fullmatch('[0-9a-f]{64}',record['sha256']):
            raise ValueError('Invalid bundle member size or fingerprint.')
    if sum(r['bytes'] for r in manifest['files'])!=manifest['unpacked_bytes']:
        raise ValueError('Bundle size inventory mismatch.')
    return manifest


def digest(path):
    with Path(path).open('rb') as handle:return hashlib.file_digest(handle,'sha256').hexdigest()


def install_archive(archive_path,manifest,root):
    archive_path=Path(archive_path);root=Path(root).resolve()
    if archive_path.stat().st_size!=manifest['bytes'] or digest(archive_path)!=manifest['sha256']:
        raise ValueError('Model archive fingerprint or size differs from the pinned manifest.')
    expected={r['path']:r for r in manifest['files']};seen=set()
    for name in expected:
        path=PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0]!='artifacts' or '\\' in name:
            raise ValueError('Unsafe model bundle destination.')
        if not (root/name).resolve().is_relative_to(root):
            raise ValueError('Model bundle destination escapes the installation root.')
    with tarfile.open(archive_path,'r:gz') as archive:
        for member in archive:
            if not member.isfile() or member.name not in expected or member.name in seen:
                raise ValueError('Unexpected, duplicate or unsafe model archive member.')
            record=expected[member.name]
            if member.size!=record['bytes']:raise ValueError('Model member size differs from inventory.')
            destination=root/member.name
            destination.parent.mkdir(parents=True,exist_ok=True)
            partial=destination.with_name(destination.name+'.installing')
            try:
                source=archive.extractfile(member)
                checksum=hashlib.sha256();written=0
                if partial.is_symlink():raise ValueError('Unsafe partial model destination.')
                with source,partial.open('wb') as target:
                    while chunk:=source.read(1024*1024):
                        written+=len(chunk)
                        if written>record['bytes']:raise ValueError('Model member exceeded its size budget.')
                        checksum.update(chunk);target.write(chunk)
                if written!=record['bytes'] or checksum.hexdigest()!=record['sha256']:
                    raise ValueError('Model member fingerprint differs from inventory.')
                partial.replace(destination)
            finally:partial.unlink(missing_ok=True)
            seen.add(member.name)
    if seen!=set(expected):raise ValueError('Model archive is incomplete.')
    return len(seen)


def install_bundle(manifest_path,root,archive_path=None):
    manifest=read_manifest(manifest_path);root=Path(root).resolve()
    root.mkdir(parents=True,exist_ok=True)
    # Full model download + extraction is bounded; never use training artifacts.
    needed=manifest['unpacked_bytes']+(0 if archive_path else manifest['bytes'])
    if shutil.disk_usage(root).free < needed+512*2**20:
        raise RuntimeError('Not enough free disk for the verified inference bundle.')
    if archive_path:return install_archive(archive_path,manifest,root)
    url=manifest['url']
    if not url.startswith('https://github.com/samyaksrijan/theoryBERT/releases/download/'):
        raise ValueError('Model downloads must use the configured project release.')
    context=ssl.create_default_context()
    try:
        import certifi
        context=ssl.create_default_context(cafile=certifi.where())
    except ImportError:pass
    with tempfile.TemporaryDirectory(prefix='theorybert-download-') as temporary:
        archive=Path(temporary)/'model.tar.gz'
        with urlopen(url,timeout=180,context=context) as response,archive.open('wb') as target:
            written=0
            while chunk:=response.read(1024*1024):
                written+=len(chunk)
                if written>manifest['bytes']:raise ValueError('Model download exceeded its pinned size.')
                target.write(chunk)
        return install_archive(archive,manifest,root)
