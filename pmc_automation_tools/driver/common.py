import urllib
import zipfile
import winreg
import re
from warnings import warn

from pmc_automation_tools.common.get_file_properties import getFileProperties
import os
import time
import json
from abc import ABC, abstractmethod
from typing import Literal
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    NoSuchElementException
    )
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webelement import WebElement
from pmc_automation_tools.common.exceptions import (
    UpdateError,
    LoginError,
)
from pmc_automation_tools.common.utils import (
    debug_logger,
    create_batch_folder,
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


    def wait_for_element(self, selector:tuple[str, str], driver=None, timeout:int=15, type=VISIBLE, ignore_exception: bool=False, element_class:object=None) -> 'PlexElement':
        """Wait until an element meets specified criteria.

        Wrapper for Selenium WebDriverWait function for common Plex usage.

        Args:
            selector (tuple[str, str]): Selenium style element selector e.g. (By.NAME, 'ElementName')
            driver (WebDriver|PlexElement, optional): root WebDriver to use for locating the element. Defaults to None.
            timeout (int, optional): Time to wait until timeout is triggered. Defaults to 15.
            type (str, optional): Type of wait to be performed. Defaults to VISIBLE.
            ignore_exception (bool, optional): Don't raise an exception if the timeout is reached. Defaults to False.
            element_class (object, optional): class of the WebElement to return. Defaults to None.

        Raises:
            exception: re-raises exception from failing to meet the expected condition

        Returns:
            PlexElement: PlexElement based on search criteria
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
        """Wait for the spinning gears image to appear and disappear

        This should be called after searching or updating a screen.

        Essentially any time you are clicking a button which would cause the page to load.

        The gears sometimes dissappear quicker than can be detected. 
            If the gears are not detected at the begining, the end timeout is shorter.

        Arg:
            selector (tuple[str, str]): Selenium style element selector e.g. (By.NAME, 'ElementName')
            loading_timeout (int, optional): Time to wait until the gears disappear after being detected. Defaults to 10.
        """
        gears_visible = False
        gears_visible = self.wait_for_element(selector, type=VISIBLE, timeout=1, ignore_exception=True)
        timeout = loading_timeout if gears_visible else 1
        self.debug_logger.debug(f'Timeout for invisible is {timeout}.')
        self.wait_for_element(selector, type=INVISIBLE, timeout=timeout, ignore_exception=True)

    def login(self, username, password, company_code, pcn, test_db=True, headless=False):
        """Log in to Plex

        Args:
            username (str): Plex username
            password (str): Plex password
            company_code (str): Plex company code
            pcn (str): PCN number
            test_db (bool, optional): Log in to the test database. Defaults to True.
            headless (bool, optional): Run in headless mode. Defaults to False.
        """
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
            company_box = self.wait_for_element((By.NAME, self.plex_log_comp), ignore_exception=True, type=CLICKABLE, timeout=5)
            if company_box == self.driver.switch_to.active_element:
                self.debug_logger.debug(f'Company box is active. Filling in with supplied data.')
                company_box.click()
                company_box.clear()
                company_box.send_keys(company_code)
                company_box.send_keys(Keys.TAB)
            pass_box = self.wait_for_element((By.NAME, self.plex_log_pass), type=CLICKABLE)
            if pass_box == self.driver.switch_to.active_element:
                self.debug_logger.debug(f'Filling in password.')
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




    def _download_edge_driver(self, version:str=None):
        """Downloads the EdgeDriver that will allow Selenium to function.

        Args:
            version (str, optional): edgedriver version if different than latest. Defaults to None.
        """
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
            
    def _download_chrome_driver(self, version:str=None):
        """Downloads the ChromeDriver that will allow Selenium to function.

        Args:
            version (str, optional): chromedriver version if different than latest. Defaults to None.
        """
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

    
    def sync_checkbox(self, bool_state:bool|int):
        """Sync a checkbox to the provided checked state

        Args:
            bool_state (bool | int): Checkbox state to make the element.
        """
        if not type(bool_state) == bool:
            bool_state = bool(int(bool_state))
        check_state = self.get_property('checked')
        if not check_state == bool_state:
            self.debug_logger.info(f'{self.get_property("name")} - Checkbox state: {check_state}. Clicking to make it {bool_state}.')
            self.click()
        else:
            self.debug_logger.debug(f'{self.get_property("name")} - Checkbox state: {check_state} matches provided state: {bool_state}.')


    def sync_textbox(self, text_content:str, clear:bool=False):
        """Sync a textbox with the provided value

        Args:
            text_content (str): Desired value for the text box
            clear (bool, optional): Clear out the text box if sending an empty string. Defaults to False.
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