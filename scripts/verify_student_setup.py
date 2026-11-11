"""Run the free batch exercise and package only selected review reports."""
import argparse
import json
from importlib.metadata import version
from pathlib import Path
import platform
import shutil
import zipfile

from reaction_knowledge_lab.batch import batch_demo
from reaction_knowledge_lab.files import ROOT, write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('runs/student-check'))
    args=parser.parse_args()
    workdir=args.output
    result=batch_demo(workdir)
    write_json(workdir/'student-environment.json',{
        'system':platform.system(),'architecture':platform.machine(),'python':platform.python_version(),
        'packages':{name:version(name) for name in ['ord-schema','rdkit','PyMuPDF']},'api_calls':0})
    shutil.copyfile(ROOT/'docs/REVIEW_RETURN.md',workdir/'REVIEW_RETURN.md')
    files=['verification.json','query-regression.json','incremental.json','student-environment.json',
           'validation/validation.json','REVIEW_RETURN.md']
    archive=workdir/'return-to-teacher.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in files:bundle.write(workdir/name,arcname=name)
    print(json.dumps({'passed':result['passed'],'api_calls':0,'return_zip':str(archive),
        'note':'Fill REVIEW_RETURN.md separately and return it with this ZIP; no source papers or credentials included.'},ensure_ascii=True,indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
