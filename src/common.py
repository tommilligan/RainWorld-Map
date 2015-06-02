import os
import shutil
import sys

def make_dir_if_not_found(dir_path):
    if os.path.isdir(dir_path) is not True:
        os.makedirs(dir_path)
    return None
    
def get_top_dir():
    return os.path.dirname(os.path.realpath(os.path.join(sys.argv[0],'..')))
    
def initialise_subdirs(dir_names):
    directories = list()
    if len(dir_names) == 2 and isinstance(dir_names, list):
        TOP_DIR = get_top_dir()
        directories = [os.path.normpath(os.path.join(TOP_DIR, x)) for x in dir_names] # Ruturns a list of 2: 0 is input, 1 is output
        if os.path.isdir(directories[1]):
            shutil.rmtree(directories[1])
        for dir_path in directories:
            make_dir_if_not_found(dir_path)
    else:
        sys.exit('Bad directories specified')
    return directories