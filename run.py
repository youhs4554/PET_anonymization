from __future__ import print_function
import pydicom
from utils import dcm_to_nrrd
import os
import glob
from natsort import natsorted
from tqdm import tqdm
import argparse
from p_tqdm import p_map


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
    for filename in filename_list:
        dataset = pydicom.dcmread(filename)

        dataset = anonymize(dataset, TARGET_ELEMENTS)

        # save resulting dataset
        anm_dir = infold.replace(INPUT_ROOT, ANONYM_DCM_ROOT)
        if not os.path.exists(anm_dir):
            print(f'create directory at {anm_dir}')
            os.makedirs(anm_dir, exist_ok=True)  # cretae a new dir
        anm_path = os.path.join(anm_dir, os.path.basename(filename))
        dataset.save_as(anm_path)

        if args.VERBOSE:
            for de in TARGET_ELEMENTS:
                print(filename, dataset.data_element(de))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--INPUT_ROOT', type=str,
                        default='DCMs', help='root directory of dcm slices.')
    parser.add_argument('--ANONYM_DCM_ROOT', type=str,
                        default='DCMs_anonymized', help='root directory of dcm slices.')
    parser.add_argument('--VERBOSE', action='store_true',
                        help='If true, convert and save anonymized dcms to nrrd format.')
    parser.set_defaults(VERBOSE=False)
    args = parser.parse_args()

    INPUT_ROOT = args.INPUT_ROOT
    ANONYM_DCM_ROOT = args.ANONYM_DCM_ROOT

    TARGET_ELEMENTS = []
    for line in open('target_elements.txt', 'r'):
        TARGET_ELEMENTS.append(line.strip())
    print(f'Start anonymization process for {TARGET_ELEMENTS}')

    input_folders = natsorted(glob.glob(f'{INPUT_ROOT}/*'))
    p_map(runner, input_folders)

    print('Done!')
