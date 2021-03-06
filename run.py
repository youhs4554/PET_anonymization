from __future__ import print_function
import pydicom
from utils import dcm_to_nrrd
import os
import glob
from natsort import natsorted
from tqdm import tqdm
import argparse
import pandas as pd
import numpy as np
from multiprocessing import Pool
from utils import download_dependencies, get_suv_factor
import SimpleITK as sitk

parser = argparse.ArgumentParser()
parser.add_argument('--INPUT_ROOT', type=str,
                    default='DCMs', help='root directory of dcm slices.')
parser.add_argument('--ANONYM_DCM_ROOT', type=str,
                    default='DCMs_anonymized', help='root directory of dcm slices.')
parser.add_argument('--TABLE_PATH', type=str,
                    default='./data/ID_Change.xlsx', help='path to mapping talbe.')
parser.add_argument('--VERBOSE', action='store_true',
                    help='If true, convert and save anonymized dcms to nrrd format.')
parser.set_defaults(VERBOSE=False)
parser.add_argument('--debug', action='store_true',
                    help='If true, enter debug mode.')
parser.set_defaults(debug=False)
parser.add_argument('--disable_suv', action='store_true',
                    help='If true, compute SUV value')
parser.set_defaults(disable_suv=False)
args = parser.parse_args()


INPUT_ROOT = args.INPUT_ROOT
ANONYM_DCM_ROOT = args.ANONYM_DCM_ROOT


#global TARGET_ELEMENTS
#global data_frame

TARGET_ELEMENTS = []
for line in open('target_elements.txt', 'r'):
    TARGET_ELEMENTS.append(line.strip())
print(f'Start anonymization process for {TARGET_ELEMENTS}')

data_frame = pd.read_excel(args.TABLE_PATH)
#input_folders = natsorted(glob.glob(f'{INPUT_ROOT}/*'))
input_folders = natsorted([ os.path.join(INPUT_ROOT, x) for x in data_frame.HospNo ])

data_frame.HospNo = np.char.zfill(data_frame.HospNo.values.astype(str), 32)



def pid2ixs(df, pid):
    return str(df[df.HospNo == str(pid).zfill(32)].No.values[0])


def anonymize(dataset, data_elements,
              replacement_str="anonymous"):
    for de in data_elements:
        try:
            ret = dataset.data_element(de)
        except KeyError:
            # skip non-existing key
            continue
        if ret is None:
            # exception handling
            raise Exception(f"Unkown element \'{de}\'")
        ret.value = replacement_str

    return dataset

def runner(infold):
    filename_list = natsorted(glob.glob(infold+'/*'))
    # run SUVFactorCalculator
    if not args.disable_suv:
        suv = get_suv_factor(infold)
        suv_slices = []

    # anonymize and save as .dcm
    try:
        for i in tqdm(range(len(filename_list)), desc='anonymize...'):
            filename = filename_list[i]
            try:
                dataset = pydicom.dcmread(filename)
            except:
                continue

            dataset = anonymize(dataset, TARGET_ELEMENTS)

            # save resulting dataset
            pid = os.path.basename(infold)
            cvt_ix = pid2ixs(data_frame, pid=pid)

            anm_dir = infold.replace(
                INPUT_ROOT, ANONYM_DCM_ROOT).replace(pid, cvt_ix)
            anm_dir_raw = anm_dir
            if not args.disable_suv:
                anm_dir_raw = os.path.join(anm_dir, 'raw')
            
            # directory for raw anonymized dcms
            if not os.path.exists(anm_dir_raw):
                print(f'create directory at {anm_dir_raw}')
                os.makedirs(anm_dir_raw, exist_ok=True)  # cretae a new dir
               
            _, ext = os.path.splitext(os.path.basename(filename))
            anm_path = os.path.join(anm_dir_raw, f'Slice{i:04}'+ext)
            dataset.save_as(anm_path)   # 1 : save original pixel data
            
            # multiply with SUV-ScaleFactor
            img = sitk.GetArrayFromImage(sitk.ReadImage(anm_path))  # (1,h,w)
            #anm_suv_path = os.path.join(anm_dir_suv, f'PET{i:04}'+'.nrrd')

            if not args.disable_suv:
                suv_slices.append( suv * img )
                suv_img = sitk.GetImageFromArray(suv * img)
           
            if args.VERBOSE:
                for de in TARGET_ELEMENTS:
                    print(filename, dataset.data_element(de))
        if not args.disable_suv:
            suv_volume = sitk.GetImageFromArray(np.vstack(suv_slices)[::-1])
            suv_volume = sitk.Cast(suv_volume, sitk.sitkFloat64)
        
            # write a resulting volume as .nrrd file
            sitk.WriteImage(suv_volume, os.path.join(anm_dir, 'SUV.nrrd'))

    except KeyboardInterrupt:
        raise Exception('User Interrupt')


if __name__ == '__main__':
    # Download dependencies from GoogleDrive
    if not args.disable_suv and not os.path.exists('./lib/Slicer-4.10.2-linux-amd64') and not os.path.exists('./lib/NA-MIC'):
        download_dependencies()

    pool = Pool(8)

    pool.map(runner, input_folders)
    pool.close()
    pool.join()

    if args.debug:
        runner(input_folders[0])

    print('Done!')
