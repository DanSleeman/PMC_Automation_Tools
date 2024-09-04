from typing import Literal, Union
from pmc_automation_tools.driver.common import (
    PlexDriver,
    PlexElement,
    VISIBLE,
    INVISIBLE,
    CLICKABLE,
    EXISTS,
    )
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select



class GenericDriver(PlexDriver):
    def __init__(self, driver_type: Literal['edge', 'chrome'], *args, **kwargs):
        super().__init__(environment='ux', *args, driver_type=driver_type, **kwargs)
        for k, v in kwargs.items():
            setattr(self, k, v)
    
    def wait_for_element(self, selector, *args, driver=None, timeout=15, type=VISIBLE, ignore_exception=False) -> 'GenericElement':
        return super().wait_for_element(selector, *args, driver=driver, timeout=timeout, type=type, ignore_exception=ignore_exception, element_class=GenericElement)
    
    def login(self, url) -> 'GenericDriver':
        self.driver = self._driver_setup(self.driver_type)
        self.driver.get(url)
        return self.driver
    launch = login
    
    def click_button(self):...
    def token_get(self):...
    def _pcn_switch(self):...

class GenericElement(PlexElement):
    def __init__(self, webelement, parent):
        super().__init__(webelement, parent)
    
    def sync_picker(self, sync_value:Union[int, str], text:bool=True) -> None:
        if not isinstance(sync_value, (int, str)):
            raise TypeError("sync_value must be an int or str")
        _select = Select(self)
        if isinstance(sync_value, str):
            if text:
                _select.select_by_visible_text(sync_value)
                return None
            _select.select_by_value(sync_value)
            return None
        _select.select_by_index(sync_value)