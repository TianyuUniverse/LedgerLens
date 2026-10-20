"""Scan tracked files, never print credentials or private file contents."""
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    paths=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf-8').strip('\0').split('\0')
    private=ROOT/'data/provider.json'
    secret=json.loads(private.read_text(encoding='utf-8')).get('api_key','') if private.exists() else ''
    failed=[]
    pattern=re.compile(rb'\bsk-[a-zA-Z0-9]{24,}\b')
    for name in paths:
        if not name:continue
        file=ROOT/name
        if not file.is_file():continue
        data=file.read_bytes()
        if name.startswith(('data/','tmp/','node_modules/','output/')) or file.name=='.env' or (secret and secret.encode() in data) or pattern.search(data):
            failed.append(name)
    if failed:
        raise SystemExit('Private content selected in '+str(len(failed))+' files; review locally before sharing.')
    print('Shared-file credential scan passed:',len(paths),'tracked files.')
if __name__=='__main__':main()
