# Plex Manufacturing Cloud (PMC) Automation Tools

This library serves two main functions.

1. Methods to log into PMC and automate tasks under a user's account.
    * Supports classic and UX.
    * This is basically a wrapper around Selenium with specific functions designed around how the PMC screens behave.

2. Methods for calling PMC data sources.
    * Classic SOAP data sources
    * UX REST data sources
    * Modern APIs (developer portal)

## Table of Contents
- [Plex Manufacturing Cloud (PMC) Automation Tools](#plex-manufacturing-cloud-pmc-automation-tools)
  - [Table of Contents](#table-of-contents)
  - [Requirements](#requirements)
  - [Utilities](#utilities)
    - [create\_batch\_folder](#create_batch_folder)
    - [setup\_logger](#setup_logger)
  - [PlexDriver Functions](#plexdriver-functions)
    - [wait\_for\_element](#wait_for_element)
    - [wait\_for\_gears](#wait_for_gears)
    - [wait\_for\_banner](#wait_for_banner)
    - [login](#login)
    - [token\_get](#token_get)
    - [pcn\_switch](#pcn_switch)
    - [click\_button](#click_button)
    - [click\_action\_bar\_item](#click_action_bar_item)
  - [PlexElement Functions](#plexelement-functions)
    - [sync\_picker](#sync_picker)
    - [sync\_textbox](#sync_textbox)
    - [sync\_checkbox](#sync_checkbox)
    - [screenshot](#screenshot)
  - [DataSource Functions](#datasource-functions)
    - [set\_auth](#set_auth)
    - [call\_data\_source](#call_data_source)
      - [ApiDataSource unique details](#apidatasource-unique-details)
  - [DataSourceInput Functions](#datasourceinput-functions)
    - [pop\_inputs](#pop_inputs)
    - [purge\_empty](#purge_empty)
  - [UXDataSourceInput Unique Functions](#uxdatasourceinput-unique-functions)
    - [type\_reconcile](#type_reconcile)
    - [get\_to\_update](#get_to_update)
    - [purge\_empty](#purge_empty-1)
      - [Tips](#tips)
  - [DataSourceResponse Functions](#datasourceresponse-functions)
    - [save\_csv](#save_csv)
    - [save\_json](#save_json)
    - [get\_response\_attribute](#get_response_attribute)
  - [Usage Examples](#usage-examples)
      - [Example 1](#example-1)
      - [Example 2](#example-2)
      - [Example 3](#example-3)
      - [Example 4](#example-4)

## Requirements

* Selenium
* pywin32
* Requests
* urllib3
* zeep

In order to make classic SOAP calls, you will also need the WSDL files from Plex. 

They do not expose their WSDL URL anymore, but the files are on the community.



## Utilities

### create_batch_folder

Create a batch folder, useful for recording transactions by run-date.

Parameters
* root - Root directory for where to create the batch folder
* batch_code - Provide your own batch code to be used instead of generating one. Overrides include_time parameter.
* include_time - Include the timestamp in the batch code.
* test - Test batches. Stored in a TEST directory.

Default format: YYYYmmdd

Format with include_time: YYYYmmdd_HHMM

### setup_logger

Setup a logging file.

Parameters
* name - logger name
* log_file - filename for the log file.
* file_format - "DAILY" | "MONTHLY" | "". Will be combined with the log_file filename provided.
* level - log level for the logger. logging module levels.
* formatter - logging formatter
* root_dir - root directory to store the log file

## PlexDriver Functions

Sub classes `UXDriver` and `ClassicDriver`

Parameters
* driver_type - supports edge and chrome browsers
* debug_level - level of debugging for built in debug printing during operations

Debug commands are printed to stdout for the `PlexDriver` objects.

```python
from pmc_automation_tools import UXDriver, ClassicDriver
u = UXDriver(driver_type='edge')
c = ClassicDriver(driver_type='chrome')
```

### wait_for_element

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

### wait_for_gears

Waits for the visibiility and then invisibility of the "gears" gif that shows when pages load.

Parameters
* loading_timeout - How long to wait after the gears become visible. Default 10.

The loading gif doesn't always display for long enough to be detected.

If the gif is detected, then the wait for it to become invisible is longer and controlled by the parameter.

```python
pa.wait_for_gears(loading_timeout=30) # Maybe a report takes 20-30 seconds to run.
```

### wait_for_banner

Waits for the banner to appear after a record is updated or if there is an error.

Currently only supported in `UXDriver` class.

### login

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

UX token is supplied with the full query format. __asid=############

Depending on where in the URL it is placed, should be manually prefixed with a ? or &

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

### token_get

Return the current session token from the URL.

This is needed in order to maintain the proper PCN when navigating between them.

Otherwise, the screens may revert back to your home PCN.

### pcn_switch

alias: switch_pcn

Switch to the PCN provided

Paramters
* PCN
    * PCN number for the destination PCN

For UX, the number itself is used to switch PCNs using a static URL: 
```python
pa = UXDriver(driver_type='edge')
driver, url_comb, token = pa.login(username, password, company_code, pcn, test_db=True)

pa.pcn_switch('######')
# Equivalent to: 
driver.get(f'{url_comb}/SignOn/Customer/######?{token}')
```

For classic, you will need to have a JSON file to associate the PCN number to the PCN name. 

This will be prompted with instructions to create it if missing.

### click_button

Clicks a button with the provided text.

Parameters
* button_text - Text to search for
* driver - root driver to start the search from. Can be used to click "Ok" buttons from within popups without clicking the main page's 'Ok' button by mistake.

### click_action_bar_item

Used to click an action bar item on UX screens.

Parameters
* item - Text for the action bar item to click
* sub_item - Text for the sub item if the item is for a drop-down action

If the screen is too small, or there are too many action bar items, the function will automatically check under the "More" drop-down list for the item.

## PlexElement Functions

Plex specific wrappers around Selenium `WebElement` objects.

Standard Selenium functionality should be retained on these objects.

### sync_picker

Updates the picker element's content to match the provided value. Does nothing if the contents match.

Works for the magnifying style pickers and Select style drop-down lists.

- [ ] TODO: Add support for multi-picker value selection
- [ ] TODO: Add support for `ClassicDriver` object

### sync_textbox

Updates a textbox value to match the provided value.

### sync_checkbox

Updates a checkbox state to match the provided state.

### screenshot

Wrapper around Selenium's screenshot functionality.

Saves a screenshot of the element to the screenshots folder using the element's ID and name.

## DataSource Functions

Convenience functions for handling Plex specific web service/API calls.

Supports Classic SOAP, UX REST, and Developer Portal REST API calls.

Classes
* ClassicDataSource
* UXDataSource
* ApiDataSource

Parameters
* auth - authentication. See `set_auth` function for more details
* test_db - boolean. Connect to the test database if True (default).
* pcn_config_file - file that stores pcn web service credentials.

### set_auth

Generate authentication to be used in the call.

Parameters
* key
  * Classic: HTTPBasic | str for pcn_config.json lookup
  * UX: HTTPBasic | str for pcn_config.json lookup
  * API: API key as a string

Supports using a pcn_config.json file to reference the PCN's credentials.

Format expected for JSON file:

```json
{
    "PCN_REF":{
        "api_user":"Username@plex.com",
        "api_pass":"password"
    },
    "PCN_2_REF":{
        "api_user":"Username2@plex.com",
        "api_pass":"password2"
    }
}
```
If not using the file, and not providing an HTTPBasicAuth object, you will be prompted to provide your credentials via the console.

### call_data_source

Triggers the data source request.

Parameters
* query - DataSourceInput object

#### ApiDataSource unique details

Parameters
* pcn - string or list of strings containing the PCN number(s).

This directs the API to the appropriate PCN.

## DataSourceInput Functions

Input object that stores the attributes for building the proper request format.

Classes
* ClassicDataSourceInput
* UXDataSourceInput
* ApiDataSourceInput

### pop_inputs

Removes attributes provided.

Parameters
* args - Any attribute name provided here will be removed
* kwargs - use "keep" with a list of arguments to keep. All others will be removed.

You can pass an empty list to the `keep` kwarg which will remove all other attributes.

### purge_empty

Removes empty/Nonetype attributes from the input.

## UXDataSourceInput Unique Functions

Parameters
* template_folder - folder containing json template files from the UX data sources screen "Sample Request".

Template files are expected in order to use the `type_reconcile` function.

### type_reconcile

Adjusts the attribute types to match the expected types of the data source.

This is useful when dealing with CSV input files since the attributes will all be consider strings and will not be useable in the request call.

### get_to_update

Takes a `UXDataSourceResponse` object to update the attributes to match what was returned.

This is useful for required fields from a data source which would be changed if you don't provide the input.

It avoids requiring an initial SQL query for the update calls.

### purge_empty

Additionally removes any attributes not existing in the input_types dictionary.


#### Tips

When calling a UX data source, save a json file based on the sample call from the Plex screen.

* Locate the data source details and click on "Sample Request"  
![](./img/ux_data_source_details.jpg)
* Click "Show more"  
![](./img/ux_data_source_sample_1.jpg)
* Highlight the JSON and copy the text  
![](./img/ux_data_source_sample_2.jpg)
* Paste into notepad
* Save the file as a .json file with a name matching the data source ID  
![](./img/ux_data_source_template.jpg)


When initializing your data source input object, pass in the template file path.

```python
u = UXDataSourceInput(10941,template_folder='ds_templates')
u.pop_inputs(keep=[]) # Removes the default values from the template file
```

Using this method, the `UXDataSourceInput` object will have an attribute which records the expected input types properly.

This will allow you to use a csv source file for all the inputs without needing to define the types manually.

Before making the data source call, use the `type_reconcile` function to match up the current attributes to the expected types.

## DataSourceResponse Functions

### save_csv

Saves the response into a csv file.

Parameters
* out_file - file location to save.

### save_json

Saves the response into a json file.

Parameters
* out_file - file location to save.

### get_response_attribute

Extract the attribute from the formatted data in the response.

Parameters
* attribute - attribute name from the response to return
* preserve_list - Pass true to retain a list of attributes even if a single item is found.
* kwargs - arbitrary number of filters to use when searching for a specific attribute to return.

EX: Calling the customer list API for all active customers.
```python
# Will return a list of ALL active customer IDs
cust_id = r.get_response_attribute('id')
# Will return the id for the customer with name 'NISSAN MOTOR'
cust_id = r.get_response_attribute('id', name='NISSAN MOTOR')
```

## Usage Examples

#### Example 1

Automate data entry into screens which do not support or have an upload, datasource, or API to make the updates.

This example demonstrates updating a container type's dimensions from a csv file.

https://github.com/ClawhammerLobotomy/PMC_Automation_Tools/blob/d3846296871f0b4b68daa9140523838668774723/examples/example_1.py#L1-L38

#### Example 2

Call a UX datasource from a Plex SQL query.

This example demonstrates saving the SQL records to a file in a batch folder which can be referenced to prevent duplicate updates if running in the same batch.

This data source is also for updating a container types's dimensions.

https://github.com/ClawhammerLobotomy/PMC_Automation_Tools/blob/d3846296871f0b4b68daa9140523838668774723/examples/example_2.py#L1-L32

#### Example 3

Call a classic data source from a csv file row.

This demonstrates adding supplier cert records into a new PCN based on the current cert records in another PCN.

https://github.com/ClawhammerLobotomy/PMC_Automation_Tools/blob/d3846296871f0b4b68daa9140523838668774723/examples/example_3.py#L1-L52

#### Example 4

Call a developer portal API to download EDI documents and save them to a file.

https://github.com/ClawhammerLobotomy/PMC_Automation_Tools/blob/d3846296871f0b4b68daa9140523838668774723/examples/example_4.py#L1-L47
