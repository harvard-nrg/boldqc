import os
import json
import shutil
import base64
import boldqc
import logging
import boldqc.tasks as tasks
from executors.models import Job

logger = logging.getLogger(__file__)

class Task(tasks.BaseTask):
    def __init__(self, infile, outdir, tempdir=None, pipenv=None, layout=None):
        super().__init__(infile, outdir, tempdir, pipenv, layout)

    def build(self):
        if 'echo' in self._layout.get_entities() and '2' in self._layout.get_echos():
            sidecar = self._layout.get('file', extension='.json', suffix='bold', echo=2)[0]
        else:
            sidecar = self._layout.get('file', extension='.json', suffix='bold')[0]
        mask_threshold = self.get_mask_threshold()
        cmd = [
            'selfie',
            '--lock',
            '--output-file', self._prov,
            'niftiqa_wrapper.py',
            '--skip', '4',
            '--mask-threshold', str(mask_threshold),
            '--output-dir', self._outdir
        ]
        cmd.append(self._infile)
        logger.debug(cmd)
        if self._pipenv:
            os.chdir(self._pipenv)
            cmd[:0] = ['pipenv', 'run']
        logdir = self.logdir()
        # copy json sidecar into output logs directory
        destination = os.path.join(logdir, os.path.basename(sidecar))
        logger.debug('copying %s to %s', sidecar, destination)
        shutil.copy2(sidecar, destination)
        # return job object
        log = os.path.join(logdir, 'niftiqa_wrapper.log')
        self.job = Job(
            name='niftiqa',
            time='1440',
            memory='3G',
            command=cmd,
            output=log,
            error=log
        )

