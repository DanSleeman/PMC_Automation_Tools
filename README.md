# Plex Manufacturing Cloud (PMC) Automation Tools

This library serves two main functions.

1. Methods to log into PMC and automate tasks under a user's account.
    * Supports classic and UX.
    * This is basically a wrapper around Selenium with specific functions designed around how the PMC screens behave.

2. Methods for calling PMC data sources.
    * Classic SOAP data sources
    * UX REST data sources
    * Modern APIs (developer portal)

## Requirements

* Selenium
* pywin32
* Requests
* urllib3
* zeep

In order to make classic SOAP calls, you will also need the WSDL files from Plex. 

They do not expose their WSDL URL anymore, but the files are on the community.

## 

## Usage

Automate data entry into screens which do not support or have an upload, datasource, or API to make the updates.

```python

from pmc_automation_tools import UXDriver

# UX screens
pa = UXDriver(driver_type='edge')
driver, url_comb, token = pa.login(username,password,company_code,pcn,test_db=True)
token = pa.pcn_switch(destination_pcn)
pa.driver.get(f'{url_comb}/VisionPlex/Screen?__actionKey=6531&{token}&__features=novirtual') # &__features=novirtual will stop the results grid from lazy loading.
pa.wait_for_gears()
pa.wait_for_element((By.NAME,'ContainerTypenew'))
pa.ux_click_button('Search')
pa.wait_for_gears()

with open(csv_file,'r',encoding='utf-8-sig') as f:
    c = csv.DictReader(f)
    for r in c:
        container_type = r['container_type']
        cube_width = r['cube_width']
        cube_height = r['cube_height']
        cube_length = r['cube_length']
        cube_unit = r['cube_unit']
        pa.wait_for_element((By.LINK_TEXT,container_type)).click()
        pa.wait_for_gears()
        pa.wait_for_element((By.NAME,'CubeLength')).sync_textbox(cube_length)
        pa.wait_for_element((By.NAME,'CubeWidth')).sync_textbox(cube_width)
        pa.wait_for_element((By.NAME,'CubeHeight')).sync_textbox(cube_height)
        pa.wait_for_element((By.NAME,'UnitKey')).sync_picker(cube_unit)
        pa.ux_click_button('Ok')
        pa.wait_for_banner()
        pa.wait_for_gears()
        pa.wait_for_element((By.NAME,'ContainerTypenew'))
        pa.wait_for_gears()
        pa.wait_for_banner()
```

## Functions

### PlexDriver Functions

`wait_for_element`

Waits for until an element condition is met.

Parameters
* selector - Selenium tuple selector
* driver - WebDriver or WebElement as starting point for locating the element
* timeout - How long to wait until the condition is met
* type - What type of condition
    * Visible (default)
    * Invisible
    * Clickable
    * Exists (Don't wait at all, just retun a PlexElement object)
* ignore_exception - Don't raise an exception if the condition is not met.

Returns PlexElement object

```python 
checklist_box = pa.wait_for_element((By.NAME, 'ChecklistKey'), type=CLICKABLE)
```
`wait_for_gears`

Waits for the visibiility and then invisibility of the "gears" gif that shows when pages load.

Parameters
* loading_timeout - How long to wait after the gears become visible.

The loading gif doesn't always display for long enough to be detected.

If the gif is detected, then the wait for it to become invisible is longer and controlled by the parameter.

```python
pa.wait_for_gears(loading_timeout=30) # Maybe a report takes 20-30 seconds to run.
```

`wait_for_banner`

Waits for the banner to appear after a record is updated or if there is an error.

`login`

Log in to Plex with the provided credentials.

Parameters
* username - PMC username
* password - PMC password
* company_code - PMC company code
* pcn - PCN number
    * Used to lookup the proper PCN to click in a classic login process.
* test_db - If true, log into the test database
* headless - Run the chrome/edge driver in headless mode.
    * Note: UX does not always behave as expected when using this option.

Returns
* driver - The webdriver that can be used with all the Selenium actions and PMC driver actions
* url_comb - The combined url to be used for direct URL navigation within PMC
    * Classic - https://www.plexonline.com/__SESSION_TOKEN__ | https://test.plexonline.com/__SESSION_TOKEN__
    * UX - https://cloud.plex.com | https://test.cloud.plex.com
* token - The current session token. Needed to retain the proper PCN and screen when navigating directly to URLs.
    * Classic - This is built into url_comb since it always comes directly after the domain
    * UX - This is held in a query search parameter, and must be generated after changing PCNs, or the system will navigate using your home PCN.

UX token is supplied with the full query format. __asid=################

Depending on where in the URL it is placed, should be manually prefixed with a ? or &.

UX:
```python
pa = UXDriver(driver_type='edge')
driver, url_comb, token = pa.login(username, password, company_code, pcn, test_db=True)
pa.driver.get(f'{url_comb}/VisionPlex/Screen?__actionKey=6531&{token}&__features=novirtual')
```
Classic:
```python
pa = ClassicDriver(driver_type='edge')
driver, url_comb, token = pa.login(username, password, company_code, pcn, test_db=True)
pa.driver.get(f'{url_comb}/Modules/SystemAdministration/MenuSystem/MenuCustomer.aspx') # This is the PCN selection screen.
```

`token_get`

Return the current session token from the URL.

This is needed in order to maintain the proper PCN when navigating between them.

Otherwise, the screens may revert back to your home PCN.

`pcn_switch` alias `switch_pcn`

Switch to the PCN provided

Paramters
* PCN
    * PCN number for the destination PCN

For UX, the number itself is used to switch PCNs using a static URL: 
```python
pa = UXDriver(driver_type='edge')
driver, url_comb, token = pa.login(username, password, company_code, pcn, test_db=True)

pa.pcn_switch('#######')
# Equivalent to: 
driver.get(f'{url_comb}/SignOn/Customer/#######?{token}')
```

`click_button`

Clicks a button with the provided text.

Parameters
* button_text - Text to search for
* driver - root driver to start the search from. Can be used to click "Ok" buttons from within popups without clicking the main page's 'Ok' button by mistake.

`click_action_bar_item`

Used to click an action bar item on UX screens.

Parameters
* item - Text for the action bar item to click
* sub_item - Text for the sub item if the item is for a drop-down action

If the screen is too small, or there are too many action bar items, the function will automatically check under the "More" drop-down list for the item.

### Utilities

`create_batch_folder`

Create a batch folder, useful for recording transactions by run-date.

Parameters
* root - Root directory for where to create the batch folder
* batch_code - Provide your own batch code to be used instead of generating one. Overrides include_time parameter.
* include_time - Include the timestamp in the batch code.
* test - Test batches. Stored in a TEST directory.

Default format: YYYYmmdd

Format with include_time: YYYYmmdd_HHMM

`setup_logger`

Setup a logging file.

Parameters
* name - logger name
* log_file - filename for the log file.
* file_format - "DAILY" | "MONTHLY | "". Will be combined with the log_file provided.
* level - log level for the logger
* formatter - loggin formatter
* root_dir - root directory to store the log file

### PlexElement Functions

`sync_picker`

`sync_textbox`

`sync_checkbox`

`save_element_image`
