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

parser = argparse.ArgumentParser()
parser.add_argument('--INPUT_ROOT', type=str,
                    default='DCMs', help='root directory of dcm slices.')
parser.add_argument('--ANONYM_DCM_ROOT', type=str,
                    default='DCMs_anonymized', help='root directory of dcm slices.')
parser.add_argument('--VERBOSE', action='store_true',
                    help='If true, convert and save anonymized dcms to nrrd format.')
parser.set_defaults(VERBOSE=False)
parser.add_argument('--debug', action='store_true',
                    help='If true, enter debug mode.')
parser.set_defaults(debug=False)
args = parser.parse_args()


INPUT_ROOT = args.INPUT_ROOT
ANONYM_DCM_ROOT = args.ANONYM_DCM_ROOT


#global TARGET_ELEMENTS
#global data_frame

TARGET_ELEMENTS = []
for line in open('target_elements.txt', 'r'):
    TARGET_ELEMENTS.append(line.strip())
print(f'Start anonymization process for {TARGET_ELEMENTS}')

data_frame = pd.read_excel('./data/ID_Change.xlsx')
data_frame.HospNo = np.char.zfill(data_frame.HospNo.values.astype(str), 8)


input_folders = natsorted(glob.glob(f'{INPUT_ROOT}/*'))


def pid2ixs(df, pid):
    return str(df[df.HospNo == str(pid).zfill(8)].No.values[0])


def anonymize(dataset, data_elements,
              replacement_str="anonymous"):
    for de in data_elements:
        ret = dataset.data_element(de)
        if ret is None:
            # exception handling
            raise Exception(f"Unkown element \'{de}\'")
        ret.value = replacement_str

    return dataset


def runner(infold):
    filename_list = natsorted(glob.glob(infold+'/*'))

    # anonymize and save as .dcm
    try:
        for i in tqdm(range(len(filename_list))):
            filename = filename_list[i]
            dataset = pydicom.dcmread(filename)

            dataset = anonymize(dataset, TARGET_ELEMENTS)

            # save resulting dataset
            pid = os.path.basename(infold)
            cvt_ix = pid2ixs(data_frame, pid=pid)

            anm_dir = infold.replace(
                INPUT_ROOT, ANONYM_DCM_ROOT).replace(pid, cvt_ix)
            if not os.path.exists(anm_dir):
                print(f'create directory at {anm_dir}')
                os.makedirs(anm_dir, exist_ok=True)  # cretae a new dir
            _, ext = os.path.splitext(os.path.basename(filename))
            anm_path = os.path.join(anm_dir, f'PET{i:04}'+ext)
            dataset.save_as(anm_path)

            if args.VERBOSE:
                for de in TARGET_ELEMENTS:
                    print(filename, dataset.data_element(de))
    except KeyboardInterrupt:
        raise Exception('User Interrupt')


if __name__ == '__main__':
    pool = Pool(8)

    pool.map(runner, input_folders)
    pool.close()
    pool.join()

    if args.debug:
        runner(input_folders[0])

    print('Done!')
