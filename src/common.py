import os
import errno
import shutil
import sys

def root_dir():
    return os.path.dirname(os.path.realpath(os.path.join(sys.argv[0],'..')))


def query_yes_no(question, default=None):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It can be True(yes), False (no) or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == True:
        prompt = " [Y/n] "
    elif default == False:
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return default
        elif choice.lower() in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please answer 'y' or 'n'.\n")

def make_dir_if_not_found(dir_path):
    if os.path.isdir(dir_path) is not True:
        os.makedirs(dir_path)
    return None
    
def delete_dir(dir_path):
    '''
    True if successfully deleted
    False if user abort
    None if path not a directory
    '''
    if os.path.isdir(dir_path):
        try:
            os.rmdir(dir_path)
        except OSError as ex:
            if ex.errno == errno.ENOTEMPTY:
                prompt = 'The directory "'+dir_path+'" is not empty. Proceeding will delete all files. Proceed?'
                answer = query_yes_no(prompt, default=True)
                if answer:
                    shutil.rmtree(dir_path)
                    return True
                else:
                    return False
    return None
    
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