import os
import errno
import shutil
import sys

def root_dir():
    return os.path.dirname(os.path.realpath(os.path.join(sys.argv[0],'..')))

def make_dir_if_not_found(dir_path):
    if os.path.isdir(dir_path) is not True:
        os.makedirs(dir_path)
    return None
    
def delete_dir(dir_path):
    if os.path.isdir(dir_path):
        shutil.rmtree(dir_path)
    return True
    
def renew_dir(dir_path):
    '''
    False if user abort
    True if dir (re)created and is empty
    '''
    user_response = delete_dir(dir_path)
    if user_response is False:
        return False
    else:
        make_dir_if_not_found(dir_path)
        return True

def initialise_subdirs(subdir_names):
    '''Appends subdir names to the root directory, makes subdirs if they don't exist, and returns their absolute paths'''
    dir_paths = tuple([os.path.normpath(os.path.join(root_dir(), x)) for x in subdir_names])
    for dir_path in dir_paths:
        make_dir_if_not_found(dir_path)
    return dir_paths
    
def get_db_path():
    return os.path.join(root_dir(), 'assets', 'network.db')