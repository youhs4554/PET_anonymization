# encoding: utf-8
import SimpleITK as sitk
import dicom

from google_drive_downloader import GoogleDriveDownloader as gdd
import os
import json
from copy import deepcopy, copy
import subprocess
import pydicom
from pathlib import Path

def fetch_file_from_google_drive(file_map, file_id):
    print(f'###Download {file_map[file_id]}###')
    gdd.download_file_from_google_drive(file_id=file_id,
                                        dest_path='./lib/tmp.zip',
                                        unzip=True)
    os.system('rm ./lib/tmp.zip')

def download_dependencies(manifest_path='./gdrive_manifest.json'):
    file_map = json.load(open(manifest_path))

    for file_id in file_map:
        fetch_file_from_google_drive(file_map, file_id)
    
    # setup for Slicer App
    os.system(f'chmod -R 777 ./lib/Slicer-4.10.2-linux-amd64/Slicer')

    # setup for lib usage
    config_home = os.path.join(str(Path.home()), '.config')
    os.system(f'cp -r ./lib/NA-MIC {config_home} && chmod -R 777 {config_home}')

def get_suv_factor(infold):
    res = subprocess.run(['./lib/Slicer-4.10.2-linux-amd64/Slicer',
                          '--launch', 'SUVFactorCalculator',
                          '-p', infold,
                          '-r', '.'], stdout=subprocess.PIPE)

    for line in res.stdout.split(b'\n'):
        if line.startswith(b'saving to'):
            line = line.decode('utf-8')
            break

    res_dcm = line.split()[-1]

    d = pydicom.read_file(res_dcm)
    suv = d.ReferencedImageRealWorldValueMappingSequence[0].RealWorldValueMappingSequence[0].RealWorldValueSlope
    os.remove(res_dcm)
    
    return suv


def dcm_to_nrrd(folder, to_path, intensity_windowing=True, compression=False):
    """Read a folder with DICOM files and convert to a nrrd file.
    Assumes that there is only one DICOM series in the folder.

    Parameters
    ----------
    folder : string
      Full path to folder with dicom files.
    to_path : string
      Full path to output file (with .nrrd extension). As the file is
      outputted through SimpleITK, any supported format can be selected.
    intensity_windowing: bool
      If True, the dicom tags 'WindowCenter' and 'WindowWidth' are used
      to clip the image, and the resulting image will be rescaled to [0,255]
      and cast as uint8.
    compression : bool
      If True, the output will be compressed.
    """
    reader = sitk.ImageSeriesReader()
    series_ids = reader.GetGDCMSeriesIDs(folder)

    assert len(series_ids) == 1, 'Assuming only one series per folder.'

    filenames = reader.GetGDCMSeriesFileNames(folder, series_ids[0])
    reader.SetFileNames(filenames)
    image = reader.Execute()

    if intensity_windowing:
        dcm = dicom.read_file(filenames[0])
        assert hasattr(dcm, 'WindowCenter') and hasattr(dcm, 'WindowWidth'),\
            'when `intensity_windowing=True`, dicom needs to have the `WindowCenter` and `WindowWidth` tags.'
        center = dcm.WindowCenter
        width = dcm.WindowWidth

        lower_bound = center - (width - 1)/2
        upper_bound = center + (width - 1)/2

        image = sitk.IntensityWindowing(image,
                                        lower_bound, upper_bound, 0, 255)
        image = sitk.Cast(image, sitk.sitkUInt8)  #  after intensity windowing, not necessarily uint8.

    writer = sitk.ImageFileWriter()
    if compression:
        writer.UseCompressionOn()

    writer.SetFileName(to_path)
    writer.Execute(image)