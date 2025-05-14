# Plex Manufacturing Cloud (PMC) Automation Tools
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

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
  - [Installation](#installation)
  - [Utilities](#utilities)
    - [create\_batch\_folder](#create_batch_folder)
    - [setup\_logger](#setup_logger)
    - [read\_updated](#read_updated)
    - [save\_updated](#save_updated)
  - [PlexDriver Functions](#plexdriver-functions)
    - [wait\_for\_element](#wait_for_element)
    - [wait\_for\_elements](#wait_for_elements)
    - [find\_element\_by\_label](#find_element_by_label)
    - [wait\_for\_gears](#wait_for_gears)
    - [wait\_for\_banner](#wait_for_banner)
    - [login](#login)
    - [token\_get](#token_get)
    - [pcn\_switch](#pcn_switch)
    - [click\_button](#click_button)
    - [click\_action\_bar\_item](#click_action_bar_item)
  - [GenericDriver Functions](#genericdriver-functions)
    - [launch](#launch)
  - [PlexElement Functions](#plexelement-functions)
    - [sync](#sync)
    - [sync\_picker](#sync_picker)
    - [sync\_textbox](#sync_textbox)
    - [sync\_checkbox](#sync_checkbox)
    - [screenshot](#screenshot)
  - [GenericElement Functions](#genericelement-functions)
    - [sync\_picker](#sync_picker-1)
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
      - [Example 5](#example-5)

## Requirements

* Selenium
* Requests
* urllib3
* zeep
* openpyxl

In order to make classic SOAP calls, you will also need the WSDL files from Plex. 

They do not expose their WSDL URL anymore, but the files are on the community.

## Installation

```bash
pip install pmc-automation-tools
```

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

### read_updated

Read in a json file of already updated records.

Useful to skip over anything processed by previous runs.

Parameters:
* in_file - file containing the data to read.

Returns:
* json object or empty list

### save_updated

Save a json file containing a list of already processed records.

Useful when dealing with errors and re-running data sources from an un-changed SQL query.

Parameters:
* in_file - file to use to save
* obj - json object to write to file. Typically a list containing dictionaries.

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
import pmc_automation_tools as pa
checklist_box = pa.wait_for_element(By.NAME, 'ChecklistKey', type=pa.CLICKABLE)
```

### wait_for_elements

Waits for until an element condition is met.

Parameters
* selector - Selenium tuple selector
* driver - WebDriver or WebElement as starting point for locating the element
* timeout - How long to wait until the condition is met
* type - What type of condition
    * Visible (default)
    <!-- * Invisible
    * Clickable
    * Exists (Don't wait at all, just retun a PlexElement object) -->
* ignore_exception - Don't raise an exception if the condition is not met.

Returns PlexElement object

```python 
import pmc_automation_tools as pa
attribute_list = pa.wait_for_elements(By.NAME, 'PoLineAttributeValue')
for el in attribute_list:
    el.sync_textbox('Text')
```
### find_element_by_label

Locates an input element using the element's text label.

This is useful for updating or adding a record where the screen has many different types of inputs.

E.X. Operations screen. This has textboxes, checkboxes, pickers, drop-down lists, and large text area elements.

With this function, you can update all the elements using a dictionary of label:value pairs.

This works well with a SQL report that pulls all the data required and the column names equal the field labels.  
The function replaces underscores with spaces automatically.  
Use this when you need to copy records from one PCN to another.

```python
import pmc_automation_tools as pa
# Create a csv file from a SQL report
input_file = 'Operations.csv'
input_records = pa.read_updated(input_file)
ux = pa.UXDriver('chrome')
# ====Log in and navigate to the screen here====
for row in input_records:
    ux.click_action_bar_item('Add')
    for k,v in row.items():
        screen_elem = ux.find_element_by_label(k)
        screen_elem.sync(v)
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

Parameters
* timeout - how long to wait for the banner. Default 10 seconds
* ignore_exception - ignore exception raised when an expected banner class is not detected. Default False

timeout and ignore_exception can be used in some cases.

EX:

The successful update takes a long time, but there may be some initial validation for required fields which make the update fail.

You can then continue to another record after a short time, but capture any error/warnings.

```python
ux.click_button('Apply')
try:
    ux.wait_for_banner(timeout=1, ignore_exception=True)
except UpdateError as e: # UpdateError will only be triggered if a banner with a warning/error banner type is detected before the timeout.
    logger.warning(f'Error making the update. {e.clean_message}') # e.clean_message will show the banner text without any newline characters.
```
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

## GenericDriver Functions

Intended for use with non-Plex websites with similar methods available for use.

### launch

Configures and launches a webdriver session and navigates to the URL provided.

Parameters:

* url - Where to go when launching the webdriver

## PlexElement Functions

Plex specific wrappers around Selenium `WebElement` objects.

Standard Selenium functionality should be retained on these objects.

### sync

Generic function that will sync the element's value based on what type of input it is.

EX:
```python
elem = ux.wait_for_element(By.NAME, 'OperationCode')
elem.sync('Assembly')
# Alternative:
elem = ux.find_element_by_label('Operation Code')
elem.sync('Assembly')
```

### sync_picker

Updates the picker element's content to match the provided value. Does nothing if the contents match.

Works for the magnifying style pickers and Select style drop-down lists.

- [ ] TODO: Add support for `ClassicDriver` object

### sync_textbox

Updates a textbox value to match the provided value.

### sync_checkbox

Updates a checkbox state to match the provided state.

### screenshot

Wrapper around Selenium's screenshot functionality.

Saves a screenshot of the element to the screenshots folder using the element's ID and name.

## GenericElement Functions

### sync_picker

Basic wrapper around Selenium's Select class.

Parameters:
* sync_value - str or int - value to sync to the Select object. int input will select based on index.
* text - bool - True for syncing with visible text. False for value

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

Adjusts the attribute types to match the expected types of the data source.

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

<details>
<summary>
Example 1
</summary>

```python
from pmc_automation_tools import UXDriver
import csv
from selenium.webdriver.common.by import By
username = open('resources/username', 'r').read()
password = open('resources/password', 'r').read()
company_code = open('resources/company', 'r').read()
pcn = '123456'
destination_pcn = '987654'
csv_file = 'container_types.csv'
pa = UXDriver(driver_type='edge') # edge or chrome is supported
driver, url_comb, token = pa.login(username, password, company_code, pcn, test_db=True)
token = pa.pcn_switch(destination_pcn)
pa.driver.get(f'{url_comb}/VisionPlex/Screen?__actionKey=6531&{token}&__features=novirtual') # &__features=novirtual will stop the results grid from lazy loading.
pa.wait_for_gears()
pa.wait_for_element(By.NAME, 'ContainerTypenew')
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
        pa.wait_for_element(By.LINK_TEXT, container_type).click()
        pa.wait_for_gears()
        pa.wait_for_element(By.NAME, 'CubeLength').sync_textbox(cube_length)
        pa.wait_for_element(By.NAME, 'CubeWidth').sync_textbox(cube_width)
        pa.wait_for_element(By.NAME, 'CubeHeight').sync_textbox(cube_height)
        pa.wait_for_element(By.NAME, 'UnitKey').sync_picker(cube_unit)
        pa.ux_click_button('Ok')
        pa.wait_for_banner()
        pa.wait_for_gears()
        pa.wait_for_element(By.NAME, 'ContainerTypenew')
        pa.wait_for_gears()
        pa.wait_for_banner()
```

</details>


#### Example 2

Call a UX datasource from a Plex SQL query.

This example demonstrates saving the SQL records to a file in a batch folder which can be referenced to prevent duplicate updates if running in the same batch.

This data source is also for updating a container types's dimensions.

<details>
<summary>
Example 2
</summary>

```python
from pmc_automation_tools import UXDataSourceInput, UXDataSource, save_updated, read_updated, setup_logger, create_batch_folder
import csv
in_file = 'plex_sql_report.csv'
ds_id = '2360'
pcn = '123456'
update_file = 'updated_records.json'
batch_folder = create_batch_folder(test=True)
logger = setup_logger('Container Updates',log_file='Container_Updates.log',root_dir=batch_folder,level=10) #level=logging.DEBUG
ux = UXDataSource(pcn, test_db=True)
updates = read_updated(update_file)
with open(in_file,'r',encoding='utf-8-sig') as f: # use utf-8-sig if exporting a CSV from classic SDE
    c = csv.DictReader(f)
    for r in c:
        container_type = r['Container_Type']
        try:
            u = UXDataSourceInput(ds_id, template_folder='templates')
            u.pop_inputs(keep=[])
            for k,v in r.items():
                setattr(u,k,v)
            log_record = {k:v for k,v in vars(u).items() if not k.startswith('_')}
            u.pop_inputs('Container_Type')
            u.type_reconcile()
            u.purge_empty()
            if log_record in updates:
                continue
            r = ux.call_data_source(u)
            updates.append(log_record)
            logger.info(f'{pcn} - Datasource: {ds_id} - Container Type: {container_type} Updated.')
        except:
            logger.error(f'{pcn} - Datasource: {ds_id} - Container Type: {container_type} Failed to update.')
        finally:
            save_updated(update_file, updates)
```

</details>

#### Example 3

Call a classic data source from a csv file row.

This demonstrates adding supplier cert records into a new PCN based on the current cert records in another PCN.

<details>
<summary>
Example 3
</summary>

```python
from pmc_automation_tools import (
    ClassicDataSource,
    ClassicDataSourceInput,
    create_batch_folder,
    setup_logger,
    read_updated,
    save_updated
)
from pmc_automation_tools.common.exceptions import ClassicConnectionError
import csv
import os


batch_folder = create_batch_folder(test=True)
logger = setup_logger('Supplier Cert',log_file='certs_added.log',root_dir=batch_folder)
cert_updates_file = os.path.join(batch_folder,'cert_updates.json')
updated_records = read_updated(cert_updates_file)

input_file = 'cert_reference.csv'
pcn = 'PCN name'

wsdl = os.path.join('resources','Plex_SOAP_prod.wsdl')
pc = ClassicDataSource(auth=pcn,test_db=True,wsdl=wsdl)

with open(input_file,'r',encoding='utf-8-sig') as f:
    c = csv.DictReader(f)
    for r in c:
        try:
            ci = ClassicDataSourceInput(57073)
            supplier_code = r['Delete - Supplier Code'] # just for reference
            cert_name = r['Delete - Certification'] # just for reference
            ci.MP1_Supp_Cert_List_Key = r['Supplier_Cert_List_Key']
            ci.MP1_Begin_Date = r['Begin_Date']
            if not r['Begin_Date']:
                # Some certs possibly had no begin date in classic which is not allowed in the data source.
                logger.warning(f'{pcn} - {supplier_code} - {cert_name} : {r["Note"]} - Missing start date.')
                continue
            ci.MP1_Expiration_Date = r['Expiration_Date']
            ci.MP1_Note = r['Note']
            ci.MP1_Parent = r['Parent']
            ci.MP_Supplier_Cert_Key = r['Supplier_Cert_Key']
            ci.Cert_Supplier_No = r['Cert_Supplier_No']
            log_record = {k:v for k,v in vars(ci).items() if not k.startswith('_')}
            if log_record in updated_records:
                continue
            response = pc.call_data_source(ci)
            logger.info(f'{pcn} - {supplier_code} - {cert_name} - Added')
            updated_records.append(log_record)
        except ClassicConnectionError as e:
            logger.error(f'{pcn} - {supplier_code} - {cert_name} - Failed to be added - {str(e)}')
        finally:
            save_updated(cert_updates_file,updated_records)
```

</details>

#### Example 4

Call a developer portal API to download EDI documents and save them to a file.

<details>
<summary>
Example 4
</summary>

```python
from pmc_automation_tools import ApiDataSource, ApiDataSourceInput
from datetime import datetime, timedelta
import base64

test = True
today = datetime.now()
tomorrow = today + timedelta(days=1)
yesterday = today - timedelta(days=1)
pcn = '123456'
api_key = 'API_KEY_HERE'

a = ApiDataSource(auth=api_key, test_db=test)

# Get customer ID
url = 'https://connect.plex.com/mdm/v1/customers'
method = 'get'
ai = ApiDataSourceInput(url, method)
ai.name = 'Customer Name Here'
r = a.call_data_source(pcn, ai)
cust_id = r.get_response_attribute('id') # Should only return 1 item.

# Get EDI log entries
url = 'https://connect.plex.com/edi/v1/logs'
method = 'get'
ai = ApiDataSourceInput(url, method)
ai.customerId = cust_id
ai.action = 'Receive'
ai.mailboxActive = True
ai.logDateBegin = log_start_date = yesterday.strftime('%Y-%m-%dT04:00:00Z')
# This will return a list of all received documents
r = a.call_data_source(pcn, ai)
# Filter for 830s and 862s. This isn't possible directly from the API call.
edi_documents = ['830', '862']
edi_messages = r.get_response_attribute('id', preserve_list=True, documentName=edi_documents)

# Get the actual EDI documents
method = 'get'
for edi_id in edi_messages:
    url = f'https://connect.plex.com/edi/v1/documents/{edi_id}'
    ai = ApiDataSourceInput(url, method)
    r = a.call_data_source(pcn, ai)
    edi_raw = r.get_response_attribute('rawDocument')
    # You'll need to decode this from base64 string and save it to a file
    edi_str = str(base64.b64decode(edi_raw).decode('utf-8'))
    with open(f'{edi_id}_edi_file.txt', 'w+', encoding='utf-8') as out_file:
        out_file.write(edi_str)
```

</details>

#### Example 5

Get one PCN's operation details from a SQL query and create the matching records in another PCN.  
There is no data source or upload for these items.

<details>
<summary>
Example 5
</summary>

Run this query in SQL Development Environment and save as a CSV file.

```SQL
SELECT

 o.Operation_Code
,o.Operation_Type
,o.Inventory_Type
,o.Defect_Log
,o.Material
,o.Rework
,o.Ship 'Allow Ship'
,o.Default_Operation 'Default'
,o.Shipping_Operation
,o.Uses_Tools
,o.Variable_BOM_Qty 'Variable BOM'
,o.Job_Quantity_Defective_Increase
,o.Final_Operation
,o.unit 'Inventory Unit'
,o.Denominator_Unit
,o.Fixed_Run_Time
,o.Delay_Before
,o.Delay_After
,o.Note

FROM part_v_operation o
ORDER BY o.operation_code
```

Use the saved file as a source for this script.

```python
import pmc_automation_tools as pa
import os
from selenium.webdriver.common.by import By

username = open(os.path.join('resources','username')).read()
password = open(os.path.join('resources','password')).read()
company_code = open(os.path.join('resources','company')).read()
pcn = '123456'
dest_pcn = '987654'
test = True
input_file = 'Operations.csv'
input_records = pa.read_updated(input_file)

batch_code_folder = pa.create_batch_folder(test=test)
update_file = os.path.join(batch_code_folder, 'Updates.csv')
error_file = os.path.join(batch_code_folder, 'Errors.csv')
updated = pa.read_updated(update_file)

ux = pa.UXDriver('chrome')
logger = pa.setup_logger('Operations', root_dir=batch_code_folder)
driver, url_comb, token = ux.login(username, password, company_code, pcn, test_db=test)
token = ux.pcn_switch(dest_pcn)
# Operations screen URL
MAIN_URL = f'{url_comb}/VisionPlex/Screen?__actionKey=7148&{token}&__features=novirtual'
driver.get(MAIN_URL)
ux.wait_for_element(By.NAME, 'OperationCode')

for row in input_records:
    if row in updated:
        continue
    try:
        ux.click_action_bar_item('Add')
        ux.wait_for_gears()
        # Each column name should match the screen element's label text.
        # Underscores in the column name are replaced with spaces.
        # Case sensitivity does not matter.
        for k, v in row.items():
            screen_elem = ux.find_element_by_label(k)
            screen_elem.sync(v)
        ux.click_button('Ok')
        ux.wait_for_banner()
        ux.wait_for_gears()
        pa.save_updated(update_file, row)
    except Exception as e:
        logger.error(row)
        logger.exception(e)
        pa.save_updated(error_file, row)
        driver.get(MAIN_URL)
        ux.wait_for_element(By.NAME, 'OperationCode')
```
</details>