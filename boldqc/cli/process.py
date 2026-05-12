import os
import re
import sys
import json
import yaml
import yaxil
import glob
import math
import boldqc
import logging
import tarfile
import executors
import tempfile as tf
import subprocess as sp
import boldqc.tasks.stackcheck_ext as stackcheck_ext
import boldqc.tasks.niftiqa_wrapper as niftiqa_wrapper
from executors.models import Job, JobArray
from boldqc.bids import BIDS
from boldqc.xnat import Report
from boldqc.state import State

logger = logging.getLogger(__name__)
LIBEXEC = os.path.realpath(os.path.join(os.path.dirname(boldqc.__file__), 'libexec'))
os.environ['PATH'] = LIBEXEC + ':' + os.environ['PATH']

def do(args):
    if args.insecure:
        logger.warning('disabling ssl certificate verification')
        yaxil.CHECK_CERTIFICATE = False

    # create job executor and job array
    if args.scheduler:
        E = executors.get(args.scheduler, partition=args.partition)
    else:
        E = executors.probe(args.partition)
    jarray = JobArray(E)

    # create BIDS
    B = BIDS(args.bids_dir, args.sub, ses=args.ses)
    raw = B.raw_bold('bold', run=args.run)
    logger.debug('BOLD raw: %s', raw)

    # get repetition time from T1w sidecar for vNav processing
    sidecar = os.path.join(*raw) + '.json'
    logger.debug('sidecar: %s', sidecar)
    with open(sidecar) as fo:
        js = json.load(fo)
        tr = js['RepetitionTime']
    logger.debug('TR: %s', tr)

    boldqc_outdir = None
    infile = os.path.join(*raw) + '.nii.gz'
    boldqc_outdir = B.derivatives_dir('boldqc')
    boldqc_outdir = os.path.join(boldqc_outdir, 'func', raw[1])
    
    # niftiqa job
    task = niftiqa_wrapper.Task(
        infile,
        boldqc_outdir
    )
    logger.info(json.dumps(task.command, indent=1))
    jarray.add(task.job)

    # stackcheck_ext job
    task = stackcheck_ext.Task(
        infile,
        boldqc_outdir
    )
    logger.info(json.dumps(task.command, indent=1))
    jarray.add(task.job)

    # submit jobs and wait for them to finish
    if not args.dry_run:
        logger.info('submitting jobs')
        jarray.submit(limit=1)
        logger.info('waiting for all jobs to finish')
        jarray.wait()
        numjobs = len(jarray.array)
        failed = len(jarray.failed)
        complete = len(jarray.complete)
        if failed:
            logger.info('%s/%s jobs failed', failed, numjobs)
            for pid,job in iter(jarray.failed.items()):
                logger.error('%s exited with returncode %s', job.name, job.returncode)
                with open(job.output, 'r') as fp:
                    logger.error('standard output\n%s', fp.read())
                with open(job.error, 'r') as fp:
                    logger.error('standard error\n%s', fp.read())
        logger.info('%s/%s jobs completed', complete, numjobs)
        if failed > 0:
            sys.exit(1)

    # artifacts directory
    if not args.artifacts_dir:
        args.artifacts_dir = os.path.join(
            boldqc_outdir,
            'xnat-artifacts'
        )

    # build data to upload to XNAT
    R = Report(args.bids_dir, args.sub, args.ses, args.run)
    logger.info('building xnat artifacts to %s', args.artifacts_dir)
    R.build_assessment(args.artifacts_dir)

    # upload data to xnat over rest api
    if args.xnat_upload:
        logger.info('Uploading artifacts to XNAT')
        auth = yaxil.auth2(args.xnat_alias)
        if getattr(args, 'jsession', None):
            auth = auth._replace(cookie={'JSESSIONID': args.jsession})
        with yaxil.session(auth) as ses:
            ses.storerest(args.artifacts_dir, 'boldqc-resource')

