from typing import Literal, Union
import os
from warnings import warn
import sys
from pmc_automation_tools.driver.common import (
    PlexDriver,
    PlexElement,
    VISIBLE,
    INVISIBLE,
    CLICKABLE,
    EXISTS,
    SIGNON_URL_PARTS
    )
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    NoSuchElementException
    )
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from pmc_automation_tools.common.exceptions import (
    UpdateError,
    NoRecordError,
    LoginError,
    PlexAutomateError
)
import time
from tkinter import filedialog
from tkinter import messagebox
import json
import csv
from pmc_automation_tools.common.utils import (
    get_case_insensitive_key_value
)

PLEX_GEARS_SELECTOR = (By.ID, '__WAITMESSAGE_CONTAINER')
PCN_SQL = '''Please create the pcn.json file by running the following SQL report in Plex and save it as a csv file.

SELECT
 P.Plexus_Customer_No
, P.Plexus_Customer_Name
FROM Plexus_Control_v_Customer_Group_Member P

Press OK to select the csv file.'''
class ClassicDriver(PlexDriver):
    def __init__(self, *args, **kwargs):
        super().__init__(environment='classic', *args, **kwargs)
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.pcn_file_path = kwargs.get('pcn_file_path', os.path.join('resources', 'pcn.json'))
        self._pcn_file_check()

    def _pcn_file_check(self):
        while not os.path.exists(self.pcn_file_path):
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

    def _csv_to_json(self, csv_file):
        """Function to take a csv file from Plex and create a
        
        PCN JSON file that can be used to log into specific PCNs
            if the user has multiple PCN access.
        
        This should only be called on initialization if
            the pcn.json file does not exist yet.
        
        Only required for classic logins.

        Args:
            csv_file (str): path to the csv file generated from the SQL development environment.
        """
        _pcn_dict = {}
        with open(csv_file, 'r', encoding='utf-8-sig') as c:
            r = csv.DictReader(c)
            for row in r:
                if not row:
                    continue
                _pcn_dict[get_case_insensitive_key_value(row, 'plexus_customer_no')] = get_case_insensitive_key_value(row, 'plexus_customer_name')
        if not os.path.exists('resources'):
            os.mkdir('resources')
        with open(os.path.join('resources', 'pcn.json'), 'w+', encoding='utf-8') as j:
            j.write(json.dumps(_pcn_dict, indent=4, ensure_ascii=False))


    def wait_for_element(self, selector, *args, driver:Union['ClassicDriver','ClassicPlexElement']=None, timeout=15, type=VISIBLE, ignore_exception=False) -> 'ClassicPlexElement':
        return super().wait_for_element(selector, *args, driver=driver, timeout=timeout, type=type, ignore_exception=ignore_exception, element_class=ClassicPlexElement)


    def wait_for_elements(self, selector, *args, driver:Union['ClassicDriver','ClassicPlexElement']=None, timeout=15, type=VISIBLE, ignore_exception=False) -> 'ClassicPlexElement':
        return super().wait_for_elements(selector, *args, driver=driver, timeout=timeout, type=type, ignore_exception=ignore_exception, element_class=ClassicPlexElement)


    def wait_for_gears(self, loading_timeout=10):
        super().wait_for_gears(PLEX_GEARS_SELECTOR, loading_timeout)


    def click_button(self, button_text:str, driver:'ClassicPlexElement'=None):
        """Click on a button.

        Classic buttons have two different types of buttons.
            - buttons using a/span tags
            - buttons made of ul/li tags

        Args:
            button_text (str): Text matching the button to click
            driver (ClassicPlexElement, optional): The WebDriver to use as a root for searching for the button. Defaults to None.
        """
        driver = driver or self.driver
        # Elements with <a><span> button structure
        a_buttons = driver.find_elements(By.CLASS_NAME, 'Button')
        # Elements with <ul><li> button structure
        ul_buttons = driver.find_elements(By.CLASS_NAME, 'button')
        buttons = a_buttons + ul_buttons
        for b in buttons:
            if b.get_property('textContent') == button_text:
                self.debug_logger.debug(f'Button found with matching text: {button_text}')
                b.click()
                break


    def login(self, username, password, company_code, pcn, test_db=True, headless=False):
        """Log in to Plex

        Args:
            username (str): Plex username
            password (str): Plex password
            company_code (str): Plex company code (No longer relevant)
            pcn (str): PCN number
            test_db (bool, optional): Determines if logging in to the test database. Defaults to True.
            headless (bool, optional): Run in headless mode. Defaults to False.

        Returns:
            tuple: WebDriver and combine url for navigating to other screens.
        """
        self._set_login_vars()
        super().login(username, password, company_code, pcn, test_db, headless)
        self._classic_popup_handle()
        self._login_validate()
        self.pcn_switch(self.pcn)
        self.token_get()
        self.first_login = False
        return (self.driver, self.url_comb)
    

    def _set_login_vars(self):
        self.plex_main = 'plexonline.com'
        self.plex_prod = 'www.'
        self.plex_test = 'test.'
        self.sso = '/signon'
        super()._set_login_vars()

    def _classic_popup_handle(self):
        """Deal with the browser popup that occurs after logging in to Plex classic.

        Raises:
            LoginError: If there is any credential issues, the window will not appear.
        """
        _pcn_name = self.pcn_dict.get(self.pcn, None)
        main_window_handle = self.driver.current_window_handle
        signin_window_handle = None
        timeout_signin = 30
        timeout_start = time.time()
        while time.time() < timeout_start + timeout_signin:
            self.debug_logger.debug(f'Searching for classic signin window')
            window_handles = self.driver.window_handles
            if len(window_handles) > 1:
                for handle in window_handles:
                    if handle != main_window_handle:
                        self.debug_logger.debug(f'Found classic login window')
                        signin_window_handle = handle
                        break
                if signin_window_handle:
                    break
                time.sleep(1)
        if not signin_window_handle:
            raise LoginError(environment=self.environment, db=self.test_db, pcn=_pcn_name, message=f'Failed to find Plex signon window. Please validate login credentials and try again.')
        self.driver.switch_to.window(signin_window_handle)


    def _login_validate(self):
        _pcn_name = self.pcn_dict.get(self.pcn, None)
        url = self.driver.current_url
        if not any(url_part in url.upper() for url_part in SIGNON_URL_PARTS):
            raise LoginError(environment=self.environment, db=self.test_db, pcn=_pcn_name, message=f'Login page not detected. Please validate login credentials and try again.')


    def _pcn_switch(self, pcn):
        _pcn_name = self.pcn_dict.get(pcn, None)
        if not _pcn_name:
            raise LoginError(environment=self.environment, db=self.test_db, pcn=_pcn_name, message=f'PCN: {pcn} is not present in reference file. Verify pcn.json data.')
        _url = self.driver.current_url
        if self.single_pcn:
            warn(f'This account only has access to one PCN.', loglevel=2)
            return
        if not 'MENUCUSTOMER.ASPX' in _url.upper() and self.first_login:
            self.debug_logger.debug(f'Single PCN account detected.')
            self.single_pcn = True
            return
        if not self.single_pcn and not self.first_login:
            self.driver.get(f'{self.url_comb}/Modules/SystemAdministration/MenuSystem/MenuCustomer.aspx')
        if self._pcn_link_locate(f'//img[@alt="{_pcn_name}"]'):
            return
        if self._pcn_link_locate(f'//*[contains(text(), "{_pcn_name}")]'):
            return
        raise LoginError(environment=self.environment, db=self.test_db, pcn=_pcn_name, message=f'Unable to locate PCN. Verify you have access.')


    def _pcn_link_locate(self, xpath):
        try:
            self.driver.find_element(By.XPATH, xpath).click()
            return True
        except NoSuchElementException:
            return False


    def token_get(self) -> str:
        """Sets self.url_comb for current token value.

        Returns:
            str: Plex URL combination containing token.
        """
        url = self.driver.current_url
        url_split = url.split('/')
        url_proto = url_split[0]
        url_domain = url_split[2]
        self.url_token = url_split[3]
        self.url_comb = f'{url_proto}//{url_domain}/{self.url_token}'
        return self.url_comb

class ClassicPlexElement(PlexElement):
    def __init__(self, webelement, parent):
        super().__init__(webelement, parent)

    def sync_picker(self, text_content, clear=False, date=False):
        """TODO - Create this function."""