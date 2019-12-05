from __future__ import print_function
import pydicom
from utils import dcm_to_nrrd
import os
import glob
from natsort import natsorted
from tqdm import tqdm
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--INPUT_ROOT', type=str, default='DCMs', help='root directory of dcm slices.')
parser.add_argument('--ANONYM_DCM_ROOT', type=str, default='DCMs_anonymized', help='root directory of dcm slices.')
parser.add_argument('--ANONYM_NRRD_ROOT', type=str, default='NRRDs_anonymized', help='root directory of dcm slices.')
parser.add_argument('--VERBOSE', action='store_true', help='If true, convert and save anonymized dcms to nrrd format.')
parser.set_defaults(VERBOSE=False)
args = parser.parse_args()

INPUT_ROOT = args.INPUT_ROOT
ANONYM_DCM_ROOT = args.ANONYM_DCM_ROOT
ANONYM_NRRD_ROOT = args.ANONYM_NRRD_ROOT

TARGET_ELEMENTS = []
for line in open('target_elements.txt', 'r'):
    TARGET_ELEMENTS.append(line.strip())    
print(f'Start anonymization process for {TARGET_ELEMENTS}')

def anonymize(dataset, data_elements, 
                       replacement_str="anonymous"):
    for de in data_elements:
        ret = dataset.data_element(de)
        if ret is None:
            # exception handling
            raise Exception(f"Unkown element \'{de}\'")
        ret.value = replacement_str
    
    return dataset


input_folders = natsorted(glob.glob(f'{INPUT_ROOT}/*'))
out_paths = [ os.path.join(ANONYM_NRRD_ROOT, os.path.basename(infold)+'.nrrd') for infold in input_folders ]

for infold, outpath in tqdm(list(zip(input_folders, out_paths))):
    filename_list = natsorted(glob.glob(infold+'/*'))
    
    # anonymize and save as .dcm
    for filename in filename_list:
        dataset = pydicom.dcmread(filename)
        
        dataset = anonymize(dataset, TARGET_ELEMENTS)
        
        # save resulting dataset
        anm_dir = infold.replace(INPUT_ROOT, ANONYM_DCM_ROOT)
        if not os.path.exists(anm_dir):
            print(f'create directory at {anm_dir}')
            os.makedirs(anm_dir, exist_ok=True) # create a new dir
        anm_path = os.path.join(anm_dir, os.path.basename(filename))
        dataset.save_as(anm_path)
        
        if args.VERBOSE:
            for de in TARGET_ELEMENTS:
                print(filename, dataset.data_element(de))
    
    # convert dcm -> nrrd
    if not os.path.exists(outpath):
        print(f'create directory at {os.path.dirname(outpath)}')
        os.makedirs(os.path.dirname(outpath), exist_ok=True) # create a new dir
    dcm_to_nrrd(infold, outpath, intensity_windowing=True)

print('Done!')
