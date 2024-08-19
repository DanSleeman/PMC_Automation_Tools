import urllib
import zipfile
import winreg
import re
from warnings import warn

from common.get_file_properties import getFileProperties
import os
import csv
import sys
import time
import json
from abc import ABC, abstractmethod
from typing import Literal, Self
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    NoSuchElementException
    )
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webelement import WebElement
from common.exceptions import (
    UpdateError,
    NoRecordError,
    LoginError,
    PlexAutomateError
)
from common.utils import (
    debug_logger,
    # debug_dump_variables,
    frozen_check,
    create_batch_folder,
    # setup_logger
    )
VALID_ENVIRONMENTS = {'ux', 'classic'}


BANNER_SUCCESS = 1
BANNER_WARNING = 2
BANNER_ERROR = 3
BANNER_CLASSES = {
    'plex-banner-success': BANNER_SUCCESS,
    'plex-banner-error': BANNER_WARNING,
    'plex-banner-warning': BANNER_ERROR
}
BANNER_SELECTOR = (By.CLASS_NAME, 'plex-banner')

SIGNON_URL_PARTS = {'/LAUNCHPAGE', '/MENUCUSTOMER.ASPX', '/MENU.ASPX'}

VISIBLE = 10
INVISIBLE = 20
CLICKABLE = 30
EXISTS = 0
_wait_until = {
    VISIBLE : EC.presence_of_element_located,
    INVISIBLE : EC.invisibility_of_element_located,
    CLICKABLE : EC.element_to_be_clickable,
    EXISTS : None
}


class PlexDriver(ABC):
    """
    Needs login details
    chrome driver download
    TODO - split functionality between classic and ux drivers with shared functionality
    """
    def __init__(self, environment: Literal['ux', 'classic'], *args, driver_type: Literal['edge', 'chrome']='edge', **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.driver_type = driver_type
        self.pcn_file_path = kwargs.get('pcn_file_path', Path('resources/pcn.json'))
        self.debug = kwargs.get('debug', False)
        self.debug_level = kwargs.get('debug_level', 0)
        self.debug_logger = debug_logger(self.debug_level)
        self.environment = environment.lower()
        self.driver_override = kwargs.get('driver_override')
        self.single_pcn = False
        
        self._set_login_vars()
        self._path_init()
        self._read_driver_version()
        self.debug_logger.debug('finished initializing.')


    def _set_login_vars(self):
        self.plex_log_id = 'username'
        self.plex_log_pass = 'password'
        self.plex_log_comp = 'companyCode'
        self.plex_login = 'loginButton'


    def _path_init(self):
        self.resource_path = 'resources'
        if not os.path.exists(self.resource_path):
            os.mkdir(self.resource_path)
        self.download_dir = 'downloads'
        if not os.path.exists(self.download_dir):
            os.mkdir(self.download_dir)
        self.latest_driver_version_file = os.path.join(self.resource_path, 'driver_version.txt')


    def wait_for_element(self, selector, driver=None, timeout=15, type=VISIBLE, ignore_exception: bool=False, element_class=None) -> 'PlexElement':
        """
        Wait until an element meets specified criteria.

        Wrapper for Selenium WebDriverWait function for common Plex usage.

        Parameters

            - selector: Element selector to wait for
            - driver: root WebDriver to use for locating the element
            - timeout: How long to wait until raising an exception
            - type: Type of wait to be used
                - VISIBLE
                - INVISIBLE
                - CLICKABLE
                - EXISTS: Just return the element with no waiting.
            - ignore_exception: Do not raise exception if element isn't located.

        Returns

            - PlexElement object
        """
        try:
            driver = driver or self.driver
            element_condition = _wait_until.get(type)
            if element_condition:
                WebDriverWait(driver, timeout).until(element_condition(selector))
            element_class = element_class or PlexElement
            return element_class(driver.find_element(*selector), self)

        except (TimeoutException, StaleElementReferenceException, NoSuchElementException):
            if ignore_exception:
                return None
            raise
    
    def search_for_element(self, selector, match_value, driver=None, ignore_exception=False):
        try:
            driver = driver or self.driver
            _el = driver.find_elements(*selector)
            for e in _el:
                val = e.get_attribute('value')
                tex = e.get_attribute('textContent')
                if match_value == val or match_value == tex:
                    return e
            raise NoSuchElementException('No element could be found with the provided selector and match value.')
        except (TimeoutException, StaleElementReferenceException, NoSuchElementException):
            if ignore_exception:
                return None
            raise

    def wait_for_banner(self) -> None:
        try:
            loop = 0
            while loop <= 10:
                banner = self.wait_for_element(BANNER_SELECTOR)
                banner_class = banner.get_attribute('class')
                banner_type = next((BANNER_CLASSES[c] for c in BANNER_CLASSES if c in banner_class), None)
                if banner_type:
                    self._banner_handler(banner_type, banner)
                    break
                time.sleep(1)
                loop += 1
            else:
                raise UpdateError(f'Unexpected banner type detected. Found {banner_class}. Expected one of {list(BANNER_CLASSES.keys())}')
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
            raise UpdateError('No banner detected.')


    def _banner_handler(self, banner_type, banner):
        if banner_type == BANNER_SUCCESS:
            return
        else:
            banner_text = banner.get_property('textContent')
            raise UpdateError(banner_text)

    def wait_for_gears(self, selector, loading_timeout=10):
        """
        Wait for the spinning gears image to appear and wait for it to dissappear.

        This should be called after searching or updating a screen.
        
        Essentially any time you are clicking a button which would cause the page to load.

        The gears sometimes dissappear quicker than can be detected. 
            If the gears are not detected at the begining, the end timeout is shorter.

        Parameters

            - loading_timeout: how long to wait until the gears disappear once visible.
                Use this if the screen usually takes a long time to load/search.
        """
        gears_visible = False
        gears_visible = self.wait_for_element(selector, type=VISIBLE, timeout=1, ignore_exception=True)
        timeout = loading_timeout if gears_visible else 1
        self.debug_logger.debug(f'Timeout for invisible is {timeout}.')
        self.wait_for_element(selector, type=INVISIBLE, timeout=timeout, ignore_exception=True)

    def login(self, username, password, company_code, pcn, test_db=True, headless=False):
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
        # self._chrome_check()
        self.test_db = test_db
        self.batch_folder = create_batch_folder(test=self.test_db)
        self.pcn = pcn
        self.headless = headless
        if hasattr(self, 'pcn_dict'):
            self.pcn_name = self.pcn_dict[self.pcn]
        else:
            self.pcn_name = self.pcn
        self.driver = self._driver_setup(self.driver_type)

        db = self.plex_test if self.test_db else self.plex_prod
        self.driver.get(f'https://{db}{self.plex_main}{self.sso}')
        # Test for new login screen
        try:
            self.wait_for_element((By.XPATH, '//img[@alt="Rockwell Automation"]'), timeout=4)
            self.debug_logger.debug(f'New Rockwell IAM login screen detected.')
            rockwell = True
        except (NoSuchElementException, TimeoutException):
            self.wait_for_element((By.XPATH, '//img[@alt="Plex"]'))
            rockwell = False
        if rockwell:
            id_box = self.wait_for_element((By.NAME, self.plex_log_id), type=CLICKABLE)
            id_box.send_keys(username)
            id_box.send_keys(Keys.TAB)
            company_box = self.wait_for_element((By.NAME, self.plex_log_comp), type=CLICKABLE)
            company_text = company_box.get_attribute('value')
            if company_text != company_code:
                self.debug_logger.info(f'Auto-populated company code: {company_text} does not match provided login credentials: {company_code}.')
                company_box.click()
                company_box.clear()
                company_box.send_keys(company_code)
                company_box.send_keys(Keys.TAB)
            pass_box = self.wait_for_element((By.NAME, self.plex_log_pass), type=CLICKABLE)
            pass_box.send_keys(password)
        else:
            self.debug_logger.debug(f'Plex IAM login screen detected.')
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

    def _driver_setup(self, type):
        if type == 'edge':
            self._edge_check()
            self._download_edge_driver(self.full_browser_version)  # Adjust this to download the correct Edge driver
            return self._edge_setup()
        if type == 'chrome':
            self._chrome_check()
            self._download_chrome_driver(self.driver_override)
            return self._chrome_setup()


    def _read_driver_version(self):
        if os.path.exists(self.latest_driver_version_file):
            with open(self.latest_driver_version_file, 'r') as f:
                self.latest_downloaded_driver_version = f.read()
                self.debug_logger.debug(f'Latest downloaded chromedriver version: {self.latest_downloaded_driver_version}')
        else:
            self.debug_logger.debug(f'Latest downloaded chromedriver file not detected. Setting version to None.')
            self.latest_downloaded_driver_version = None


    def _save_driver_version(self, version):
        self.debug_logger.debug(f'Saving latest downloaded driver version: {version}')
        with open(self.latest_driver_version_file, 'w+') as f:
            f.write(version)




    def _download_edge_driver(self, version=None):
        '''
        Downloads the EdgeDriver that will allow Selenium to function.
        '''
        text_path = os.path.join(self.resource_path, 'edgedriver.txt')
        zip_path = os.path.join(self.resource_path, 'edgedriver.zip')
        edgedriver_url = None
        if version:
            self.full_browser_version = version
        else:
            url = 'https://msedgedriver.azureedge.net/LATEST_STABLE'

            urllib.request.urlretrieve(url, text_path)
            with open(text_path, 'r', encoding='utf-16') as f:
                latest_edgedriver_version = f.read().strip()
            self.full_browser_version = latest_edgedriver_version
        edgedriver_url = f'https://msedgedriver.azureedge.net/{self.full_browser_version}/edgedriver_win64.zip'
        
        if self.latest_downloaded_driver_version == edgedriver_url:
            self.debug_logger.debug(f'Latest downloaded EdgeDriver version matches the latest online. Skipping download.')
            return
        else:
            self._save_driver_version(edgedriver_url)

        self.debug_logger.debug(f'Downloading EdgeDriver version from: {edgedriver_url}')
        urllib.request.urlretrieve(edgedriver_url, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            self.debug_logger.debug(f'Extracting EdgeDriver to: {self.resource_path}')
            zip_ref.extractall(self.resource_path)
            
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
        latest_chromedriver_version = chrome_releases['milestones'][self.browser_version]['downloads']['chromedriver']#['platform']
        
        for x in latest_chromedriver_version:
            if x['platform'] == 'win64':
                chromedriver_url = x['url']
        if chromedriver_url:
            url = chromedriver_url
            if self.latest_downloaded_chromedriver_version == url:
                self.debug_logger.debug(f'Latest downloaded chromedriver version matches with lasted on web. Skipping download.')
                return
            else:
                self._save_driver_version(url)
        else:
            if version:
                self.full_browser_version = version
            url = f'https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/{self.full_browser_version}/win64/chromedriver-win64.zip'
        self.debug_logger.debug(f'Downloading chromedriver version at: {url}')
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            self.debug_logger.debug(f'Exctracting chromedriver to: {self.resource_path}')
            zip_ref.extractall(self.resource_path)

    def _chrome_check(self):
        chrome_key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "ChromeHTML\\shell\\open\\command", 0, winreg.KEY_READ)
        command = winreg.QueryValueEx(chrome_key, "")[0]
        winreg.CloseKey(chrome_key)
        chrome_browser = re.search("\"(.*?)\"", command)
        if chrome_browser:
            chrome_browser = chrome_browser.group(1)
            print(f'Chrome browser install location: {chrome_browser}')
        cb_dictionary = getFileProperties(chrome_browser) # returns whole string of version (ie. 76.0.111)
        self.browser_version = cb_dictionary['FileVersion'].split('.')[0] # substring version to capabable version (ie. 77 / 76)
        self.full_browser_version = cb_dictionary['FileVersion']
        print(f'Chrome base version: {self.browser_version} | Full Chrome version: {self.full_browser_version}')
    
    def _edge_check(self):
        edge_key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "MSEdgeHTM\\shell\\open\\command", 0, winreg.KEY_READ)
        command = winreg.QueryValueEx(edge_key, "")[0]
        winreg.CloseKey(edge_key)
        edge_browser = re.search("\"(.*?)\"", command)
        if edge_browser:
            edge_browser = edge_browser.group(1)
            print(f'Edge browser install location: {edge_browser}')
        edge_dictionary = getFileProperties(edge_browser)  # returns the full version string (e.g., 91.0.864.67)
        self.browser_version = edge_dictionary['FileVersion'].split('.')[0]  # Extract the major version (e.g., 91)
        self.full_browser_version = edge_dictionary['FileVersion']  # Full version (e.g., 91.0.864.67)

        print(f'Edge base version: {self.browser_version} | Full Edge version: {self.full_browser_version}')

    def _edge_setup(self):
        executable_path = os.path.join(self.resource_path, 'msedgedriver.exe')
        edge_options = EdgeOptions()
        edge_options.use_chromium = True
        edge_options.add_argument("--log-level=3")
        if self.headless:
            self.debug_logger.debug(f'Running Edge in headless mode.')
            edge_options.add_argument("--headless")
        edge_options.add_experimental_option("prefs", {
            "download.default_directory": f"{self.download_dir}",
            "download.prompt_for_download": False,
        })

        service = Service(executable_path=executable_path)
        return webdriver.Edge(service=service, options=edge_options)
    

    def _chrome_setup(self):
        executable_path = os.path.join(self.resource_path, 'chromedriver-win64', 'chromedriver.exe')
        os.environ['webdriver.chrome.driver'] = executable_path
        chrome_options = Options()
        chrome_options.add_argument("--log-level=3")
        if self.headless:
            self.debug_logger.debug(f'Running chrome in headless mode.')
            chrome_options.add_argument("--headless")
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": f"{self.download_dir}",
            "download.prompt_for_download": False,
            })
        service = Service(executable_path=executable_path)
        return webdriver.Chrome(service=service, options=chrome_options)

    def _classic_popup_handle(self):
        main_window_handle = None
        while not main_window_handle:
            self.debug_logger.debug('looking for main window')
            main_window_handle = self.driver.current_window_handle
        signin_window_handle = None
        timeout_signin = 30
        timeout_start = time.time()
        login_attempt = 0
        while not signin_window_handle and time.time() < timeout_start + timeout_signin:
            self.debug_logger.debug(f'Searching for classic signin window')
            for handle in self.driver.window_handles:
                if handle != main_window_handle:
                    self.debug_logger.debug(f'Found classic login window')
                    signin_window_handle = handle
                    break
                else:
                    timeout_signin -= 1
                    login_attempt += 1
                    time.sleep(1)
                    self.debug_logger.debug(f'Login attempt: {login_attempt}')
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
            self.debug_logger.debug(f'Single PCN account detected.')
            self.single_pcn = True
            self.first_login = False
            return (self.driver, self.url_comb, "None")
        if not self.single_pcn and not self.first_login:
            self.driver.get(f'{self.url_comb}/Modules/SystemAdministration/MenuSystem/MenuCustomer.aspx')
        try:
            try:
                self.driver.find_element(By.XPATH, f'//img[@alt="{_pcn_name}"]').click()
                self.debug_logger.debug(f'PCN found by logo text: {_pcn_name}.')
            except NoSuchElementException: # PCN does not have a logo, find the URL link instead.
                try:
                    self.driver.find_element(By.XPATH, f'//*[contains(text(), "{_pcn_name}")]').click()
                    self.debug_logger.debug(f'PCN found by link text: {_pcn_name}.')
                except NoSuchElementException:
                    raise LoginError(self.environment, self.db, _pcn_name, f'Unable to locate PCN. Verify you have access.')
            finally:
                self.first_login = False
        except (IndexError, KeyError):
            raise LoginError(self.environment, self.db, _pcn_name, 'PCN is not present in reference file. Verify pcn.json data.')



    @abstractmethod
    def token_get(self):...

    @abstractmethod
    def _pcn_switch(self):...

    
    def pcn_switch(self, pcn):
        pcn = str(pcn)
        self.debug_logger.debug(f'Switching to PCN: {pcn}.')
        self._pcn_switch(pcn)
        return self.token_get()    
    switch_pcn = pcn_switch

    @abstractmethod
    def click_button(self):...
    
class PlexElement(WebElement):
    """
    Subclass of Selenium WebElement with specialized functions for Plex elements.
    """
    def __init__(self, webelement, parent):
        """
        Debug level from parent
        Debug flag from parent ?
        Driver from webelement
        batch_folder from parent
        screenshot_folder from parent

        methods

            wait for element
            wait for gears
            search for element
            screenshot
            sync checkbox
            sync textbox

        abstract methods
            sync picker

        """
        super().__init__(webelement._parent, webelement._id)
        self.debug = parent.debug
        self.debug_level = parent.debug_level
        self.debug_logger = debug_logger(self.debug_level)
        self.batch_folder = parent.batch_folder
        self.test_db = parent.test_db
        self.driver = webelement._parent
        self.wait_for_element = parent.wait_for_element
        self.click_button = parent.click_button
        self.wait_for_gears = parent.wait_for_gears
        self.search_for_element = parent.search_for_element


    def screenshot(self):
        """
        Save a screenshot of the element. Useful to debug if there are any issues locating the element properly.
        """
        element_id = self.id[-8:]
        session = self.parent.session_id[-5:]
        name = self.accessible_name or 'No_Name'
        if not hasattr(self, 'batch_folder'):
            self.batch_folder = create_batch_folder(test=self.test_db)
        if not hasattr(self, 'screenshot_folder'):
            self.screenshot_folder = os.path.join(self.batch_folder, 'screenshots')
            os.makedirs(self.screenshot_folder, exist_ok=True)
        filename = os.path.join(self.screenshot_folder, f"{session}_{element_id}_{name}_screenshot.png")
        super().screenshot(filename)

    
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
            self.debug_logger.info(f'{self.get_property("name")} - Checkbox state: {check_state}. Clicking to make it {bool_state}.')
            self.click()
        else:
            self.debug_logger.debug(f'{self.get_property("name")} - Checkbox state: {check_state} matches provided state: {bool_state}.')


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
            self.debug_logger.info(f'{self.get_property("name")} - Current text: {text}. Replacing with provided text: {text_content}')
            self.clear()
            self.send_keys(text_content)
            self.send_keys(Keys.TAB)
        else:
            self.debug_logger.debug(f'{self.get_property("name")} - Current text: {text}. Matches provided text: {text_content}')

    @abstractmethod
    def sync_picker(self):...