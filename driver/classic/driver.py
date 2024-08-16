import os
from warnings import warn
import sys
from typing import Literal, Self
from driver.common import (
    PlexDriver,
    PlexElement,
    VISIBLE,
    INVISIBLE,
    CLICKABLE,
    EXISTS,
    SIGNON_URL_PARTS
    )
from selenium.common.exceptions import TimeoutException,StaleElementReferenceException,NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from common.exceptions import (
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
from common.utils import (
    get_case_insensitive_key_value
)
# TODO - figure out classic gears locator
PLEX_GEARS_SELECTOR = (By.ID,'__WAITMESSAGE_CONTAINER')
PCN_SQL = '''Please create the pcn.json file by running the following SQL report in Plex and save it as a csv file.

SELECT
 P.Plexus_Customer_No
,P.Plexus_Customer_Name
FROM Plexus_Control_v_Customer_Group_Member P

Press OK to select the csv file.'''
class ClassicDriver(PlexDriver):
    """
    Classic Unique requirements
    pcn_file required
    url parts different
    need csv_to_json function

    login uniqueness

    """
    def __init__(self, *args, **kwargs):
        super().__init__(environment='classic', *args, **kwargs)
        for k,v in kwargs.items():
            setattr(self,k,v)
        self.pcn_file_path = kwargs.get('pcn_file_path',os.path.join('resources','pcn.json'))
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
            '''
            Function to take a csv file from Plex and create a
            
            PCN JSON file that can be used to log into specific PCNs
                if the user has multiple PCN access.
            
            This should only be called on initialization if
                the pcn.json file does not exist yet.
            
            Only required for classic logins.
            '''
            _pcn_dict = {}
            with open(csv_file,'r',encoding='utf-8-sig') as c:
                r = csv.DictReader(c)
                for row in r:
                    if not row:
                        continue
                    _pcn_dict[get_case_insensitive_key_value(row,'plexus_customer_no')] = get_case_insensitive_key_value(row,'plexus_customer_name')
            if not os.path.exists('resources'):
                os.mkdir('resources')
            with open(os.path.join('resources','pcn.json'),'w+',encoding='utf-8') as j:
                j.write(json.dumps(_pcn_dict, indent=4, ensure_ascii=False))

    def wait_for_element(self,selector, driver=None, timeout=15,type=VISIBLE,ignore_exception=False):
        return super().wait_for_element(selector, driver=driver, timeout=timeout,type=type,ignore_exception=ignore_exception,element_class=ClassicPlexElement)

    def wait_for_gears(self,loading_timeout=10):
        super().wait_for_gears(PLEX_GEARS_SELECTOR, loading_timeout)

    def click_button(self, button_text, driver=None):
        """
        Classic buttons have two different types of buttons.
        1. buttons using a/span tags
        2. buttons made of ul/li tags

        Parameters:

        - name: Text of the button to click
        - driver: webdriver root to use if different than default

        """
        driver = driver or self.driver
        # Elements with button type. <a><span> structure 
        a_buttons = driver.find_elements(By.CLASS_NAME,'Button')
        # Elements with button type. <ul><li> structure
        ul_buttons = driver.find_elements(By.CLASS_NAME,'button')
        buttons = a_buttons + ul_buttons
        for b in buttons:
            if b.get_property('textContent') == button_text:
                self.debug_logger.debug(f'Button found with matching text: {button_text}')
                b.click()
                return
            

    def login(self, username, password, company_code, pcn, test_db=True, headless=False):
        """
        set variables for url
        initialize parent class function
            chrome check
            download chromedriver
        classic popup handle
        pcn select
        token set
        pcn switch (first login)
        return
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
            raise LoginError('Failed to find Plex signon window. Please validate login credentials and try again.')
        self.driver.switch_to.window(signin_window_handle)


    def _login_validate(self):
        url = self.driver.current_url
        if not any(url_part in url.upper() for url_part in SIGNON_URL_PARTS):
            raise LoginError('Login page not detected. Please validate login credentials and try again.')


    def _pcn_switch(self,pcn):
        _pcn_name = self.pcn_dict.get(pcn,None)
        if not _pcn_name:
            raise LoginError(f'PCN: {pcn} is not present in reference file. Verify pcn.json data.')
        _url = self.driver.current_url
        if self.single_pcn:
            warn(f'This account only has access to one PCN.',loglevel=2)
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
        raise LoginError(self.environment, self.db, _pcn_name, f'Unable to locate PCN. Verify you have access.')


    def _pcn_link_locate(self, xpath):
        try:
            self.driver.find_element(By.XPATH, xpath).click()
            return True
        except NoSuchElementException:
            return False


    def token_get(self):
        url = self.driver.current_url
        url_split = url.split('/')
        url_proto = url_split[0]
        url_domain = url_split[2]
        self.url_token = url_split[3]
        self.url_comb = f'{url_proto}//{url_domain}/{self.url_token}'

class ClassicPlexElement(PlexElement):
    def __init__(self, webelement, parent):
        super().__init__(webelement, parent)

    def sync_picker(self, text_content, clear=False,date=False):
        """"""