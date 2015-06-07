import os
import errno
import shutil
import sys

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
    
def get_top_dir():
    return os.path.dirname(os.path.realpath(os.path.join(sys.argv[0],'..')))
    
def initialise_subdirs(dir_names):
    if len(dir_names) == 2 and isinstance(dir_names, list):
        TOP_DIR = get_top_dir()
        directories = tuple([os.path.normpath(os.path.join(TOP_DIR, x)) for x in dir_names]) # Ruturns a list of 2: 0 is input, 1 is output
        if os.path.isdir(directories[1]):
            try:
                os.rmdir(directories[1])
            except OSError as ex:
                if ex.errno == errno.ENOTEMPTY:
                    prompt = 'The output directory "'+directories[1]+'" is not empty. Proceeding will delete all files. Proceed?'
                    answer = query_yes_no(prompt, default=True)
                    if answer:
                        shutil.rmtree(directories[1])
                    else:
                        sys.exit('User aborted')
                        
        for dir_path in directories:
            make_dir_if_not_found(dir_path)
        return directories
    else:
        sys.exit('Bad directories specified')
    
def get_db_path():
    return os.path.join(get_top_dir(), 'assets', 'network.db')