import os
import re
import json
import yaml
import yaxil
import logging
import yaxil.bids
import argparse as ap
import subprocess as sp
import boldqc.cli.get
import boldqc.cli.process
import collections as col
import yaxil.bids

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

        subject_label = scan['subject_label']
        logger.info(json.dumps(scans, indent=2))

        for run,scansr in scans.items():
            if run != args.run:
                continue
            logger.info('getting bold run=%s, scan=%s', run, scansr['bold'])
            boldqc.cli.get.get_bold(
                args,
                ses._auth,
                run,
                scansr['bold'],
                verbose=args.verbose
            )
            args.run = int(run)
            args.run = int(run)
            bids_ses_label = yaxil.bids.legal.sub('', args.label)
            bids_sub_label = yaxil.bids.legal.sub('', subject_label)
            args.sub = 'sub-' + bids_sub_label
            args.ses = 'ses-' + bids_ses_label
            logger.debug('sub=%s, ses=%s', args.sub, args.ses)
            args.jsession = ses._auth.cookie['JSESSIONID']
            boldqc.cli.process.do(args)
