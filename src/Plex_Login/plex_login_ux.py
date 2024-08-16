import __main__

from warnings import warn

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webelement import WebElement

import os
import sys
from pathlib import Path
import configparser
import json
import csv
try:
    from PIL import Image
    USE_PILLOW = True
except ImportError:
    USE_PILLOW = False
import io
from inspect import currentframe

import urllib.request

import zipfile

from get_file_properties import *

from tkinter import filedialog
from tkinter import messagebox

import logging
from datetime import datetime
import time

import winreg
import re

from typing import Literal

__author__ = 'Dan Sleeman'
__copyright__ = 'Copyright 2020, PMC Automated Login'
__credits__ = ['Helmut N. https://stackoverflow.com/a/7993095']
__license__ = 'GPL-3'
__version__ = '3.0.0'
__maintainer__ = 'Dan Sleeman'
__email__ = 'sleemand@shapecorp.com'
__status__ = 'production'


__all__ = ['WAIT_VISIBLE', 'WAIT_INVISIBLE', 'WAIT_CLICKABLE', 'UX_PLEX_GEARS_SELECTOR',
           'UX_SUCCESS_SELECTOR', 'UX_ERROR_SELECTOR', 'UX_WARNING_SELECTOR']

class Error(Exception):
    pass
class PlexAutomateError(Error):
    """A base class for handling exceptions in this project"""
class NoRecordError(PlexAutomateError):
    pass
class ActionError(PlexAutomateError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.expression = kwargs.get('expression')
        self.message = kwargs.get('message')
class LoginError(PlexAutomateError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.environtment = kwargs.get('environment')
        self.db = kwargs.get('db')
        self.pcn = kwargs.get('pcn')
        self.message = kwargs.get('message')
class UpdateError(PlexAutomateError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.clean_message = args[0].replace('×', '').replace('\n', '').strip()


VISIBLE = 10
INVISIBLE = 20
CLICKABLE = 30
EXISTS = 0
_wait_until= {
    VISIBLE : EC.presence_of_element_located,
    INVISIBLE : EC.invisibility_of_element_located,
    CLICKABLE : EC.element_to_be_clickable,
    EXISTS : None
}

class PlexBanner():
    SUCCESS = 1
    WARNING = 2
    ERROR = 3
    

BANNER_SUCCESS_CLASS = 'plex-banner-success'
BANNER_ERROR_CLASS = 'plex-banner-error'
BANNER_WARNING_CLASS = 'plex-banner-warning'
BANNER_CLASS = 'plex-banner'
BANNER_CLASSES = [
    BANNER_SUCCESS_CLASS,
    BANNER_ERROR_CLASS,
    BANNER_WARNING_CLASS
]

UX_PLEX_GEARS_SELECTOR = (By.XPATH, '//i[@class="plex-waiting-spinner"]')
UX_SUCCESS_SELECTOR = (By.CLASS_NAME, BANNER_SUCCESS_CLASS)
UX_ERROR_SELECTOR = (By.CLASS_NAME, BANNER_ERROR_CLASS)
UX_WARNING_SELECTOR = (By.CLASS_NAME, BANNER_WARNING_CLASS)
UX_BANNER_SELECTOR = (By.CLASS_NAME, BANNER_CLASS)


VALID_ENVIRONMENTS = {'UX', 'CLASSIC'}
VALID_DB = {'TEST', 'PROD'}
SIGNON_URL_PARTS = {'/LAUNCHPAGE', '/MENUCUSTOMER.ASPX', '/MENU.ASPX'}
UX_INVALID_PCN_MESSAGE = '__MESSAGE=YOU+WERE+REDIRECTED+TO+YOUR+LANDING+COMPANY'
PCN_SQL = '''Please create the pcn.json file by running the following SQL report in Plex and save it as a csv file.

SELECT
 P.Plexus_Customer_No
, P.Plexus_Customer_Name
FROM Plexus_Control_v_Customer_Group_Member P

Press OK to select the csv file.'''

class PlexElement(WebElement):
    """
    Subclass of Selenium WebElement with specialized functions for Plex elements.
    """
    
    def __init__(self, webelement, parent_automate):
        super().__init__(webelement._parent, webelement._id)
        self.parent_automate = parent_automate


    def save_element_image(self):
        """
        Save a screenshot of the element. Useful to debug if there are any issues locating the element properly.
        """
        if not USE_PILLOW:
            warn('Pillow module is not installed. Cannot save element images.', category=ImportWarning, stacklevel=2)
            return
        image_binary = self.screenshot_as_png
        img = Image.open(io.BytesIO(image_binary))
        element_id = self.id[-8:]
        session = self.parent.session_id[-5:]
        name = self.accessible_name
        if name == '':
            name = 'No_Name'
        if not hasattr(self.parent_automate, 'batch_folder'):
            self.parent_automate.create_batch_folder()
            self.parent_automate.screenshot_folder = os.path.join(self.parent_automate.batch_folder, 'screenshots')
            os.mkdir(self.parent_automate.screenshot_folder)
        img.save(os.path.join(self.parent_automate.screenshot_folder, f"{session}_{element_id}_{name}_screenshot.png"))
    
    
    def sync_checkbox(self, bool_state):
        """
        Sync a checkbox to the provided checked state.

        parameters

            : bool_state - Checked state to make the checkbox.
        """
        if not type(bool_state) == bool:
            bool_state = bool(int(bool_state))
        check_state = self.get_property('checked')
        if not check_state == bool_state:
            self.parent_automate._debug_print(f'{self.get_property("name")} - Checkbox state: {check_state}. Clicking to make it {bool_state}.', level=1)
            self.click()
        else:
            self.parent_automate._debug_print(f'{self.get_property("name")} - Checkbox state: {check_state} matches provided state: {bool_state}.', level=0)


    def sync_textbox(self, text_content, clear=False):
        """
        Sync a textbox with the provided value.

        parameters

            : text_content - Desired value for the text box
            : clear - Clear out the text box if providing a blank text_content
        """
        if not text_content and not clear:
            return
        text = self.get_property('value')
        if not text == text_content:
            text_content = text_content.replace('\t', ' ') # The input will break if sending tab characters. This should only happen when a copy/paste from word/excel was done on the original field text.
            self.parent_automate._debug_print(f'{self.get_property("name")} - Current text: {text}. Replacing with provided text: {text_content}', level=1)
            self.clear()
            self.send_keys(text_content)
            self.send_keys(Keys.TAB)
        else:
            self.parent_automate._debug_print(f'{self.get_property("name")} - Current text: {text}. Matches provided text: {text_content}', level=0)


    def sync_picker(self, text_content, clear=False, date=False):
        """
        Sync the picker element to the provided value.

        parameters

            : text_content - Desired value for the picker
            : clear - Clear out the picker if providing a blank text_content
            : date - If the picker is a date picker. This should be detected automatically, but can be forced if behavior is unexpected.
        """
        multi = False
        matching = False
        picker_type = self.get_attribute('class')
        if picker_type == 'input-sm':
            date = True
        if not text_content and not clear:
            return
        if self.tag_name == 'select':
            self.parent_automate._debug_print(f'{self.get_property("name")} - Picker type is selection list.', level=0)
            _select = Select(self)
            _current_selection = _select.first_selected_option.text
            if _current_selection == text_content:
                self.parent_automate._debug_print(f'{self.get_property("name")} - Picker selection: {_current_selection} matches {text_content}', level=0)
                return
            for o in _select.options:
                if o.text == text_content:
                    matching = True
            if matching:
                self.parent_automate._debug_print(f'{self.get_property("name")} - Matching option found. Picking {text_content}', level=1)
                _select.select_by_visible_text(text_content)
                self.send_keys(Keys.TAB)
            else:
                self.parent_automate._debug_print(f'{self.get_property("name")} - No matching selection available for {text_content}', level=1)
                raise NoRecordError(f'{self.get_property("name")} - No matching selection available for {text_content}')
            return
        else:
            try:
                # We would then need to locate if a value is already input and check the title attribute
                self.parent_automate._debug_print(f'{self.get_property("name")} - Trying to locate an existing selected item.', level=0)
                selected_element = self.parent_automate.wait_for_element((By.XPATH, "preceding-sibling::div[@class='plex-picker-selected-items']"), driver=self, timeout=1)
                if selected_element:
                    self.parent_automate._debug_print(f'{self.get_property("name")} - Selected item detected', level=0)
                    selected_item = self.parent_automate.wait_for_element((By.CLASS_NAME, "plex-picker-item-text"), driver=selected_element)
                    current_text = selected_item.get_property('textContent')
                    if current_text != text_content:
                        self.parent_automate._debug_print(f'{self.get_property("name")} - Current text: {current_text} does not match provided text: {text_content}', level=1)
                        self.send_keys(Keys.BACKSPACE) # Backspace will convert the picker item to normal text.
                        self.clear()
                    else:
                        self.parent_automate._debug_print(f'{self.get_property("name")} - Current text: {current_text} matches provided text: {text_content}.', level=0)
                        matching = True
                        return
            except (NoSuchElementException, TimeoutException):
                self.parent_automate._debug_print(f'{self.get_property("name")} - No initial selected item.', level=0)
            finally:
                if matching:
                    self.parent_automate._debug_print(f'{self.get_property("name")} - Existing value matches.', level=0)
                    return
                self.send_keys(text_content)
                self.send_keys(Keys.TAB)
                try:
                    if date:
                        self.parent_automate._debug_print(f'{self.get_property("name")} - Picker is a date filter.', level=0)
                        self.parent_automate.wait_for_element((By.XPATH, "preceding-sibling::div[@class='plex-picker-item']"), driver=self, timeout=5)
                        self.parent_automate._debug_print(f'{self.get_property("name")} - Date picker has been filled in with {text_content}', level=1)
                    else:
                        self.parent_automate.wait_for_element((By.XPATH, "preceding-sibling::div[@class='plex-picker-selected-items']"), driver=self, timeout=5)
                        self.parent_automate._debug_print(f'{self.get_property("name")} - Normal picker has been filled in with {text_content}', level=1)
                except (TimeoutException, NoSuchElementException) as e:
                    try:
                        self.parent_automate._debug_print(f'{self.get_property("name")} - No auto filled item, checking for a popup window.', level=0)
                        popup = self.parent_automate.wait_for_element((By.CLASS_NAME, 'modal-dialog.plex-picker'), timeout=3)
                        if 'plex-picker-multi' in popup.get_attribute('class'):
                            self.parent_automate._debug_print(f'{self.get_property("name")} - Picker is a multi-picker', level=0)
                            multi = True
                        self.parent_automate.wait_for_gears()
                        items = popup.find_elements(By.CLASS_NAME, 'plex-grid-row')
                        if not items:
                            result_text = popup.find_element(By.TAG_NAME, 'h4').get_property('textContent')
                            if 'No records' in result_text:
                                self.parent_automate._debug_print(f'{self.get_property("name")} - No records found for {text_content}', level=1)
                                footer = popup.find_element(By.CLASS_NAME, 'modal-footer')
                                _cancel = footer.find_element(By.LINK_TEXT, 'Cancel')
                                _cancel.click()
                                raise NoRecordError(f'No records found for {text_content}')
                        for i in items:
                            if i.text != text_content:
                                continue
                            self.parent_automate._debug_print(f'{self.get_property("name")} - Found matching item with text {i.text}.', level=1)
                            i.click()
                            if multi:
                                self.parent_automate._debug_print(f'{self.get_property("name")} - Multi-picker, clicking ok on the popup window.', level=1)
                                self.parent_automate.ux_click_button('Ok', driver=popup)
                                self.parent_automate._debug_print(f'{self.get_property("name")} - Multi-picker, clicked ok on the popup window.', level=1)
                                
                    except (TimeoutException, NoSuchElementException) as e:
                        self.parent_automate._debug_print(f'{self.get_property("name")} - No matching elements found for {text_content}', level=1)



class PlexAutomate(object): # TODO Convert to Plex driver. Create common function library to handle things like batch code creation and automation specific tasks.
    '''
    parameters
        : environment - Accepted options are Classic and UX.
            Determines how the program will log in and changes some functionality
        : pcn_path - path to the pcn.json file. Only required for classic login.
            Used to find the PCN menu node using the PCN name.
                Default expected path is ./resources/pcn.json
        : chromedriver_override - specify a specific Chromedriver version to use instead of the most current.
        : debug : bool - Whether or not to print debug messages
        : debug_level : int - Level for printing debug message. Default 0, print everything.
    '''
    def __init__(self, environment, *args, **kwargs):
        self.__dict__.update(kwargs)
        if 'cumulus' in kwargs.keys():
            warn('cumulus keyword is deprecated. Does not function with IAM logins. This argument will be ignored.', DeprecationWarning, stacklevel=2)
        if 'legacy_login' in kwargs.keys():
            warn('legacy_login keyword is deprecated. Non IAM logins are not supported by Plex. This argument will be ignored.', DeprecationWarning, stacklevel=2)
        self.pcn_file_path = kwargs.get('pcn_file_path', Path('resources/pcn.json'))
        self.debug = kwargs.get('debug', False)
        self.debug_level = kwargs.get('debug_level', 0)
        self.environment = environment.upper()
        self.chromedriver_override = kwargs.get('chromedriver_override')
        self.single_pcn = False
        if self.environment not in VALID_ENVIRONMENTS:
            raise ValueError(f"{type(self).__name__}: environment must be one of {VALID_ENVIRONMENTS}")
        if self.environment == 'CLASSIC':
            while not self.pcn_file_path.is_file():
                confirm = messagebox.askokcancel(title='Classic PCN reference file is missing',
                                                message=PCN_SQL)
                if not confirm:
                    messagebox.showinfo(title='User Selected Cancel',
                                        message='The program will now close.')
                    sys.exit("Process quit by user")
                self.file_path = filedialog.askopenfilename()
                if self.file_path:
                    self._csv_to_json(self.file_path)
            self.pcn_dict = {}
            with open(self.pcn_file_path, 'r', encoding='utf-8') as pcn_config:
                self.pcn_dict = json.load(pcn_config)
        if self.environment == 'UX':
            self.plex_main = 'cloud.plex.com'
            self.plex_prod = ''
            self.plex_test = 'test.'
            self.sso = '/sso'
        else:
            self.plex_main = '.plexonline.com'
            self.plex_prod = 'www'
            self.plex_test = 'test'
            self.sso = '/signon'
        self.plex_log_id = 'username'
        self.plex_log_pass = 'password'
        self.plex_log_comp = 'companyCode'
        self.plex_login = 'loginButton'
        
        self._frozen_check()
        self.resource_path = os.path.join(self.bundle_dir, 'resources')
        if not os.path.exists(self.resource_path):
            os.mkdir(self.resource_path)
        self.chrome_download_dir = os.path.join(self.bundle_dir, 'downloads')
        if not os.path.exists(self.chrome_download_dir):
            os.mkdir(self.chrome_download_dir)
        self.latest_chromedriver_version_file = os.path.join(self.resource_path, 'driver_version.txt')
        self._read_driver_version()


    def _debug_print(self, *args, **kwargs):
        if self.debug:
            _debug_level = kwargs.get('level', 0)
            if _debug_level >= self.debug_level:
                cf = currentframe()
                print(datetime.now(), cf.f_back.f_lineno, *args)


    def _debug_dump_variables(self):
        """
        Dumps variables of current PlexAutomate object to a log file.
        """
        if not hasattr(self, 'dump_logger'):
            if hasattr(self, 'batch_folder'):
                root = self.batch_folder
            else:
                root = os.getcwd()
            self.dump_logger = self.setup_logger('Debug Dump', log_file='Debug_Dump', root_dir=root)
        self.dump_logger.debug(f"Dumping variables for {type(self.__name__)}:")
        for k, v in vars(self).items():
            self._debug_print(k, v, level=0)
            self.dump_logger.debug(f'{k} : {v}')


    def _chrome_check(self):
        chrome_key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "ChromeHTML\\shell\\open\\command", 0, winreg.KEY_READ)
        command = winreg.QueryValueEx(chrome_key, "")[0]
        winreg.CloseKey(chrome_key)
        chrome_browser = re.search("\"(.*?)\"", command)
        if chrome_browser:
            chrome_browser = chrome_browser.group(1)
            print(f'Chrome browser install location: {chrome_browser}')
        cb_dictionary = getFileProperties(chrome_browser) # returns whole string of version (ie. 76.0.111)
        self.chrome_browser_version = cb_dictionary['FileVersion'].split('.')[0] # substring version to capabable version (ie. 77 / 76)
        self.full_chrome_browser_version = cb_dictionary['FileVersion']
        print(f'Chrome base version: {self.chrome_browser_version} | Full Chrome version: {self.full_chrome_browser_version}')


    def _get_case_insensitive_key_value(self, input_dict, key):
        return next((value for dict_key, value in input_dict.items() if dict_key.lower() == key.lower()), None)


    def _csv_to_json(self, csv_file):
        '''
        Function to take a csv file from Plex and create a
        PCN JSON file that can be used to log into specific PCNs
            if the user has multiple PCN access.
        This should only be called on initialization if
            the pcn.json file does not exist yet.
        Only required for classic logins.
        '''
        _pcn_dict = {}
        with open(csv_file, 'r', encoding='utf-8-sig') as c:
            r = csv.DictReader(c)
            for row in r:
                if not row:
                    continue
                _pcn_dict[self._get_case_insensitive_key_value(row, 'plexus_customer_no')] = self._get_case_insensitive_key_value(row, 'plexus_customer_name')
        if not Path('resources').is_dir():
            Path.mkdir('resources')
        with open('resources/pcn.json', 'w+', encoding='utf-8') as j:
            j.write(json.dumps(_pcn_dict, indent=4, ensure_ascii=False))


    def _frozen_check(self):
        '''
        Checks the running script to see if it is compiled to a single exe.
        If compiled, the resources will be stored in a temp folder.
        If not, then they will be in the script's working directory.
        '''
        if getattr(sys, 'frozen', False):
        # Running in a bundle
            self.bundle_dir = sys._MEIPASS # pylint: disable=no-member
        else:
        # Running in a normal Python environment
            self.bundle_dir = os.path.dirname(os.path.abspath(__main__.__file__))
        return self.bundle_dir
    
    def _read_driver_version(self):
        if os.path.exists(self.latest_chromedriver_version_file):
            with open(self.latest_chromedriver_version_file, 'r') as f:
                self.latest_downloaded_chromedriver_version = f.read()
                self._debug_print(f'Latest downloaded chromedriver version: {self.latest_downloaded_chromedriver_version}', level=0)
        else:
            self._debug_print(f'Latest downloaded chromedriver file not detected. Setting version to None.', level=0)
            self.latest_downloaded_chromedriver_version = None

    def _save_driver_version(self, version):
        self._debug_print(f'Saving latest downloaded chromedriver version: {version}', level=0)
        with open(self.latest_chromedriver_version_file, 'w+') as f:
            f.write(version)

    def _download_chrome_driver(self, version=None):
        '''
        Downloads the chromedriver that will allow selenium to function.
        '''
        text_path =os.path.join(self.resource_path, 'chromedriver.txt')
        zip_path =os.path.join(self.resource_path, 'chromedriver.zip')
        chromedriver_url = None
        url = 'https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-milestone-with-downloads.json'
        urllib.request.urlretrieve(url, text_path)
        with open(text_path, 'r') as f:
            chrome_releases = json.load(f)
        latest_chromedriver_version = chrome_releases['milestones'][self.chrome_browser_version]['downloads']['chromedriver']#['platform']
        
        for x in latest_chromedriver_version:
            if x['platform'] == 'win64':
                chromedriver_url = x['url']
        if chromedriver_url:
            url = chromedriver_url
            if self.latest_downloaded_chromedriver_version == url:
                self._debug_print(f'Latest downloaded chromedriver version matches with lasted on web. Skipping download.', level=0)
                return
            else:
                self._save_driver_version(url)
        else:
            if version:
                self.full_chrome_browser_version = version
            url = f'https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/{self.full_chrome_browser_version}/win64/chromedriver-win64.zip'
        self._debug_print(f'Downloading chromedriver version at: {url}', level=0)
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            self._debug_print(f'Exctracting chromedriver to: {self.resource_path}')
            zip_ref.extractall(self.resource_path)


    def wait_for_element(self, selector, driver=None, timeout=15, type=VISIBLE) -> PlexElement:
        """
        Wait until an element meets specified criteria.
        Wrapper for Selenium WebDriverWait function for common Plex usage.

        parameters

            : selector - Element selector to wait for
            : driver - root WebDriver to use for locating the element
            : timeout - How long to wait until raising an exception
            : type - Type of wait to be used
                : VISIBLE
                : INVISIBLE
                : CLICKABLE

        returns

            : PlexElement object
        """
        try:
            if not driver:
                driver = self.driver
            if type == VISIBLE:
                element_present = EC.presence_of_element_located(selector)
                WebDriverWait(driver, timeout).until(element_present)
                return PlexElement(driver.find_element(*selector), self)
            elif type == INVISIBLE:
                element_present = EC.invisibility_of_element_located(selector)
                WebDriverWait(driver, timeout).until(element_present)
            elif type == CLICKABLE:
                element_clickable = EC.element_to_be_clickable(selector)
                WebDriverWait(driver, timeout).until(element_clickable)
                return PlexElement(driver.find_element(*selector), self)
        except (TimeoutException, StaleElementReferenceException, NoSuchElementException):
            raise

    def wait_for_banner(self) -> PlexElement:
        try:
            loop = 0
            banner = self.wait_for_element(UX_BANNER_SELECTOR)
            banner_class = banner.get_attribute('class')
            while banner_class == BANNER_CLASS and loop <= 10:
                time.sleep(1)
                banner = self.wait_for_element(UX_BANNER_SELECTOR)
                banner_class = banner.get_attribute('class')
                loop += 1
            if BANNER_SUCCESS_CLASS in banner_class:
                self._banner_handler(PlexBanner.SUCCESS)
            elif BANNER_WARNING_CLASS in banner_class:
                self._banner_handler(PlexBanner.WARNING)
            elif BANNER_ERROR_CLASS in banner_class:
                self._banner_handler(PlexBanner.ERROR)
            else:
                raise UpdateError(f'Unexpected banner type detected. Found {banner_class}. Expected one of {BANNER_CLASSES}')
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
            raise UpdateError('No banner detected.')
        

    def _banner_handler(self, banner_type: PlexBanner):
        if banner_type == PlexBanner.SUCCESS:
            return 
        else:
            banner = self.wait_for_element(UX_BANNER_SELECTOR)
            banner_text = banner.get_property('textContent')
            raise UpdateError(banner_text)


    def wait_for_gears(self, loading_timeout=10):
        """
        Wait for the spinning gears image to appear and wait for it to dissappear.

        This should be called after searching or updating a screen.
        
        Essentially any time you are clicking a button which would cause the page to load.

        The gears sometimes dissappear quicker than can be detected. 
            If the gears are not detected at the begining, the end timeout is shorter.

        parameters

            : loading_timeout - how long to wait until the gears disappear once visible.
                Use this if the screen usually takes a long time to load/search.
        """
        gears_visible = False
        if self.environment == 'CLASSIC':
            warn(f'This function only works in UX.')
            return
        try:
            self.wait_for_element(UX_PLEX_GEARS_SELECTOR, type=VISIBLE, timeout=1)
            gears_visible = True
        except:
            None
        try:
            if gears_visible:
                timeout = loading_timeout
            else:
                timeout = 1
            self.wait_for_element(UX_PLEX_GEARS_SELECTOR, type=INVISIBLE, timeout=timeout)
        except:
            None


    def login(self, username, password, company_code, pcn, db, headless=False):
        """
        Log into Plex.

        Downloads the latest chromedriver if different than the latest version available.

        parameters

            : username - Username
            : password - Password
            : company_code - Login company code used
            : pcn - home PCN for the user. If the user account does not have multiple PCNs, this wouldn't be used.
            : db - Plex database. Test or Prod
            : headless - Launch chrome in headless mode. Note: This does not behave well with UX screens.
        
        returns

            : driver - WebDriver for main operations
            : url_comb - combined URL part for the environment (UX, Classic)
            : token - Session token from URL
        """
        self._chrome_check()
        self.db = db.upper()
        self.pcn = pcn
        if hasattr(self, 'pcn_dict'):
            self.pcn_name = self.pcn_dict[self.pcn]
        else:
            self.pcn_name = self.pcn
        if self.db not in VALID_DB:
            raise ValueError(f"{type(self).__name__}: db must be one of {VALID_DB}")
        self._download_chrome_driver(self.chromedriver_override)
        executable_path = os.path.join(self.resource_path, 'chromedriver-win64', 'chromedriver.exe')
        os.environ['webdriver.chrome.driver'] = executable_path
        chrome_options = Options()
        chrome_options.add_argument("--log-level=3")
        if headless:
            self._debug_print(f'Running chrome in headless mode.', level=0)
            chrome_options.add_argument("--headless")
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": f"{self.chrome_download_dir}",
            "download.prompt_for_download": False,
            })
        service = Service(executable_path=executable_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        if self.db == 'PROD':
            db = self.plex_prod
        else:
            db = self.plex_test
        self.driver.get(f'https://{db}{self.plex_main}{self.sso}')
        # Test for new login screen
        try:
            self.wait_for_element((By.XPATH, '//img[@alt="Rockwell Automation"]'), timeout=4)
            self._debug_print(f'New Rockwell IAM login screen detected.', level=0)
            rockwell = True
        except (NoSuchElementException, TimeoutException):
            self.wait_for_element((By.XPATH, '//img[@alt="Plex"]'))
            rockwell = False
        if rockwell:
            id_box = self.wait_for_element((By.NAME, self.plex_log_id), type=CLICKABLE)
            if id_box == self.driver.switch_to.active_element:
                self._debug_print(f'Filling in username.', level=0)
                id_box.send_keys(username)
                id_box.send_keys(Keys.TAB)
            company_box = self.wait_for_element((By.NAME, self.plex_log_comp), type=CLICKABLE, ignore_exception=True, timeout=5)
            if company_box == self.driver.switch_to.active_element:
                self._debug_print(f'Company box is active. Filling in with supplied data.')
                company_box.click()
                company_box.clear()
                company_box.send_keys(company_code)
                company_box.send_keys(Keys.TAB)
            pass_box = self.wait_for_element((By.NAME, self.plex_log_pass), type=CLICKABLE)
            if pass_box == self.driver.switch_to.active_element:
                self._debug_print(f'Filling in password.', level=0)
                pass_box.send_keys(password)
        else:
            self._debug_print(f'Plex IAM login screen detected.', level=0)
            id_box = self.driver.find_element(By.NAME, self.plex_log_id)
            pass_box = self.driver.find_element(By.NAME, self.plex_log_pass)
            company_code_box = self.driver.find_element(By.NAME, self.plex_log_comp)
            company_code_box.send_keys(company_code)
            company_code_box.send_keys(Keys.TAB)
            id_box.send_keys(username)
            id_box.send_keys(Keys.TAB)
            pass_box.send_keys(password)
        login_button = self.wait_for_element((By.ID, self.plex_login), type=CLICKABLE)
        login_button.click()
        self.first_login = True
        try:
            if self.environment == 'CLASSIC':
                self._classic_popup_handle()
            self._pcn_select()
            self.url_token = self.pcn_switch(self.pcn)
            return (self.driver, self.url_comb, self.url_token)
        except LoginError:
            raise


    def _classic_popup_handle(self):
        main_window_handle = None
        while not main_window_handle:
            self._debug_print('looking for main window')
            main_window_handle = self.driver.current_window_handle
        signin_window_handle = None
        timeout_signin = 30
        timeout_start = time.time()
        login_attempt = 0
        while not signin_window_handle and time.time() < timeout_start + timeout_signin:
            self._debug_print(f'Searching for classic signin window', level=0)
            for handle in self.driver.window_handles:
                if handle != main_window_handle:
                    self._debug_print(f'Found classic login window', level=0)
                    signin_window_handle = handle
                    break
                else:
                    timeout_signin -= 1
                    login_attempt += 1
                    time.sleep(1)
                    self._debug_print(f'Login attempt: {login_attempt}', level=0)
        if not signin_window_handle:
            raise LoginError('Failed to find Plex signon window. Please validate login credentials and try again.', environment = self.environment, db= self.db, pcn= self.pcn_name, message='Failed to find Plex signon window. Please validate login credentials and try again.')
        self.driver.switch_to.window(signin_window_handle)


    def _classic_pcn_switch(self, pcn=None):
        if not pcn:
            pcn = self.pcn
        _pcn_name = self.pcn_dict[pcn]
        _url = self.driver.current_url
        if self.single_pcn:
            warn(f'This account only has access to one PCN.', loglevel=2)
            return
        if not 'MENUCUSTOMER.ASPX' in _url.upper() and self.first_login:
            self._debug_print(f'Single PCN account detected.', level=0)
            self.single_pcn = True
            self.first_login = False
            return (self.driver, self.url_comb, "None")
        if not self.single_pcn and not self.first_login:
            self.driver.get(f'{self.url_comb}/Modules/SystemAdministration/MenuSystem/MenuCustomer.aspx')
        try:
            try:
                self.driver.find_element(By.XPATH, f'//img[@alt="{_pcn_name}"]').click()
                self._debug_print(f'PCN found by logo text: {_pcn_name}.', level=0)
            except NoSuchElementException: # PCN does not have a logo, find the URL link instead.
                try:
                    self.driver.find_element(By.XPATH, f'//*[contains(text(), "{_pcn_name}")]').click()
                    self._debug_print(f'PCN found by link text: {_pcn_name}.', level=0)
                except NoSuchElementException:
                    raise LoginError(self.environment, self.db, _pcn_name, f'Unable to locate PCN. Verify you have access.')
            finally:
                self.first_login = False
        except (IndexError, KeyError):
            raise LoginError(self.environment, self.db, _pcn_name, 'PCN is not present in reference file. Verify pcn.json data.')


    def _ux_pcn_switch(self, pcn=None):
        if not pcn:
            pcn = self.pcn
        if self.first_login:
            self.first_login = False
            return
        self.url_token = self.token_get()
        self.driver.get(f'{self.url_comb}/SignOn/Customer/{pcn}?{self.url_token}')
        if UX_INVALID_PCN_MESSAGE in self.driver.current_url.upper():
            raise LoginError(self.environment, self.db, pcn, f'Unable to login to PCN. Verify you have access.')


    def _pcn_select(self):
        url = self.driver.current_url
        if not any(url_part in url.upper() for url_part in SIGNON_URL_PARTS):
            raise LoginError(self.environment, self.db, self.pcn_name, 'Login page not detected. Please validate login credentials and try again.')
        url_split = url.split('/')
        url_proto = url_split[0]
        url_domain = url_split[2]
        if self.environment == 'UX':
            self.url_token = self.token_get()
            self.url_comb = f'{url_proto}//{url_domain}'
        else:
            self.url_token = url_split[3]
            self.url_comb = f'{url_proto}//{url_domain}/{self.url_token}'


    def token_get(self, *args):
        """
        Returns the session token for Plex

        If using UX, the whole query string is returned.
            I.E. "__asid=######"
        
        usage
            ::

                pa = PlexAutomate('UX')
                # Log in here
                token = pa.token_get() # with UX, you must get the new token after switching PCNs
                pa.driver.get(f'{pa.url_comb}/Engineering/Part?{token}')
        """
        url = self.driver.current_url
        url_split = url.split('/')
        if self.environment == 'UX':
            self.url_token = url.split('?')[1]
            if '&' in self.url_token:
                self.url_token = [x for x in self.url_token.split('&') if 'asid' in x][0]
                # self.url_token = self.url_token.split('&')[0]
        else:
            self.url_token = url_split[3]
        return self.url_token


    def pcn_switch(self, pcn):
        """
        Switch to a different PCN, provided you have access.

        parameters
        
            : pcn - PCN number for the destination PCN.
        """
        pcn = str(pcn)
        self._debug_print(f'Switching to PCN: {pcn}.', level=0)
        if self.environment == 'UX':
            self._ux_pcn_switch(pcn)
        else:
            self._classic_pcn_switch(pcn)
        return self.token_get()
    def switch_pcn(self, pcn):
        return self.pcn_switch(pcn)


    def ux_click_button(self, name, driver=None):
        """
        Clicks a standard button when given the text.
        
        Mainly used for clicking the Ok and Apply buttons.

        Can be used for Search buttons as well.
        
        parameters

            : name - Text of the button to click
            : driver - webdriver root to use if different than default

        usage
            If you don't provide the root driver, then the main page's Ok button will be clicked and not the popup window's button.
            ::
            
                popup_window = driver.find_element(By.ID, 'popupID')
                ux_click_button('Ok', driver=popup_window)
                
        """
        if self.environment == "CLASSIC":
            warn("This function only works in UX.", stacklevel=2)
            return
        if not driver:
            driver = self.driver
        buttons = driver.find_elements(By.TAG_NAME, 'button')
        for b in buttons:
            if b.get_property('textContent') == name:
                self._debug_print(f'Button found with matching text: {name}', level=0)
                b.click()
                return


    def ux_click_action_bar_item(self, item, sub_item=None):
        """
        Clicks on an action bar item.

        parameters
        
            : item - Text for the item to click
            : sub_item - Text for the item if it is within a dropdown from clicking the item first.
        
        """
        action_bar = self.wait_for_element((By.CLASS_NAME, 'plex-actions'))
        more = False
        try:
            more_box = action_bar.find_element(By.LINK_TEXT, f"More")
            style = more_box.find_element(By.XPATH, 'ancestor::li').get_dom_attribute('style')
            if 'none' in style:
                self._debug_print(f'More link found, but is not displayed to the user.', level=0)
                None
            else:
                self._debug_print(f'More link found.', level=0)
                more = True
        except NoSuchElementException:
            self._debug_print(f'No element found for more link.', level=0)
            None
        if more:
            self._debug_print(f'Locating more button', level=0)
            more_box.click()
            self.wait_for_element((By.CLASS_NAME, "plex-subactions.open"))
            
            action_bar = self.wait_for_element((By.CLASS_NAME, 'plex-actions-more'))
            self._debug_print("Clicking more button.", level=0)
        if sub_item:
            self._debug_print("Link is subitem.", level=0)
            action_items = action_bar.find_elements(By.CLASS_NAME, "plex-actions-has-more")
            for a in action_items:
                span_text = a.find_elements(By.TAG_NAME, 'span')
                for s in span_text:
                    if s.get_property('textContent') == item:
                        s.find_element(By.XPATH, "ancestor::a").click()
            action_bar.find_element(By.LINK_TEXT, sub_item).click()
        else:
            self._debug_print("Link is not subitem.", level=0)
            action_item = self.wait_for_element((By.LINK_TEXT, item), type=CLICKABLE)
            action_item.click()


    def edi_upload(self, file_list):
        """
        Takes a list of files and uploads them to the EDI log.
        
        Should be logged in to the PCN first before calling.
        """
        if self.environment == 'UX':
            warn("This function only works in classic.", loglevel=2)
            return
        self.driver.get(f'{self.url_comb}/EDI/EDI_Log2.asp')
        for f in file_list:
            self.driver.get(f'{self.url_comb}/Upload_Apps/EDI_Upload_Process.asp')
            input_box = self.wait_for_element((By.ID, 'FILE1'))
            input_box.send_keys(f)
            try:
                # Wait until the screen returns back to the EDI log, assumes that it was uploaded.
                self.wait_for_element((By.ID, 'flttxtCustomer_No'), timeout=50)
            except TimeoutException:
                continue


    def create_batch_folder(self, batch_code=None, time=False, test=False):
        """
        Used to set up a batch folder to store any log files or screenshots during an automation run.
        """
        if batch_code and time:
            warn('batch_code and time arguments are not supported together. Ignoring time argument.')
            time = False
        if hasattr(self, 'db'):
            db = self.db
        elif test:
            db = 'TEST'
        else:
            db = 'PROD'
        self.batch_code = datetime.now().strftime('%Y%m%d')
        self.batch_time = datetime.now().strftime('%H%M')
        if batch_code:
            self.batch_code = batch_code
        if time:
            self.batch_folder = os.path.join(self.bundle_dir, 'batch_codes', db, f'{self.batch_code}_{self.batch_time}')
        else:
            self.batch_folder = os.path.join(self.bundle_dir, 'batch_codes', db, f'{self.batch_code}')
        if not os.path.exists(self.batch_folder):
            os.makedirs(self.batch_folder)


    def setup_logger(self, name, log_file='log.log', file_format='DAILY',
                     level=logging.DEBUG, formatter=None, root_dir=None):
        """
        To setup as many loggers as you want.

        The log file name will have the date pre-pended to whatever is added as the
        log file name

        Default formatter %(asctime)s - %(name)s - %(levelname)s - %(message)s
        """
        if formatter == None:
            formatter = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
    
    def read_updated(self, in_file):
        updated_records = []
        if os.path.exists(in_file):
            with open(in_file, 'r', encoding='utf-8') as f:
                updated_records = json.load(f)
        return updated_records or []
    
    def save_update(self, in_file, dict):
        with open(in_file, 'w+', encoding='utf-8') as f:
            f.write(json.dumps(dict, indent=4))


class Plex(PlexAutomate):
    '''
    The main variables required to pass to the class.
    environment - accepted options are Classic and UX.
                  Determines how the program will log in
    user_id - the Plex user ID
    password - the Plex password
    company_code - the Plex company code
    pcn - Optional. PCN number that would need to be selected after login.
          Will not be needed if the account only has one PCN access or
          if using a UX login and operating in the account's main PCN
    db - Optional. Default to 'test'. Accepted values are 'test' and 'prod'.
         Can be changed via the config file after it is created.
    use_config - True/False on whether to use the config file for login details
    pcn_path - path to the pcn.json file
    '''
    def __init__(self, environment='UX', user_id='', password='', company_code='', pcn='',
                 db='test', pcn_path=Path('resources/pcn.json'),
                 utility=False, chromedriver_override=None, **kwargs):
        warn(f'{type(self).__name__} will be depreciated. Migrate to using PlexAutomate class instead.', DeprecationWarning, stacklevel=2)
        self.chrome_check()
        self.bundle_dir = self.frozen_check()
        self.resource_path = os.path.join(self.bundle_dir, 'resources')
        if 'cumulus' in kwargs.keys():
            warn('cumulus will be deprecated. Does not function with IAM logins.', DeprecationWarning, stacklevel=2)
        self.cumulus = kwargs.get('cumulus', False)
        if 'legacy_login' in kwargs.keys():
            warn('legacy_login will be deprecated. Non IAM logins are not supported by Plex.', DeprecationWarning, stacklevel=2)
        self.legacy_login = kwargs.get('legacy_login', False)
        if 'use_config' in kwargs.keys():
            warn('use_config keyword will be deprecated.', DeprecationWarning, stacklevel=2)
        self.use_config = kwargs.get('legacy_login', False)
        self.environment = environment.upper()
        self.user_id = user_id
        self.password = password
        self.company_code = company_code
        self.pcn = pcn
        self.db = db.upper()
        self.pcn_path = pcn_path
        self.chromedriver_override = chromedriver_override
        if self.environment not in VALID_ENVIRONMENTS:
            raise ValueError("Plex: environment must be one of %r." % VALID_ENVIRONMENTS)
        if self.db not in VALID_DB:
            raise ValueError("Plex: db must be one of %r." % VALID_DB)
        if utility:
            return
        elif self.environment == 'CLASSIC':
            while not pcn_path.is_file():
                confirm = messagebox.askokcancel(title='PCN file is missing',
                                                message=PCN_SQL)
                if not confirm:
                    messagebox.showinfo(title='User Selected Cancel',
                                        message='The program will now close.')
                    sys.exit("Process quit by user")
                self.file_path = filedialog.askopenfilename()
                if self.file_path:
                    self.csv_to_json(self.file_path)
            self.pcn_dict = {}
            with open(self.pcn_path, 'r', encoding='utf-8') as pcn_config:
                self.pcn_dict = json.load(pcn_config)
        self.current = set()
        # Sets the variables for the login operation based on
        # UX or classic environment
        if self.environment == 'UX':
            self.plex_main = 'cloud.plex.com'
            self.plex_prod = ''
            self.plex_test = 'test.'
            self.plex_log_id = 'userId'
            self.plex_log_pass = 'password'
            self.plex_log_comp = 'companyCode'
            self.plex_login = 'loginButton'
            self.sso = '/sso'
        else:
            self.plex_main = '.plexonline.com'
            self.plex_prod = 'www'
            self.plex_test = 'test'
            self.plex_log_id = 'txtUserID'
            self.plex_log_pass = 'txtPassword'
            self.plex_log_comp = 'txtCompanyCode'
            self.plex_login = 'btnLogin'
            self.sso = '/signon'
        if not self.legacy_login:
            self.plex_log_id = 'username'
            self.plex_log_pass = 'password'
            self.plex_log_comp = 'companyCode'
            self.plex_login = 'loginButton'
        self.download_chrome_driver(self.chromedriver_override)
        self.config()
    
    def chrome_check(self):
        # 7/30/2024 migrated to PlexAutomate class
        super()._chrome_check()


    def csv_to_json(self, csv_file):
        # 7/30/2024 migrated to PlexAutomate class
        super()._csv_to_json(csv_file)


    def config(self):
        '''
        Creates the config file which can be used to change any login
        details after it is created.
        '''
        if self.use_config:
    # Create the config file if it doesn't exist
            config_path = Path('config.ini')
            config = configparser.ConfigParser()
            if not config_path.is_file():
                config['Plex'] = {}
                config['Plex']['User'] = self.user_id
                config['Plex']['Pass'] = self.password
                config['Plex']['Company_Code'] = self.company_code
                config['Plex']['Database'] = self.db
                config['Plex']['PCN'] = self.pcn
                with open('config.ini', 'w+') as configfile:
                    config.write(configfile)
                config.read('config.ini')
                self.plex_db = config['Plex']['Database']
                self.plex_user = config['Plex']['User']
                self.plex_pass = config['Plex']['Pass']
                self.plex_company = config['Plex']['Company_Code']
                self.plex_pcn = config['Plex']['PCN']
            else:
                config.read('config.ini')
                self.plex_db = config['Plex']['Database']
                self.plex_user = config['Plex']['User']
                self.plex_pass = config['Plex']['Pass']
                self.plex_company = config['Plex']['Company_Code']
                self.plex_pcn = config['Plex']['PCN']
        else:
            self.plex_db = self.db
            self.plex_user = self.user_id
            self.plex_pass = self.password
            self.plex_company = self.company_code
            self.plex_pcn = self.pcn


    def login(self, headless=False):
        '''
        Main login function.
        This uses the config file for the variables.
        If the config file is not present,
            it will get created with the data first used in the class call.
        Logs into Plex test/prod depending on the config
        Also will select the PCN if that is configured
        ''' 
        # Using Chrome to access web
        extension_path = os.path.join(self.bundle_dir, 'resources',
                                      'cumulus_plugin.crx')
        # print('Extension path:', extension_path)
        # update for chrome version 115 and newer
        executable_path = os.path.join(self.bundle_dir, 'resources', 'chromedriver-win64',
                                       'chromedriver.exe')
        os.environ['webdriver.chrome.driver'] = executable_path
        # print(executable_path)
        chrome_options = Options()
        #chrome_options.add_argument("--log-level=off")
        # chrome_options.add_argument("--window-position=10, 10")
        # chrome_options.add_argument("--window-size=600, 800")
        chrome_options.add_argument("--log-level=3")
        if headless:
            chrome_options.add_argument("--headless")
        elif self.cumulus:
            chrome_options.add_extension(extension_path)
        chrome_options.add_experimental_option("prefs", {
        "download.default_directory": f"{self.bundle_dir}\Downloads",
        "download.prompt_for_download": False,
        })
        # print("before opening webdriver.")
        # self.driver = webdriver.Chrome(executable_path=executable_path,
        #                           options=chrome_options)
        service = Service(executable_path=executable_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        # print("after opening webdriver.")
    # Open the website
    # Test vs production can be configured in config file
    # Default is test
        if self.plex_db == 'PROD':
            self.plex_db = self.plex_prod
        else:
            self.plex_db = self.plex_test
        if self.legacy_login:
            self.sso = ''
        self.driver.get(f'https://{self.plex_db}{self.plex_main}{self.sso}')

    # Locate id and password fields
        id_box = self.driver.find_element(By.NAME, self.plex_log_id)
        pass_box = self.driver.find_element(By.NAME, self.plex_log_pass)
        company_code = self.driver.find_element(By.NAME, self.plex_log_comp)

    # Send login information
    # This can be configured in the config file
        company_code.send_keys(self.plex_company)
        company_code.send_keys(Keys.TAB)
        id_box.send_keys(self.plex_user)
        id_box.send_keys(Keys.TAB)
        pass_box.send_keys(self.plex_pass)
        
        if (headless or not self.legacy_login) and self.environment == 'CLASSIC':
            # print('headless login for classic')
            main_window_handle = None
            while not main_window_handle:
                # print('looking for main window')
                main_window_handle = self.driver.current_window_handle
            login_button = self.driver.find_element(By.ID, self.plex_login)
            login_button.click()
            # print('clicked login button')
            signin_window_handle = None
            timeout_signin = 30
            timeout_start = time.time()
            login_attempt = 0
            while not signin_window_handle and time.time() < timeout_start + timeout_signin:
                # print('searching for signin window')
                for handle in self.driver.window_handles:
                    if handle != main_window_handle:
                        # print('found login window')
                        signin_window_handle = handle
                        break
                    else:
                        timeout_signin -= 1
                        login_attempt += 1
                        time.sleep(1)
                        # print(timeout_signin)
                        print(f'Login attempt: {login_attempt}')
            if not signin_window_handle:
                raise LoginError(self.environment, self.db, self.pcn, 'Failed to find Plex signon window. Please validate login credentials and try again.')
            self.driver.switch_to.window(signin_window_handle)

    # Click login
        if not headless and (self.legacy_login or (not self.legacy_login and self.environment == 'UX')):
            login_button = self.driver.find_element(By.ID, self.plex_login)
            login_button.click()
            print("clicked login")

    # Get URL token and store it to be used for navigation later
        url = self.driver.current_url
        if not any(url_part in url.upper() for url_part in SIGNON_URL_PARTS):
            raise LoginError(self.environment, self.db, self.pcn, 'Login page not detected. Please validate login credentials and try again.')
        url_split = url.split('/')
        url_proto = url_split[0]
        url_domain = url_split[2]
        if self.environment == 'UX':
            self.url_token = url.split('?')[1]
            self.url_comb = f'{url_proto}//{url_domain}'
        else:
            self.url_token = url_split[3]
            self.url_comb = f'{url_proto}//{url_domain}/{self.url_token}'

    # Click PCN
    # Default PCN can be set in the config file
    # By default this is configured to not be used
        if self.pcn != '':
            if self.environment == 'UX':
                self.url_token = self.token_get()
                self.driver.get(f'{self.url_comb}/SignOn/Customer/{self.pcn}?{self.url_token}')
                if UX_INVALID_PCN_MESSAGE in self.driver.current_url.upper():
                    raise LoginError(self.environment, self.db, self.pcn, f'Unable to login to PCN. Verify you have access.')
                return (self.driver, self.url_comb, self.url_token)
            else:
                # Classic login with single PCN will not show PCN selector, this should handle those cases.
                if not 'MENUCUSTOMER.ASPX' in self.driver.current_url.upper():
                    return (self.driver, self.url_comb, "None")
                try:
                    self.pcn = self.pcn_dict[self.plex_pcn]
                    try:
                        self.driver.find_element(By.XPATH, f'//img[@alt="{self.pcn}"]').click()
                    except NoSuchElementException:
                        try:
                            self.driver.find_element(By.XPATH, f'//*[contains(text(), "{self.pcn}")]')[0].click()
                        except NoSuchElementException:
                            raise LoginError(self.environment, self.db, self.pcn, f'Unable to locate PCN. Verify you have access.')
                except (IndexError, KeyError):
                    raise LoginError(self.environment, self.db, self.plex_pcn, 'PCN is not present in reference file. Verify pcn.json data.')
                return (self.driver, self.url_comb, "None")


    def download_chrome_driver(self, version=None):
        super()._download_chrome_driver(version)
        resource_path = os.path.join(self.bundle_dir, 'resources')
        extension_path = os.path.join(resource_path, 'cumulus_plugin.crx')
    # Download the Cumulus plugin
        if self.cumulus:
            extension_id = 'ohndojpkopphmijlemjgnpbbpefpaang'
            url = 'https://clients2.google.com/service/update2/crx?response=redirect&os=win&arch=x86-64&os_arch=x86-64&nacl_arch=x86-64&prod=chromecrx&prodchannel=unknown&prodversion=' + self.full_chrome_browser_version + '&acceptformat=crx2, crx3&x=id%3D' + extension_id + '%26uc'
            urllib.request.urlretrieve(url, extension_path)


    def frozen_check(self):
        # 7/30/2024 migrated to PlexAutomate class
        return super()._frozen_check()


    def ux_click_button(self, name, search=0):
        """
        Takes the text from a UX button and searches for it.
        When found, triggers the mousedown function.
        """
        if self.environment == "CLASSIC":
            print("This only works in UX.")
            return
        self.name = name
        self.search = search
        self.script = """
        var buttons = document.getElementsByTagName('button')
        var searchText = "{name}"
        var found

        for (var i =0;i<buttons.length;i++){{
        if(buttons[i].textContent == searchText){{
            found = buttons[i]
            if ({search}==1){{
            $(found).trigger("mousedown")}}
            else {{
                found.click()
            }}
        break}}}}
        """.format(name=self.name, search=self.search)
        self.driver.execute_script(self.script)


    def ux_click_action_bar_item(self, item, sub_item=None, more=False):
        """
        Takes the text from a UX button and searches for it.
        When found, triggers the mousedown function.

        Parameters:
            item: Display text of the action bar item to click.
            sub_item: Display text of the sub item in cases where the item is a drop-down.
            more: If the button is under the "more actions" drop down.
            TODO - add support for this possibility
        Returns:
            If no item was detected, raise exception.
        """
        if self.environment == "CLASSIC":
            print("This only works in UX.")
            return
        self.item = item
        self.sub_item = sub_item
        self.more = more
        self.script = """
        var actionItems = document.querySelector('.plex-actions').children
        var searchText = "{item}"
        var found
        for (var i =0;i<actionItems.length;i++){{
            if(actionItems[i].firstElementChild.textContent.includes(searchText)){{
                found = actionItems[i].firstElementChild
                found.click()
                return found
            }}
        }}
        """.format(item=self.item)
        self.action_element = self.driver.execute_script(self.script)
        if not self.action_element:
            raise ActionError('Action bar item not found.', expression=item, message='Action bar item not found.')
        if self.sub_item and self.action_element:
            self.script = """
            var subItem = '{sub_item}'
            var found = arguments[0]
            subList = found.nextElementSibling.children
                for (var j = 0;j<subList.length;j++){{
                    if (subList[j].textContent.includes(subItem)){{
                        found = subList[j]
                        found.click()
                        break
                    }}
                }}
            """.format(item=self.item, sub_item=self.sub_item)
            self.driver.execute_script(self.script, self.action_element)


    def edi_upload(self, file_list):
        super().edi_upload(file_list)


    def switch_pcn(self, pcn):
        """
        Switches pcns when provided a PCN number.
        """
        self.pcn = str(pcn)
        if self.environment == 'UX':
            self.url_token = self.token_get()
            self.driver.get(f'{self.url_comb}/SignOn/Customer/{self.pcn}?{self.url_token}')
        else:
            self.url_token = self.token_get()
            self.driver.get(f'{self.url_comb}/Modules/SystemAdministration'
                                   f'/MenuSystem/MenuCustomer.aspx')
            # Click on the PCN link
            pcn = self.pcn_dict[self.pcn]
            try:
                self.driver.find_element(By.XPATH, f'//img[@alt="{pcn}"]').click()
            except NoSuchElementException:
                self.driver.find_elements(By.XPATH, f'//*[contains(text(), "{pcn}")]')[0].click()


    def make_csv_dict(self, row):
        """
        I find this is a very useful way to get csv column header references
        Using the names of the columns works even when the position of them
            changes.
        This is not fully neccessary due to the existence of csv.DictReader 
            doing mostly the same thing.
        This function supports edge cases for files with duplicate column names
            without unexpectedly sending the wrong row data.
        """
        self.row = row
        cd = {}
        for x, i in enumerate(row):
            if i in cd.keys():
                i = i+'_'+str(x)
            cd[i] = x
        return cd


    def create_results_file(self, *args):
        self.results_file = Path(os.path.join(self.bundle_dir, self.db, self.batch_code, f'{self.batch_time}_results.csv'))
        headers = ', '.join([h for h in args])
        if not os.path.isfile(self.results_file):
            with open(self.results_file, 'w+', encoding='utf-8') as outfile:
                outfile.write(headers)
        return self.results_file

if __name__ == '__main__':
    None
