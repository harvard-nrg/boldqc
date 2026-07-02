import os
import json
import errno
import fcntl
import logging
import tempfile as tf
from boldqc.state import State
from boldqc import MaskThresholdError
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseTask(ABC):
    def __init__(self, infile, outdir, tempdir=None, pipenv=None, layout=None):
        self._infile = infile
        self._outdir = outdir
        self._tempdir = tempdir
        self._pipenv = pipenv
        self._layout = layout
        self._tempdir = tempdir if tempdir else tf.gettempdir()
        self._logdir = os.path.join(outdir, 'logs')
        self._prov = os.path.join(self._logdir, 'provenance.json')
        self.build()

    @staticmethod
    def state(prov):
        if os.path.exists(prov):
            # attempt to acquire a lock on provenance file
            fd = os.open(prov, os.O_RDWR|os.O_CREAT)
            try:
                fcntl.lockf(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
                logger.debug('successfully locked %s', prov)
            except IOError as e:
                if e.errno == errno.EWOULDBLOCK:
                    logger.debug('another process has already locked %s', prov)
                    return State.RUNNING
                raise e
            # check returncode
            with open(prov) as fo:
                js = json.load(fo)
            if js['returncode'] is None:
                return State.TERMINATED
            elif js['returncode'] == 0:
                return State.COMPLETE
            else:
                return State.FAILED
        return State.NOT_FOUND

    @abstractmethod
    def build(self):
        pass

    def workdir(self):
        if not os.path.exists(self._tempdir):
            os.makedirs(self._tempdir)
        return tf.mkdtemp(suffix='.boldqc', dir=self._tempdir)

    def get_mask_threshold(self):
        js = self._layout.get_metadata(self._infile)
        bits_stored = js.get('BitsStored', None)
        receive_coil = js.get('ReceiveCoilName', None)
        # 20ch coil should use a mask threshold of 3000.0 regardless of the bits stored
        if receive_coil in ['HeadNeck_20']:
            logger.info(f'scan has "{bits_stored}" bits and receive coil "{receive_coil}", setting mask threshold to 3000.0')
            return 3000.0
        # 12-bit scans should use a mask threshold of 150.0
        if bits_stored == 12:
            logger.info(f'scan has "{bits_stored}" bits and receive coil "{receive_coil}", setting mask threshold to 150.0')
            return 150.0
        # 16-bit scans should use a mask threshold of 1500.0 for 32ch coil and 3000.0 for 64ch coil
        if bits_stored == 16:
            if receive_coil in ['Head_32']:
                logger.info(f'scan has "{bits_stored}" bits and receive coil "{receive_coil}", setting mask threshold to 1500.0')
                return 1500.0
            if receive_coil in ['Head_64', 'HeadNeck_64']:
                logger.info(f'scan has "{bits_stored}" bits and receive coil "{receive_coil}", setting mask threshold to 3000.0')
                return 3000.0
        raise MaskThresholdError(f'unexpected bits stored "{bits_stored}" + receive coil "{receive_coil}"')

    def logdir(self):
        if not os.path.exists(self._logdir):
            os.makedirs(self._logdir)
        return self._logdir

    @property
    def command(self):
        return self.job.command

