import re
import os
import io
import sys
import glob
import yaml
import json
import lxml
import shutil
import zipfile
import logging
from lxml import etree
from pathlib import Path
from bids import BIDSLayout
import boldqc.parsers as parsers

logger = logging.getLogger(__name__)

class Report:
    def __init__(self, layout, entities, outdir):
        self.layout = layout
        self.entities = entities
        self.outdir = Path(outdir)
        self.stem = self.outdir.name

    def build_assessment(self, output):
        '''
        Build XNAT assessment

        :param output: Base output directory
        '''

        # initialize namespaces
        ns = {
            None: 'http://www.neuroinfo.org/neuroinfo',
            'xs': 'http://www.w3.org/2001/XMLSchema',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xnat': 'http://nrg.wustl.edu/xnat',
            'neuroinfo': 'http://www.neuroinfo.org/neuroinfo'
        }

        # read json sidecar for scan number
        boldqc_ds = self.datasource()
        logger.info('boldqc info %s', '|'.join(boldqc_ds.values()))

        # assessment id
        aid = '{0}_BOLD_{1}_EQC'.format(
            boldqc_ds['experiment'],
            boldqc_ds['scan']
        )
        logger.info('Assessor ID %s', aid)

        # root element
        xnatns = '{%s}' % ns['xnat']
        root = etree.Element('BOLDQC', nsmap=ns)
        root.attrib['project'] = boldqc_ds['project']
        root.attrib['ID'] = aid
        root.attrib['label'] = aid
        
        # get start date and time from morph provenance
        prov = self.provenance()

        # add date and time
        etree.SubElement(root, xnatns + 'date').text = prov['start_date']
        etree.SubElement(root, xnatns + 'time').text = prov['start_time']
        
        # compile a list of files to be added to xnat:out section
        resources = self._get_resources(aid)

        floatfmt = lambda x: '{:f}'.format(float(x))

        # parse auto_report
        auto_report_file = self.outdir / f'{self.stem}_autoReport.txt'
        logger.info(f'looking for auto report {auto_report_file}')
        auto_report = parsers.parse_auto_report(auto_report_file)
        
        # parse slice_report
        slice_report_file = self.outdir / f'{self.stem}_sliceReport.txt'
        logger.info(f'looking for slice report {slice_report_file}')
        slice_report = parsers.parse_slice_report(slice_report_file)
        
        # start building XML
        xnatns = '{%s}' % ns['xnat']
        
        # add boldqc metadata
        etree.SubElement(root, xnatns + 'imageSession_ID').text = boldqc_ds['experiment_id']
        etree.SubElement(root, 'bold_scan_id').text = boldqc_ds['scan']
        etree.SubElement(root, 'session_label').text = boldqc_ds['experiment']

        # add elements from the auto report and slice report
        etree.SubElement(root, 'Size').text = auto_report['InputFileSize']
        etree.SubElement(root, 'N_Vols').text = auto_report['N_Vols']
        etree.SubElement(root, 'Skip').text = auto_report['Skip']
        etree.SubElement(root, 'qc_N_Tps').text = auto_report['qc_N_Tps']
        etree.SubElement(root, 'qc_thresh').text = floatfmt(auto_report['qc_thresh'])
        etree.SubElement(root, 'qc_nVox').text = auto_report['qc_nVox']
        etree.SubElement(root, 'qc_Mean').text = floatfmt(auto_report['qc_Mean'])
        etree.SubElement(root, 'qc_Max').text = floatfmt(slice_report['qc_Max'])
        etree.SubElement(root, 'qc_Min').text = floatfmt(slice_report['qc_Min'])
        etree.SubElement(root, 'qc_Stdev').text = floatfmt(auto_report['qc_Stdev'])
        etree.SubElement(root, 'qc_sSNR').text = floatfmt(auto_report['qc_sSNR'])
        etree.SubElement(root, 'qc_vSNR').text = floatfmt(auto_report['qc_vSNR'])
        etree.SubElement(root, 'qc_slope').text = floatfmt(auto_report['qc_slope'])
        etree.SubElement(root, 'mot_N_Tps').text = auto_report['mot_N_Tps']
        etree.SubElement(root, 'mot_rel_x_mean').text = floatfmt(auto_report['mot_rel_x_mean'])
        etree.SubElement(root, 'mot_rel_x_sd').text = floatfmt(auto_report['mot_rel_x_sd'])
        etree.SubElement(root, 'mot_rel_x_max').text = floatfmt(auto_report['mot_rel_x_max'])
        etree.SubElement(root, 'mot_rel_x_1mm').text = auto_report['mot_rel_x_1mm']
        etree.SubElement(root, 'mot_rel_x_5mm').text = auto_report['mot_rel_x_5mm']
        etree.SubElement(root, 'mot_rel_y_mean').text = floatfmt(auto_report['mot_rel_y_mean'])
        etree.SubElement(root, 'mot_rel_y_sd').text = floatfmt(auto_report['mot_rel_y_sd'])
        etree.SubElement(root, 'mot_rel_y_max').text = floatfmt(auto_report['mot_rel_y_max'])
        etree.SubElement(root, 'mot_rel_y_1mm').text = auto_report['mot_rel_y_1mm']
        etree.SubElement(root, 'mot_rel_y_5mm').text = auto_report['mot_rel_y_5mm']
        etree.SubElement(root, 'mot_rel_z_mean').text = floatfmt(auto_report['mot_rel_z_mean'])
        etree.SubElement(root, 'mot_rel_z_sd').text = floatfmt(auto_report['mot_rel_z_sd'])
        etree.SubElement(root, 'mot_rel_z_max').text = floatfmt(auto_report['mot_rel_z_max'])
        etree.SubElement(root, 'mot_rel_z_1mm').text = auto_report['mot_rel_z_1mm']
        etree.SubElement(root, 'mot_rel_z_5mm').text = auto_report['mot_rel_z_5mm']
        etree.SubElement(root, 'mot_rel_xyz_mean').text = floatfmt(auto_report['mot_rel_xyz_mean'])
        etree.SubElement(root, 'mot_rel_xyz_sd').text = floatfmt(auto_report['mot_rel_xyz_sd'])
        etree.SubElement(root, 'mot_rel_xyz_max').text = floatfmt(auto_report['mot_rel_xyz_max'])
        etree.SubElement(root, 'mot_rel_xyz_1mm').text = auto_report['mot_rel_xyz_1mm']
        etree.SubElement(root, 'mot_rel_xyz_5mm').text = auto_report['mot_rel_xyz_5mm']
        etree.SubElement(root, 'rot_rel_x_mean').text = floatfmt(auto_report['rot_rel_x_mean'])
        etree.SubElement(root, 'rot_rel_x_sd').text = floatfmt(auto_report['rot_rel_x_sd'])
        etree.SubElement(root, 'rot_rel_x_max').text = floatfmt(auto_report['rot_rel_x_max'])
        etree.SubElement(root, 'rot_rel_y_mean').text = floatfmt(auto_report['rot_rel_y_mean'])
        etree.SubElement(root, 'rot_rel_y_sd').text = floatfmt(auto_report['rot_rel_y_sd'])
        etree.SubElement(root, 'rot_rel_y_max').text = floatfmt(auto_report['rot_rel_y_max'])
        etree.SubElement(root, 'rot_rel_z_mean').text = floatfmt(auto_report['rot_rel_z_mean'])
        etree.SubElement(root, 'rot_rel_z_sd').text = floatfmt(auto_report['rot_rel_z_sd'])
        etree.SubElement(root, 'rot_rel_z_max').text = floatfmt(auto_report['rot_rel_z_max'])
        etree.SubElement(root, 'mot_abs_x_mean').text = floatfmt(auto_report['mot_abs_x_mean'])
        etree.SubElement(root, 'mot_abs_x_sd').text = floatfmt(auto_report['mot_abs_x_sd'])
        etree.SubElement(root, 'mot_abs_x_max').text = floatfmt(auto_report['mot_abs_x_max'])
        etree.SubElement(root, 'mot_abs_y_mean').text = floatfmt(auto_report['mot_abs_y_mean'])
        etree.SubElement(root, 'mot_abs_y_sd').text = floatfmt(auto_report['mot_abs_y_sd'])
        etree.SubElement(root, 'mot_abs_y_max').text = floatfmt(auto_report['mot_abs_y_max'])
        etree.SubElement(root, 'mot_abs_z_mean').text = floatfmt(auto_report['mot_abs_z_mean'])
        etree.SubElement(root, 'mot_abs_z_sd').text = floatfmt(auto_report['mot_abs_z_sd'])
        etree.SubElement(root, 'mot_abs_z_max').text = floatfmt(auto_report['mot_abs_z_max'])
        etree.SubElement(root, 'mot_abs_xyz_mean').text = floatfmt(auto_report['mot_abs_xyz_mean'])
        etree.SubElement(root, 'mot_abs_xyz_sd').text = floatfmt(auto_report['mot_abs_xyz_sd'])
        etree.SubElement(root, 'mot_abs_xyz_max').text = floatfmt(auto_report['mot_abs_xyz_max'])
        etree.SubElement(root, 'rot_abs_x_mean').text = floatfmt(auto_report['rot_abs_x_mean'])
        etree.SubElement(root, 'rot_abs_x_sd').text = floatfmt(auto_report['rot_abs_x_sd'])
        etree.SubElement(root, 'rot_abs_x_max').text = floatfmt(auto_report['rot_abs_x_max'])
        etree.SubElement(root, 'rot_abs_y_mean').text = floatfmt(auto_report['rot_abs_y_mean'])
        etree.SubElement(root, 'rot_abs_y_sd').text = floatfmt(auto_report['rot_abs_y_sd'])
        etree.SubElement(root, 'rot_abs_y_max').text = floatfmt(auto_report['rot_abs_y_max'])
        etree.SubElement(root, 'rot_abs_z_mean').text = floatfmt(auto_report['rot_abs_z_mean'])
        etree.SubElement(root, 'rot_abs_z_sd').text = floatfmt(auto_report['rot_abs_z_sd'])
        etree.SubElement(root, 'rot_abs_z_max').text = floatfmt(auto_report['rot_abs_z_max'])

        # write assessor to output mount location.
        xmlstr = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')
        assessor_dir = Path(output, 'assessor')
        assessor_dir.mkdir(parents=True, exist_ok=True)
        assessment_xml = assessor_dir / 'assessment.xml'
        logger.info(f'writing {assessment_xml}')
        assessment_xml.write_bytes(xmlstr)

        # copy resources to output mount location
        resources_dir = Path(output, 'resources')
        resources_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f'copying resources into {resources_dir}')
        for resource in resources:
            src = resource['source']
            dest = resources_dir / resource['dest']
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)

    def datasource(self):
        # returns the xnat specific data from the boldqc log .json file
        path = self.outdir / 'logs' / f'{self.stem}.json'
        with open(path) as fo:
            js = json.load(fo)
        return js['DataSource']['application/x-xnat']

    def protocol(self, task):
        # returns the protocol specific information from the boldqc log .json file
        path = self.outdir / 'logs' / f'{self.stem}.json'
        with open(path) as fo:
            js = json.load(fo)
        return js['ProtocolName']

    def provenance(self):
        # returns the provenance information from the boldqc log .json file
        path = self.outdir / 'logs' / 'provenance.json'
        with open(path) as fo:
            js = json.load(fo)
        return js

    def _get_resources(self, aid):
        """
        Build resource mapping for XNAT upload.
        
        Args:
            aid: Assessment ID
            
        Returns:
            List of dicts with 'source' and 'dest' keys
        """
        
        # Define file specifications: (suffix, extension, dest_dir, output_suffix)
        file_specs = [
            ('mean', '.nii.gz', 'mean-nifti', 'mean.nii.gz'),
            ('meanThumbnail', '.png', 'mean-image', 'mean_thumbnail.png'),
            ('meanSlice', '.txt', 'mean-slice-data', 'mean_slice.txt'),
            ('meanSlice', '.png', 'mean-slice-image', 'mean_slice.png'),
            ('mask', '.nii.gz', 'mask-nifti', 'mask.nii.gz'),
            ('maskThumbnail', '.png', 'mask-image', 'mask_thumbnail.png'),
            ('snr', '.nii.gz', 'snr-nifti', 'snr.nii.gz'),
            ('snrThumbnail', '.png', 'snr-image', 'snr_thumbnail.png'),
            ('stdev', '.nii.gz', 'stdev-nifti', 'stdev.nii.gz'),
            ('stdevThumbnail', '.png', 'stdev-image', 'stdev_thumbnail.png'),
            ('motion', '.png', 'motion-image', 'motion.png'),
            ('slope', '.nii.gz', 'slope-nifti', 'slope.nii.gz'),
            ('slopeThumbnail', '.png', 'slope-image', 'slope_thumbnail.png'),
            ('autoReport', '.txt', 'auto-report', 'auto_report.txt'),
            ('sliceReport', '.txt', 'slice-report', 'slice_report.txt')
        ]
        
        # Build from file specs
        resources = []
        for suffix, ext, dest_dir, output_name in file_specs:
            source = self.outdir / f'{self.stem}_{suffix}{ext}'
            dest = Path(dest_dir) / f'{aid}_{output_name}'
            if not source.exists():
                raise FileNotFoundError(source)
            resource = {
                'source': source,
                'dest': dest
            }
            resources.append(resource)

        return resources

class AssessmentError(Exception):
    pass
