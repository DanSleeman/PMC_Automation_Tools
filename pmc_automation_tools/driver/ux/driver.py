from typing import Literal, Union
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
from selenium.webdriver.support.ui import Select
from pmc_automation_tools.common.exceptions import (
    UpdateError,
    NoRecordError,
    LoginError
    )
import time
BANNER_SUCCESS = 1
BANNER_WARNING = 2
BANNER_ERROR = 3
BANNER_CLASSES = {
    'plex-banner-success': BANNER_SUCCESS,
    'plex-banner-error': BANNER_WARNING,
    'plex-banner-warning': BANNER_ERROR
}
BANNER_SELECTOR = (By.CLASS_NAME, 'plex-banner')
PLEX_GEARS_SELECTOR = (By.XPATH, '//i[@class="plex-waiting-spinner"]')
UX_INVALID_PCN_MESSAGE = '__MESSAGE=YOU+WERE+REDIRECTED+TO+YOUR+LANDING+COMPANY'


class UXDriver(PlexDriver):
    def __init__(self, driver_type: Literal['edge', 'chrome'], *args, **kwargs):
        super().__init__(environment='ux', *args, driver_type=driver_type, **kwargs)
        for k, v in kwargs.items():
            setattr(self, k, v)


    def wait_for_element(self, selector, *args, driver:Union['UXDriver','UXPlexElement']=None, timeout=15, type=VISIBLE, ignore_exception=False) -> 'UXPlexElement':
        return super().wait_for_element(selector, *args, driver=driver, timeout=timeout, type=type, ignore_exception=ignore_exception, element_class=UXPlexElement)


    def wait_for_elements(self, selector, *args, driver:Union['UXDriver','UXPlexElement']=None, timeout=15, type=VISIBLE, ignore_exception=False) -> 'UXPlexElement':
        return super().wait_for_elements(selector, *args, driver=driver, timeout=timeout, type=type, ignore_exception=ignore_exception, element_class=UXPlexElement)


    def wait_for_banner(self, timeout:int=10, ignore_exception:bool=False) -> None:
        """Wait for the banner to appear and handle success/error/warning messages.

        Args:
            timeout (int, optional): How long to wait for the banner before throwing an exception. Defaults to 10.
            ignore_exception (bool, optional): Don't re-raise an exception if the banner is not found. Defaults to False.

        Raises:
            UpdateError: Unexpected banner type.
            UpdateError: No banner detected at all.
            UpdateError: Any non-success banners raise an error with the banner text.
        """        
        try:
            loop = 0
            while loop <= timeout:
                banner = self.wait_for_element(BANNER_SELECTOR)
                banner_class = banner.get_attribute('class')
                banner_type = next((BANNER_CLASSES[c] for c in BANNER_CLASSES if c in banner_class), None)
                if banner_type:
                    self._banner_handler(banner_type, banner)
                    break
                time.sleep(1)
                loop += 1
            else:
                if ignore_exception:
                    return None
                raise UpdateError(f'Unexpected banner type detected. Found {banner_class}. Expected one of {list(BANNER_CLASSES.keys())}')
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
            if ignore_exception:
                return None
            raise UpdateError('No banner detected.')


    def _banner_handler(self, banner_type, banner):
        if banner_type == BANNER_SUCCESS:
            return 
        else:
            banner_text = banner.get_property('textContent')
            raise UpdateError(banner_text)
    

    def wait_for_gears(self, loading_timeout=10) -> None:
        super().wait_for_gears(PLEX_GEARS_SELECTOR, loading_timeout)

    def click_button(self, button_text:str, driver:Union['UXDriver','UXPlexElement']=None) -> None:
        """Clicks a standard button with matching text.

        Args:
            button_text (str): Text of the button to click.
            driver (UXDriver | UXPlexElement, optional): webdriver root to use if different than default. Defaults to None.

        Usage:

            If you don't provide the root driver, then the main page's Ok button will be clicked and not the popup window's button.
            ::

                popup_window = driver.find_element(By.ID, 'popupID')
                click_button('Ok', driver=popup_window)

            Alternatively:
            ::

                pa = UXDriver()
                popup_window = pa.wait_for_element((By.ID, 'popupID'))
                popup_window.click_button('Ok')
                
        """
        driver = driver or self.driver
        buttons = driver.find_elements(By.TAG_NAME, 'button')
        for b in buttons:
            if b.get_property('textContent') == button_text:
                self.debug_logger.debug(f'Button found with matching text: {button_text}')
                b.click()
                break
            
    def click_action_bar_item(self, item:str, sub_item:str=None) -> None:
        """Clicks on an action bar item.

        Args:
            item (str): Text for the item to click
            sub_item (str, optional): Text for the item if it is within a dropdown after clicking the item. Defaults to None.
        """
        action_bar = self.wait_for_element((By.CLASS_NAME, 'plex-actions'))

        # Check for the "More" link and determine if it's visible
        try:
            more_box = action_bar.find_element(By.LINK_TEXT, "More")
            style = more_box.find_element(By.XPATH, 'ancestor::li').get_dom_attribute('style')
            more_visible = 'none' not in style
            self.debug_logger.debug(f"'More' link {'found and visible' if more_visible else 'found but not visible'}.")
        except NoSuchElementException:
            self.debug_logger.debug('No element found for "More" link.')
            more_visible = False
        # Click on "More" if visible and adjust the action bar
        if more_visible:
            self.debug_logger.debug('Clicking "More" button.')
            more_box.click()
            self.wait_for_element((By.CLASS_NAME, "plex-subactions.open"))
            action_bar = self.wait_for_element((By.CLASS_NAME, 'plex-actions-more'))

        # Handle sub_item or main item click
        if sub_item:
            self.debug_logger.debug("Clicking sub-item.")
            self._click_sub_item(action_bar, item, sub_item)
        else:
            self.debug_logger.debug("Clicking main item.")
            action_item = self.wait_for_element((By.LINK_TEXT, item), type=CLICKABLE)
            action_item.click()

    def _click_sub_item(self, action_bar, item, sub_item):
        """Helper function to click on a sub-item."""
        action_items = action_bar.find_elements(By.CLASS_NAME, "plex-actions-has-more")
        for a in action_items:
            span_texts = a.find_elements(By.TAG_NAME, 'span')
            for s in span_texts:
                if s.get_property('textContent') == item:
                    s.find_element(By.XPATH, "ancestor::a").click()
                    break
        action_bar.find_element(By.LINK_TEXT, sub_item).click()


    def login(self, username, password, company_code, pcn, test_db=True, headless=False):
        self._set_login_vars()
        super().login(username, password, company_code, pcn, test_db, headless)
        self._login_validate()
        self.pcn_switch(self.pcn)
        self.token = self.token_get()
        self.first_login = False
        return (self.driver, self.url_comb, self.token)
    
    
    def _set_login_vars(self):
        self.plex_main = 'cloud.plex.com'
        self.plex_prod = ''
        self.plex_test = 'test.'
        self.sso = '/sso'
        super()._set_login_vars()


    def token_get(self) -> str:
        url = self.driver.current_url
        url_split = url.split('/')
        url_proto = url_split[0]
        url_domain = url_split[2]
        self.url_comb = f'{url_proto}//{url_domain}'
        self.url_token = url.split('?')[1]
        if '&' in self.url_token:
            self.url_token = [x for x in self.url_token.split('&') if 'asid' in x][0]
        return self.url_token
    
    
    def _pcn_switch(self, pcn=None):
        if not pcn:
            pcn = self.pcn
        if self.first_login:
            self.first_login = False
            return
        self.url_token = self.token_get()
        self.driver.get(f'{self.url_comb}/SignOn/Customer/{pcn}?{self.url_token}')
        if UX_INVALID_PCN_MESSAGE in self.driver.current_url.upper():
            raise LoginError(self.environment, self.db, pcn, f'Unable to login to PCN. Verify you have access.')
    
    
    def _login_validate(self):
        url = self.driver.current_url
        if not any(url_part in url.upper() for url_part in SIGNON_URL_PARTS):
            raise LoginError(self.environment, self.db, self.pcn_name, 'Login page not detected. Please validate login credentials and try again.')
        


class UXPlexElement(PlexElement):
    def __init__(self, webelement, parent):
        super().__init__(webelement, parent)


    def sync_picker(self, text_content:str, clear:bool=False, date:bool=False, column_delimiter:str='\t') -> None:
        """Sync the picker element to the provided value.

        Args:
            text_content (str): Desired value for the picker
            clear (bool, optional): Clear the picker if providing a blank text_content. Defaults to False.
            date (bool, optional): If the picker is a date picker. This should be detected automatically, but can be forced if behavior is unexpected.. Defaults to False.
            column_delimiter (str, optional): Delimiter for splitting the popup row's text for searching exact matches. Defaults to '\t'. 

        Raises:
            NoRecordError: If the drop-down picker does not have a matching option with the provided text content.
            NoRecordError: If the popup window does not return any results with the provided text content.
            NoSuchElementException: If the popup window has results, but there was no element matching the text content.
        """
        if not text_content and not clear:
            return
        picker_type = self.get_attribute('class')
        if picker_type == 'input-sm':
            date = True
        if self.tag_name == 'select':
            self.debug_logger.debug('Picker type is selection list.')
            self._handle_select_picker(text_content)
            return
        self.debug_logger.debug('Handling non-select picker.')
        # Check for existing selected item
        matching = self._check_existing_selection(text_content)

        # If there's no existing matching item, send the new text and process the picker
        if not matching and not clear:
            self.send_keys(text_content)
            self.send_keys(Keys.TAB)
            self._handle_popup_or_picker(text_content, date, column_delimiter)
    
    
    def _handle_select_picker(self, text_content):
        # Visible text content always collapses repeated spaces. Need to normalize searched input to account for this.
        # I don't think there should ever by any tab or newline characters within these options, but this would normalize them as well.
        # This action shouldn't be performed for non-select type pickers since the initial search uses exact database values retaining sequencial spaces.
        text_content = ' '.join(text_content.split())
        _select = Select(self)
        current_selection = _select.first_selected_option.text
        if current_selection == text_content:
            self.debug_logger.debug(f'Picker selection: {current_selection} matches {text_content}')
            return
        matching = any(o.text == text_content for o in _select.options)
        if matching:
            self.debug_logger.info(f'Matching option found. Picking {text_content}')
            _select.select_by_visible_text(text_content)
            self.send_keys(Keys.TAB)
        else:
            self.debug_logger.info(f'No matching selection available for {text_content}')
            raise NoRecordError(f'No matching selection available for {text_content}')
        

    def _check_existing_selection(self, text_content):
        try:
            self.debug_logger.debug('Trying to locate an existing selected item.')
            selected_element = self.wait_for_element(
                (By.XPATH, "preceding-sibling::div[@class='plex-picker-selected-items']"),
                driver=self,
                timeout=1
            )
            if selected_element:
                current_text = self.wait_for_element(
                    (By.CLASS_NAME, "plex-picker-item-text"),
                    driver=selected_element
                ).get_property('textContent') # This will retain sequencial space characters in the value.
                
                if current_text == text_content:
                    self.debug_logger.debug(f'Current text: {current_text} matches provided text: {text_content}.')
                    return True
                
                self.debug_logger.info(f'Current text: {current_text} does not match provided text: {text_content}')
                self.send_keys(Keys.BACKSPACE)
                self.clear()
        except (NoSuchElementException, TimeoutException):
            self.debug_logger.debug('No initial selected item detected.')
        return False
    

    def _handle_popup_or_picker(self, text_content, date, column_delimiter):
        try:
            picker_xpath = "preceding-sibling::div[@class='plex-picker-item']" if date else "preceding-sibling::div[@class='plex-picker-selected-items']"
            self.wait_for_element((By.XPATH, picker_xpath), driver=self, timeout=5)
            self.debug_logger.info(f'Picker has been filled in with {text_content}')
        except (TimeoutException, NoSuchElementException):
            self._handle_popup_window(text_content, column_delimiter)


    def _handle_popup_window(self, text_content, column_delimiter):
        try:
            self.debug_logger.debug('Checking for a popup window.')
            popup = self.wait_for_element((By.CLASS_NAME, 'modal-dialog.plex-picker'), timeout=3)
            multi = 'plex-picker-multi' in popup.get_attribute('class')
            self.wait_for_gears()

            items = popup.find_elements(By.CLASS_NAME, 'plex-grid-row')
            if not items:
                self._handle_no_records_popup(popup, text_content)
            
            option_found = self._find_and_click_option(items, text_content, column_delimiter)
            
            if not option_found:
                raise NoSuchElementException(f'No matching elements found for {text_content}')
            if multi:
                self.debug_logger.info('Multi-picker, clicking ok on the popup window.')
                self.click_button('Ok', driver=popup)

        except (TimeoutException, NoSuchElementException):
            self.debug_logger.info(f'No matching elements found for {text_content}')
            raise


    def _handle_no_records_popup(self, popup, text_content):
        result_text = popup.find_element(By.TAG_NAME, 'h4').get_property('textContent')
        if 'No records' in result_text:
            self.debug_logger.info(f'No records found for {text_content}')
            popup.find_element(By.CLASS_NAME, 'modal-footer').find_element(By.LINK_TEXT, 'Cancel').click()
            raise NoRecordError(f'No records found for {text_content}')

    def _find_and_click_option(self, items, text_content, column_delimiter):
        for item in items:
            item_columns = item.get_property('innerText').split(column_delimiter)
            if text_content in item_columns:
                self.debug_logger.info(f'Found matching item with text {item.text}.')
                item.click()
                return True
        return False
