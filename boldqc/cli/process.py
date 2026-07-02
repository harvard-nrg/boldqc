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
from bids import BIDSLayout
from boldqc.bids import make_dataset_description
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

    # create pybids layout object
    layout = BIDSLayout(args.bids_dir, validate=False)

    # create layout filters
    filters = {
        'subject': args.sub,
        'session': args.ses,
        'run': args.run,
        'datatype': 'func',
        'suffix': 'bold'
    }
    if args.ses:
        filters['session'] = args.ses

    # get TR using pybids
    logger.info(f'using BIDSLayout filters {filters}')
    tr = layout.get_tr(**filters)
    logger.info(f'TR: {tr}')

    # grab the second echo if multiecho data is present
    if '2' in layout.get_echos(**filters):
        infile_obj = layout.get(
            'object',
            extension='nii.gz',
            echo=2,
            **filters
        )[0]
    else:
        infile_obj = layout.get(
            'object',
            extension='nii.gz',
            **filters
        )[0]

    infile = infile_obj.path
    entities = infile_obj.get_entities()

    # build the boldqc derivatives directory using pybids' build_path method
    # will incorporate echo is present
    boldqc_outdir = layout.build_path(
        source=entities,
        path_patterns=(
            "derivatives/boldqc/sub-{subject}/[ses-{session}]/"
            "{datatype}/sub-{subject}[_ses-{session}]_run-{run}"
            "[_echo-{echo}]_{suffix}"
        )
    )

    # niftiqa job
    task = niftiqa_wrapper.Task(
        infile,
        boldqc_outdir,
        entities,
        layout=layout
    )
    logger.info(json.dumps(task.command, indent=1))
    jarray.add(task.job)

    # stackcheck_ext job
    task = stackcheck_ext.Task(
        infile,
        boldqc_outdir,
        entities,
        layout=layout
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
            logger.info(f'{failed}/{numjobs} jobs failed')
            for pid,job in iter(jarray.failed.items()):
                logger.error(
                    f'{job.name} exited with returncode {job.returncode}'
                )
                with open(job.output, 'r') as fp:
                    logger.error('standard output\n%s', fp.read())
                with open(job.error, 'r') as fp:
                    logger.error('standard error\n%s', fp.read())
        logger.info(f'{complete}/{numjobs} jobs completed')
        if failed > 0:
            sys.exit(1)

    # Using pybids to index the files created by boldqc
    # Allows for easy querying of files within pybids
    if failed == 0:
        logger.info('Indexing workflow derivatives with pybids')
        derivatives_path = os.path.join(args.bids_dir, 'derivatives', 'boldqc')
        BIDSVersion = layout.description.get('BIDSVersion')
        make_dataset_description(
            path=derivatives_path,
            name='boldqc',
            version=BIDSVersion,
            type='derivative'
        )
        layout.add_derivatives(derivatives_path)
        logger.info('Derivatives indexed successfully')

    # artifacts directory
    if not args.artifacts_dir:
        args.artifacts_dir = os.path.join(
            boldqc_outdir,
            'xnat-artifacts'
        )

    # build data to upload to XNAT
    R = Report(layout, entities, boldqc_outdir)
    logger.info(f'building xnat artifacts to {args.artifacts_dir}')
    R.build_assessment(args.artifacts_dir)

    # upload data to xnat over rest api
    if args.xnat_upload:
        logger.info('Uploading artifacts to XNAT')
        auth = yaxil.auth2(args.xnat_alias)
        if getattr(args, 'jsession', None):
            auth = auth._replace(cookie={'JSESSIONID': args.jsession})
        with yaxil.session(auth) as ses:
            ses.storerest(args.artifacts_dir, 'boldqc-resource')

