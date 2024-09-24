from datetime import datetime, date, timedelta, timezone
import os
import sys
import json
import csv
from warnings import warn
import logging
DEFAULT_FORMATTER = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
def debug_logger(level=logging.NOTSET):
    logger = logging.getLogger(__name__)
    FORMAT = "[%(asctime)s][%(filename)s:%(lineno)s][%(funcName)20s()] %(message)s"
    logging.basicConfig(format=FORMAT)
    logger.setLevel(level)
    return logger


def frozen_check():
    """
    Checks the running script to see if it is compiled to a single exe.
    If compiled, the resources will be stored in a temp folder.
    If not, then they will be in the script's working directory.
    """
    if getattr(sys, 'frozen', False):
    # Running in a bundle
        bundle_dir = sys._MEIPASS # pylint: disable=no-member
    else:
    # Running in a normal Python environment
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
    return bundle_dir
def debug_dump_variables(obj):
    """
    Dumps variables of provided object to a log file.
    """
    if not hasattr(obj, 'dump_logger'):
        if hasattr(obj, 'batch_folder'):
            root = obj.batch_folder
        else:
            root = os.getcwd()
        obj.dump_logger = obj.setup_logger('Debug Dump', log_file='Debug_Dump', root_dir=root)
    obj.dump_logger.debug(f"Dumping variables for {type(obj.__name__)}:")
    for k, v in vars(obj).items():
        obj.debug_logger.debug(k, v)
        obj.dump_logger.debug(f'{k} : {v}')

def get_case_insensitive_key_value(input_dict, key):
    return next((value for dict_key, value in input_dict.items() if dict_key.lower() == key.lower()), None)

def create_batch_folder(root='', batch_code=None, include_time=False, test=False) -> str:
    """
    Used to set up a batch folder to store any log files or screenshots during an automation run.
    
    Parameters:

    - root: The root directory where the batch folder will be created.
    - batch_code: Optional batch code to use instead of generated one. Overrides include_time parameter.
    - include_time: If True, appends the current time to the batch code.
    - test: If True, uses 'TEST' for the batch folder path; otherwise, uses 'PROD'.

    Returns:
    
    - The path to the created batch folder.
    """
    if batch_code and include_time:
        warn('batch_code and time arguments are not supported together. Ignoring time argument.')
        include_time = False

    db = 'TEST' if test else 'PROD'
    now = datetime.now()
    b_code = batch_code or now.strftime('%Y%m%d')
    b_time = now.strftime('%H%M')
    folder_name = f'{b_code}_{b_time}' if include_time else b_code
    batch_folder = os.path.join(root, 'batch_codes', db, folder_name)
    os.makedirs(batch_folder, exist_ok=True)
    return batch_folder
def setup_logger(name, log_file='log.log', file_format='DAILY',
                     level=logging.DEBUG, formatter=DEFAULT_FORMATTER, root_dir=None) -> logging.Logger:
    """
    Setup a logging file.

    Parameters:

    - name: logger name
    - log_file: filename for the log file.
    - file_format: "DAILY" | "MONTHLY" | "". Will be combined with the log_file filename provided.
    - level: log level for the logger. logging module levels.
    - formatter: logging formatter
    - root_dir: root directory to store the log file

    Default formatter: %(asctime)s - %(name)s - %(levelname)s - %(message)s
    """
    _name = str(name)
    _file_format = str(file_format).upper()
    today = datetime.now()
    _formatter = logging.Formatter(formatter)
    if _file_format == 'DAILY':
        log_date = today.strftime("%Y_%m_%d_")
    elif _file_format == 'MONTHLY':
        log_date = today.strftime("%Y_%m_")
    else:
        log_date = ''
    _log_file = log_date + log_file
    if root_dir:
        _log_file = os.path.join(root_dir, _log_file)
    handler = logging.FileHandler(_log_file, mode='a', encoding='utf-8')
    handler.setFormatter(_formatter)
    logger = logging.getLogger(_name)
    logger.setLevel(level)
    if not logger.hasHandlers():
        logger.addHandler(handler)
    return logger

def read_updated(in_file, obj_type=list()):
    
    """
    Read in a file of already updated records.

    Parameters:
    
    - in_file: file containing the data to read.
    - obj_type: default object type to return if file is empty or doesn't exist.

    Returns:

    - json object from file or empty obj_type object
    """
    updated_records = obj_type
    _file_type = in_file.split('.')[-1].lower()
    if os.path.exists(in_file):
        with open(in_file, 'r', encoding='utf-8') as f:
            if _file_type == 'json':
                updated_records = json.load(f)
            elif _file_type == 'csv':
                c = csv.DictReader(f)
                updated_records = [row for row in c]
            else:
                raise TypeError('File name provided is not an expected type of json or csv.')
    return updated_records

def save_updated(in_file, obj):
    """
    Save a file containing a list of already processed records.

    Parameters:
    
    - in_file: file to use to save
    - obj: json object to write to file. Expects a list containing dictionaries.
    """
    if not obj:
        return
    _file_type = in_file.split('.')[-1].lower()
    with open(in_file, 'w+', encoding='utf-8') as f:
        if _file_type == 'json':
            f.write(json.dumps(obj, indent=4))
        elif _file_type == 'csv':
            c = csv.DictWriter(f, fieldnames=obj[0].keys(), lineterminator='\n')
            c.writeheader()
            c.writerows(obj)
        else:
            raise TypeError('File name provided is not an expected type of json or csv.')
        

def plex_date_formatter(*args: datetime|int, date_offset=0):
    """
    Takes 'normal' date formats and converts them to a Plex web service 
        format (ISO format)
    Can also take a single datetime object.
    2022, 09, 11 -> 2022-09-11T04:00:00Z
    2022, 09, 11, 18, 45 -> 2022-09-11T22:45:00Z
        Next day if hours fall into 20-24 period
    2022, 09, 11, 22 -> 2022-09-12T02:00:00Z
        date_offset arg will add days to the provided time
        Useful when providing just a datetime object to the function
    """
    if isinstance(args[0], (datetime, date)):
        x = args[0]
    else:
        x = datetime(*args).astimezone(datetime.now(timezone.utc).tzinfo)
    # x += timedelta(hours=4)
    x += timedelta(days=date_offset)
    f_date = x.strftime('%Y-%m-%dT%H:%M:%SZ')
    return f_date