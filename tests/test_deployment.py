import hashlib,io,json,tarfile
from pathlib import Path
import pytest
from theorybert.deployment import install_bundle,read_manifest


def fixture(tmp_path,members=None):
    data=b'exact evaluated weight bytes';name='artifacts/model/weights.pt'
    archive=tmp_path/'bundle.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for item in members or [(name,data)]:
            entry=tarfile.TarInfo(item[0]);entry.size=len(item[1]);tar.addfile(entry,io.BytesIO(item[1]))
    manifest={'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'unpacked_bytes':len(data),'files':[{'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}]}
    path=tmp_path/'manifest.json';path.write_text(json.dumps(manifest))
    return archive,path,manifest,data


def test_installer_preserves_exact_bytes_without_training(tmp_path):
    archive,path,_,data=fixture(tmp_path)
    assert install_bundle(path,tmp_path/'installed',archive)==1
    assert (tmp_path/'installed/artifacts/model/weights.pt').read_bytes()==data


def test_installer_rejects_corrupt_archive_before_extracting(tmp_path):
    archive,path,_,_=fixture(tmp_path);archive.write_bytes(archive.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='fingerprint'):install_bundle(path,tmp_path/'installed',archive)
    assert not (tmp_path/'installed/artifacts').exists()


@pytest.mark.parametrize('name',['../escape','artifacts/../../escape','/artifacts/weights','artifacts//weights','artifacts/./weights','artifacts\\weights'])
def test_manifest_refuses_unsafe_paths(tmp_path,name):
    _,path,manifest,_=fixture(tmp_path);manifest['files'][0]['path']=name;path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='path'):read_manifest(path)


def test_installer_refuses_unlisted_tar_member(tmp_path):
    archive,path,_,_=fixture(tmp_path,[('../escape',b'bad')])
    with pytest.raises(ValueError,match='member'):install_bundle(path,tmp_path/'installed',archive)
    assert not (tmp_path/'escape').exists()


def test_installer_refuses_mismatched_member_hash(tmp_path):
    archive,path,manifest,_=fixture(tmp_path);manifest['files'][0]['sha256']='0'*64;path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='fingerprint'):install_bundle(path,tmp_path/'installed',archive)
    assert not list((tmp_path/'installed').rglob('*.installing'))


def test_installer_refuses_preexisting_symlink_escape(tmp_path):
    archive,path,_,_=fixture(tmp_path);root=tmp_path/'installed';root.mkdir();outside=tmp_path/'outside';outside.mkdir();(root/'artifacts').symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError,match='escapes'):install_bundle(path,root,archive)
    assert not list(outside.iterdir())
