## TODO

[ ] `api.datasource.call_data_source()` - Check for presence of 'json' key in `query._query_string` to avoid unintuitive initialization behavior with non-named input parameters such as lists. EX: when calling https://connect.plex.com/purchasing/v1/release-batch/cancel API which only takes a list of objects as input.

# 0.3.1 [2024-10-25]

## Changed

Changed `api.common.get_response_attribute()` to accept a list of values in the kwargs for filtering.

Changed `common.utils.read_updated()` to have an obj_type input param.  
Use this to define the returned object structure if there is no file or the file is empty.

Removed code from `api.ux.datasource.get_to_update()` that was redundant.

Changed `api.ux.datasource.type_reconcile()` boolean recognition to default to False for any value not "TRUE" case insensitive.

## Fixed

Fixed `common.utils.save_updated()` when object is empty.

Fixed `common.utils.read_updated()` encoding when opening a classic sql query download. Must use utf-8-sig in order to reference the first column properly.

Fixed `api.datasource.call_data_source()` responses not working for singular item get methods. I.E. Get_Log vs Get_Logs

Fixed `api.ux.datasource.get_to_update()` to actually function with a response object.

Added a step in `driver.ux.driver.sync_picker()` to collapse sequencial whitespace in text input when searching for options on a select type element (drop-downs).  
This should not be done for text input type pickers (magnifying glass) as they retain the sequencial whitespace in comparisons.

Fixed `api.common.get_response_attribute()` to check if kwarg is single value and compare exact match. List kwargs compare if the attribute is within the set.

Fixed `api.ux.datasource.type_reconcile()` fixed value recognition for booleans when the input is strings of 0 or 1.

## Added

Added support for ux data source template datetime type recognition.

Added param to `common.utils.plex_date_formatter()` to convert the supplied datetime to UTC.

Added output=input key replacement kwarg support to `api.ux.datasource.get_to_update()`. EX: ui.get_to_update(response, Champion_PUN='Champion') will use the "Champion_PUN" from the response object and set the ui object's "Champion" attribute to this value.

Added support for `api.common.get_response_attribute()` to return multiple attributes if supplying a tuple of attributes.

# 0.3.0 [2024-9-12]

## Changed

Changed how browser drivers were managed.  
Switched to the Selenium driver manager introduced in Selenium 4.6.

Removed code for handling the browser version checking and driver downloads.

## Fixed

Fixed README example 4 using incorrect syntax for combining two lists of EDI documents.

Fixed `api.datasource.call_data_source()` error when text response is empty string.

## Added

Added functionality to `common.utils.read_updated()` and `common.utils.save_updated()` to support csv files.

# 0.2.2 [2024-09-09]

## Fixed

Fixed `wait_for_element` method not actually using the new by, value syntax when searching for elements.

## Added

Added `wait_for_elements` method to return a list of PlexElements while waiting for them to be visible.

TODO - Add support for different expected conditions such as clickable and invisible.

# 0.2.1 [2024-09-05]

## Changed

Reworked the `driver.ux.driver.sync_picker()` method to be more coherant and work more consistently.

Updated README examples to show new style for `wait_for_element()` method.

## Fixed

Fixed missing error in `api.classic.datasource.call_data_source()` method.

# 0.2.0 [2024-09-04]

## Changed

Changed `wait_for_element` methods to support two positional arguments in addition to one tuple selector. More closely aligned with the behavior of Selenium's `find_element` method.

These are now equivalent:
* wait_for_element(By.NAME, 'ElementName')
* wait_for_element((By.NAME, 'ElementName'))

## Fixed

Fixed oversight in `driver.common.wait_for_element()` that changed `driver` argument to be positional from optional keyword argument.

# 0.1.5 [2024-08-30]

## Fixed

Fixed bug in `driver.ux.driver.click_button()`

* Type hint caused import error due to incorrect syntax

## Added

Added `driver.generic.GenericDriver` which can be used for basic website automation.

* `launch()` method only takes url parameter for launching a browser.

## Changed

Changed attribute assignment in `driver.common.PlexElement`

* Now uses `getattr()` method to prevent errors when no attributes exist

# 0.1.4 [2024-08-29]

## Fixed

Fixed bug in `driver.ux.driver.click_action_bar_item()`

## Added

Added functionality to `driver.ux.driver.sync_picker()`

* New arg, column_delimiter.
  * Supports splitting the popup results to find exact matching.
  * By default, if a popup shows multiple columns, the text is split by the tab character (\t).
  * Some popup windows will show results with combined text in a single column joined with a delimiter.

## Changed

Updated some function docstrings.

# 0.1.3 [2024-08-28]

## Fixed

Fixes for `driver.ux.driver.sync_picker()` 

* When the picker search has multiple columns, the text of the row is combined.
  * Will now split the text by tab and select fully matching values from any column in the table.
* Will now properly raise an exception when no matching row is found.

## Added

Added functionality to `driver.ux.driver.wait_for_banner()`

* Added timeout override arg
* Added arg for ignoring exception similar to the `wait_for_element()` function

# 0.1.2 [2024-08-27]

## Fixed

Fixed issue with `driver.common.login()` not inputting password with Rockwell login screen change.