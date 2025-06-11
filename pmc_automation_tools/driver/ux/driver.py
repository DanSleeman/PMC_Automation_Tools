from typing import Literal, Union
from pmc_automation_tools.driver.common import (
    PlexDriver,
    PlexElement,
    VISIBLE,
    INVISIBLE,
    CLICKABLE,
    EXISTS,
    SIGNON_URL_PARTS,
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
    LoginError,
    GridColumnError,
    GridRowError
    )
import time
import re
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


    def find_element_by_label(self, label, driver=None, timeout=15, type=VISIBLE, ignore_exception=False) -> 'UXPlexElement':
        try:
            label = label.replace('_',' ').lower()
            by = By.XPATH
            _label = f"//label[normalize-space(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'))='{label}']"
            _element_group = f"/ancestor::div[contains(@class,'plex-control-group')]"
            _controls = f"//div[contains(@class,'plex-controls')]"
            value = f"{_label}{_element_group}{_controls}"
            input_wrapper = self.wait_for_element(by, value, driver=driver, timeout=timeout, type=type, ignore_exception=ignore_exception)
            if input_wrapper:
                first_child = "./*[1]"
                child_element = UXPlexElement(input_wrapper.find_element(by, first_child), self)
                child_tag = child_element.tag_name
                child_class = child_element.get_attribute('class')
                if child_tag == 'div':
                    if child_class == 'plex-controls-element':
                        child_element = UXPlexElement(child_element.find_element(by, first_child), self)
                        child_class = child_element.get_attribute('class')
                    if child_class == 'plex-picker-control':
                        child_element = UXPlexElement(input_wrapper.find_element(by, ".//input"), self)
                    elif child_class == 'plex-select-wrapper':
                        child_element = UXPlexElement(input_wrapper.find_element(by, ".//select"), self)
                    elif 'ui-textarea-wrapper' in child_class:
                        child_element = UXPlexElement(input_wrapper.find_element(by, ".//textarea"), self)
                return child_element
        except (TimeoutException, StaleElementReferenceException, NoSuchElementException):
            if ignore_exception:
                return None
            raise

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

    banner = wait_for_banner
    def _banner_handler(self, banner_type, banner):
        if banner_type == BANNER_SUCCESS:
            return 
        else:
            banner_text = banner.get_property('textContent')
            error_elements = self.driver.find_elements(By.CSS_SELECTOR, 'label.plex-error')
            error_fields = {}
            for _el in error_elements:
                src_id = _el.get_attribute('for')
                src_name = self.driver.find_element(By.ID, src_id).get_attribute('name')
                error_fields[src_name] = _el.get_property('textContent')
            raise UpdateError(banner_text, **error_fields)
    

    def wait_for_gears(self, loading_timeout=10) -> None:
        super().wait_for_gears(PLEX_GEARS_SELECTOR, loading_timeout)
    gears = wait_for_gears
    
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
        
    
    def highlight_row(self, value:str, column:Union[str|int], row_offset:int=0):
        """
        Clicks a row in a grid with a matching value in the column provided.

        Args:
            value (str): cell contents to use for finding a matching row
            column (str|int): the column name or index of the column that should be used for matching
            row_offset(int): if there are multiple matching rows, the offset can be used to indicate which of them should be highlighted.
        """
        column_match = None
        if isinstance(column, str):
            # There are usually two thead elements for any given grid. However, they should both work for finding the proper column index for a given column title.
            _plex_grid_header = self.driver.find_element(By.TAG_NAME, 'thead')
            _header_cells = _plex_grid_header.find_elements(By.CLASS_NAME, 'plex-grid-header-cell')
            for i, h in enumerate(_header_cells):
                abbr = h.find_elements(By.TAG_NAME, 'abbr')
                if len(abbr) > 0:
                    if abbr[0].get_attribute('textContent') == column:
                        column_match = i
                        break
            if column_match is None:
                raise GridColumnError(f'No column detected in the table matching provided value: {column}.')
            column = column_match
        link_check = self.driver.find_element(By.XPATH, f"//tr[contains(@class,'plex-grid-row selectable')]/td[@data-col-index={column}]/a")
        if link_check:
            matching_rows = self.driver.find_elements(By.XPATH, f"//tr[contains(@class,'plex-grid-row selectable')]/td[@data-col-index={column}]/a[text()='{value}']")
        else:
            matching_rows = self.driver.find_elements(By.XPATH, f"//tr[contains(@class,'plex-grid-row selectable')]/td[@data-col-index={column} and text()='{value}']")
        if len(matching_rows) == 0:
            raise GridRowError(f"Plex grid row not found for column index {column} containing value: {value}.")
        if len(matching_rows) > 1:
            print(f"Multiple rows match the provided text content. Selecting row number {row_offset} from these results.")
        matching_rows[row_offset].find_element(By.XPATH, '..').click() # Click the TR element to avoid clicking a hyperlink in the TD
        return None


class UXPlexElement(PlexElement):
    def __init__(self, webelement, parent):
        super().__init__(webelement, parent)


    def _type_detect(self, ignore_exception=False):
        try:
            wrapper_element = self.find_element(By.XPATH, "./ancestor::div[contains(@class,'plex-control-group')]//div[contains(@class,'plex-controls')]/*[1]")
            wrapper_tag = wrapper_element.tag_name
            wrapper_class = wrapper_element.get_attribute('class')
            if wrapper_tag == 'input':
                return self.get_attribute('type')
            elif wrapper_tag == 'div':
                if wrapper_class == 'plex-controls-element':
                    wrapper_element = wrapper_element.find_element(By.XPATH, "./*[1]")
                    wrapper_tag = wrapper_element.tag_name
                    wrapper_class = wrapper_element.get_attribute('class')
                if wrapper_tag == 'input':
                    return self.get_attribute('type')
                if wrapper_class == 'plex-picker-control':
                    return 'picker'
                elif wrapper_class == 'plex-select-wrapper':
                    return 'picker'
                elif 'ui-textarea-wrapper' in wrapper_class:
                    return 'text'
        except (TimeoutException, StaleElementReferenceException, NoSuchElementException):
            if ignore_exception:
                return ''
            raise


    def sync(self, value:Union[str, int, bool], **kwargs) -> None:
        clear = getattr(kwargs, 'clear', False)
        date = getattr(kwargs, 'date', False)
        column_delimiter = getattr(kwargs, 'column_delimiter', '\t')
        if not hasattr(self, 'sync_type'):
            self.sync_type = self._type_detect(ignore_exception=True)
        if hasattr(self, 'sync_type'):
            if self.sync_type == 'checkbox':
                self.sync_checkbox(value)
            elif self.sync_type ==  'text':
                self.sync_textbox(value, clear=clear)
            elif self.sync_type ==  'picker':
                self.sync_picker(value, clear=clear, date=date, column_delimiter=column_delimiter)
            else:
                raise ValueError(f'Unexpected sync type attribute for UXPlexElement object. Value: {self.sync_type}. Expected values checkbox, text, picker')
        else:
            raise AttributeError(f'UXPlexElement object does not have a defined sync type.')

    def sync_picker(self, text_content:Union[str, list], clear:bool=False, date:bool=False, column_delimiter:str='\t') -> None:
        """Sync the picker element to the provided value.

        Args:
            text_content (str|list): Desired value(s) for the picker
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
        # Check for existing selected item
        if isinstance(text_content, list):
            self.debug_logger.debug('Handling non-select multi picker.')
        else:
            text_content = [text_content]
            self.debug_logger.debug('Handling non-select picker.')
        matching = self._check_existing_multiple(text_content)
        self.debug_logger.debug(f'Matching value: {matching}')
        if not isinstance(matching, bool):
            # The response could return an integer value for the number of existing values if there is a difference.
            # Must check for boolean instance rather than integer since bool is a subclass of int.
            self.debug_logger.debug(f'Detected difference between current and provided values. Sending backspace {matching} times.')
            self.send_keys(Keys.BACK_SPACE * matching)
            matching = False
        if not matching and not clear:
            if isinstance(text_content, list):
                for t in text_content:
                    self.debug_logger.debug(f'Entering value {t} into multi-select picker.')
                    self.send_keys(t)
                    self.send_keys(Keys.TAB)
                    self._handle_popup_or_picker(t, date, column_delimiter)
            else:
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
        
    def _check_existing_multiple(self, text_content:list):
        try:
            self.debug_logger.debug('Trying to locate existing selected items.')
            text_content.sort()
            selected_elements = self.find_elements(By.XPATH, "preceding-sibling::div[@class='plex-picker-selected-items']")
            if len(selected_elements) > 0: # Should always only be 1 element
                self.debug_logger.debug('Found selected item wrapper element.')
                current_text = selected_elements[0].find_elements(By.CLASS_NAME, 'plex-picker-item-text')
                if len(current_text) > 0:
                    self.debug_logger.debug('Multiple selected items detected.')
                    last_element = current_text[-1]
                    last_text = last_element.get_property('textContent')
                    self.debug_logger.debug(f'{len(current_text)} elements found. Last element text: {last_text}')
                    match = re.fullmatch(r'([0-9,]+) more', last_text)
                    if match:
                        self.debug_logger.debug('Too many elements selected. Expanding selection to check whole list.')
                        last_element.click()
                        current_text = selected_elements[0].find_elements(By.CLASS_NAME, 'plex-picker-item-text')
                    compare_value = [c.get_property('textContent') for c in current_text]
                    compare_value.sort()
                    self.debug_logger.debug(f'Current value: {compare_value}\nInput value: {text_content}')
                    if text_content == compare_value:
                        self.debug_logger.debug('Two lists match, not making any updates.')
                        return True
                    else:
                        self.debug_logger.debug('Lists do not match.')
                        return len(compare_value)
        except (NoSuchElementException, TimeoutException):
            self.debug_logger.debug('No initial selected item detected.')
        return False
    
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
            self.wait_for_element((By.CLASS_NAME, 'modal-dialog.plex-picker'), timeout=3, type=INVISIBLE, ignore_exception=True)

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
