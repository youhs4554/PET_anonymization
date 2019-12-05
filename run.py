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
parser.add_argument('--ANNONYM_DCM_ROOT', type=str, default='DCMs_annonymized', help='root directory of dcm slices.')
parser.add_argument('--ANNONYM_NRRD_ROOT', type=str, default='NRRDs_annonymized', help='root directory of dcm slices.')
parser.add_argument('--VERBOSE', action='store_true', help='If true, convert and save anonymized dcms to nrrd format.')
parser.set_defaults(VERBOSE=False)
args = parser.parse_args()

INPUT_ROOT = args.INPUT_ROOT
ANNONYM_DCM_ROOT = args.ANNONYM_DCM_ROOT
ANNONYM_NRRD_ROOT = args.ANNONYM_NRRD_ROOT

TARGET_ELEMENTS = []
for line in open('target_elements.txt', 'r'):
    TARGET_ELEMENTS.append(line.strip())    
print(f'Start annonimzation process for {TARGET_ELEMENTS}')

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
out_paths = [ os.path.join(ANNONYM_NRRD_ROOT, os.path.basename(infold)+'.nrrd') for infold in input_folders ]

for infold, outpath in tqdm(list(zip(input_folders, out_paths))):
    filename_list = natsorted(glob.glob(infold+'/*'))
    
    # anonymize and save as .dcm
    for filename in filename_list:
        dataset = pydicom.dcmread(filename)
        
        dataset = anonymize(dataset, TARGET_ELEMENTS)
        
        # save resulting dataset
        ann_dir = infold.replace(INPUT_ROOT, ANNONYM_DCM_ROOT)
        if not os.path.exists(ann_dir):
            print(f'create directory at {ann_dir}')
            os.system(f'mkdir -p {ann_dir}') # cretae a new dir
            
        ann_path = os.path.join(ann_dir, os.path.basename(filename))
        dataset.save_as(ann_path)
        
        if args.VERBOSE:
            for de in TARGET_ELEMENTS:
                print(filename, dataset.data_element(de))
    
    # convert dcm -> nrrd
    if not os.path.exists(outpath):
        print(f'create directory at {os.path.dirname(outpath)}')
        os.system(f'mkdir -p {os.path.dirname(outpath)}') # cretae a new dir
    dcm_to_nrrd(infold, outpath, intensity_windowing=True)

print('Done!')