## TODO

[ ] - `driver.common.wait_for_elements()` - Add support for different expected conditions such as clickable and invisible.

[ ] - `driver.classic.driver.sync_picker()` - Add support for `ClassicDriver` object

# 0.6.4 [2025-5-5]

## Fixed

Fixed issue with not being able to manually input datasource credentials when a file exists, but the key is not present.

Fix to `plex_date_formatter()` to support date objects as `arg[0]` input without throwing exceptions for timezone conversions.

Fix to `UXPlexElement.sync_textbox()` when using `int` type inputs. Converts these to strings to avoid any issues with string functions.

## Added

Added function to find an element using the element's text label. `find_element_by_label()`

Added support to `UXPlexElement` for universal `sync()` method when using above function to locate the element.

Added function aliases for `wait_for_gears()` and `wait_for_banner()` to UXDriver class.

Added support for multi-picker elements with `sync()` and `sync_picker()` methods.

## Changed

Added support for `sync_checkbox()` input to accept multiple options for truthiness. True, 1, "1", "True", "TRUE" should all evaluate to True.

Changed `setup_logger()` function to always add a handler regardless of any parent handlers. Can be overwritten by passing propagate=True.

Added error safe handling for threaded datasource calls

# 0.6.3 [2025-1-28]

## Fixed

Fixed incorrectly formatted `__repl__` method in `api.classic.datasource.py`

# 0.6.2 [2025-1-23]

## Changed

Changed GenericDriver to rely less on Plex specific attributes for functionality.
* No longer supers the init function as many of the attributes are not used and cause issues when missing.
* Defaults various attributes that are baked into the driver setup functions

## Added

Added time_taken attribute to `api.datasource.call_datasource()` response

# 0.6.1 [2024-12-13]

## Fixed

Fixed `highlight_row` method for instances where the cell content to match is a hyperlink.

# 0.6.0 [2024-12-12]

## Added

Added method for highlighting a UX row to allow for relevant action bar items to be clicked.

# 0.5.1 [2024-12-3]

## Added

Added tz input to `common.utils.plex_date_formatter()` to allow for converting times based in other locations to UTC. Not usually needed for dealing with Plex SQL, but could be helpful.

Added `driver.common.insert_text()` method to `PlexElement` class. Allows to insert text into a field at a specific position without removing anything.

# 0.5.0 [2024-11-4]

## Added

Added dependancy for openpyxl to handle reading in .xlsx files.

Added support to `common.utils.read_updated()` for reading an Excel file for the source data.

Added detailed field error capturing for `UpdateError` class when raised in `driver.ux.driver._banner_handler()` errors.

Added various `__repr__` and `__str__` methods for datasource objects.

Added `plex_date_formatter()` to `__init__.py`.

`common.utils.save_updated()` Added input to overwrite the file contents regardless of the input object.

Added support for xlsm files in `read_updated()`.

Added support for specifying sheet name when reading Excel files in `read_updated()`.

## Fixed

Fixed `api.ux.datasource.type_reconcile()` when dealing with datetime values.

Fixed `driver.common.wait_for_element()` when using link text selectors and having repeated whitespace and/or non-printing whitespace characters in the search value.

Fixed `common.utils.save_updated()` for instances when a single length list was provided as the input.

Fixed `common.utils.plex_date_formatter()` to hopefully work when run in any country. (Should always use local time in New York Eastern coded as UTC)

Fixed `common.utils.read_updated()` for instances where the file exists, but is empty. Should return the default empty object now.

Fixed `UXDatetime` class to support the different date formats that could come from Plex SQL reports.

## Changed

Changed `common.utils.save_updated()` to append single dictionary values to the existing file. If providing a list of dictionaries, the previous full file re-write method will be called instead.

Rewrote `common.utils.setup_logger()` to be less complicated and include memoryhandler/streamhandler support.

Added support to return the full item in `DataSourceResponse.get_response_attribute()` using 'ALL' as the input variable.

Changed `DataSourceResponse.get_response_attribute()` to return `None` if there are no matches.

# 0.4.0 [2024-11-1]

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

Fixed `api.ux.datasource.type_reconcile()` value recognition for booleans when the input is strings of 0 or 1.

Fixed `api.datasource._update_input_parameters()` to recognize 'json' attribute and assign it to _query_string directly.

Fixed `common.utils.read_updated()` to not cause clashing with error records and update records when called for separate objects.

Fixed `ux.driver.sync_picker()` when using clear=True. Was expecting an element or popup when there wouldn't be any.

## Added

Added support for ux data source template datetime type recognition.

Added param to `common.utils.plex_date_formatter()` to convert the supplied datetime to UTC.

Added output=input key replacement kwarg support to `api.ux.datasource.get_to_update()`. EX: ui.get_to_update(response, Champion_PUN='Champion') will use the "Champion_PUN" from the response object and set the ui object's "Champion" attribute to this value.

Added support for `api.common.get_response_attribute()` to return multiple attributes if supplying a tuple of attributes.

Added `__str__` method for `DataSourceResponse` class to print the transformed data attribute.

Added `batch_prefix` param to `common.utils.create_batch_folder()` if a static batch is not desired, but still want different batches for different operations within the same directory.

Added `common.utils.chunk_list()` function. Useful for API calls where a list of IDs would cause a URI to become too long.

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