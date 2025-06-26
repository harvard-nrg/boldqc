import os
import json
import tarfile
import logging
from . import __version__

logger = logging.getLogger()

def version():
   return __version__.__version__
 
def archive(indir, output):
    with tarfile.open(output, 'w:gz') as tar:
        tar.add(indir, os.path.basename(indir))

def get_mask_threshold(sidecar):
    with open(sidecar, 'r') as fo:
        js = json.load(fo)
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

class MaskThresholdError(Exception):
    pass

