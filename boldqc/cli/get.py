import os
import re
import sys
import json
import yaml
import yaxil
import logging
import argparse as ap
import subprocess as sp
import collections as col

logger = logging.getLogger(__name__)

def do(args):
    if args.insecure:
        logger.warning('disabling ssl certificate verification')
        yaxil.CHECK_CERTIFICATE = False

    # load authentication data and set environment variables for ArcGet.py
    auth = yaxil.auth2(
        args.xnat_alias,
        args.xnat_host,
        args.xnat_user,
        args.xnat_pass
    )
    os.environ['XNAT_HOST'] = auth.url
    os.environ['XNAT_USER'] = auth.username
    os.environ['XNAT_PASS'] = auth.password
    # query BOLD scans
    with yaxil.session(auth) as ses:
        scans = col.defaultdict(dict)
        run = 0
        for scan in ses.scans(label=args.label, project=args.project):
            scan_id = scan['id']
            scan_type = scan['type']
            if scan_type == 'BOLD':
                run += 1
                scans[run]['bold'] = scan_id
        logger.info(json.dumps(scans, indent=2))
        for run,scansr in scans.items():
            logger.info('getting bold run=%s, scan=%s', run, scansr['bold'])
            get_bold(args, ses._auth, run, scansr['bold'], verbose=args.verbose)

def get_bold(args, auth, run, scan, verbose=False):
    config = {
        'func': {
            'bold': [
                {
                    'run': int(run),
                    'scan': scan
                }
            ]
        }
    }
    config = yaml.safe_dump(config)
    cmd = [
        'ArcGet.py',
        '--label', args.label,
        '--output-dir', args.bids_dir,
        '--output-format', 'bids',
    ]
    if args.project:
        cmd.extend([
            '--project', args.project
        ])
    if args.insecure:
        cmd.extend([
            '--insecure'
        ])
    if args.in_mem:
        cmd.extend([
            '--in-mem'
        ])
    cmd.extend([
        '--config', '-'
    ])
    # pass jsession cookie so YAXIL does not create another one
    cmd.extend([
        '--jsession', auth.cookie['JSESSIONID']
    ])
    if verbose:
        cmd.append('--debug')
    logger.info(sp.list2cmdline(cmd))
    sp.check_output(cmd, input=config.encode('utf-8'))

