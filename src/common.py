import os
import errno
import shutil
import sys
import sqlite3

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
    
def lookup_region_key(name):
    conn = sqlite3.connect(get_db_path())
    region_cursor = conn.cursor()
    region_cursor.execute('SELECT key, name FROM regions WHERE name = ?', (name.lower(),))
    region = region_cursor.fetchone()
    if region:
        return region
    else:
        print '!', name, 'not found in region database'
        raise ValueError