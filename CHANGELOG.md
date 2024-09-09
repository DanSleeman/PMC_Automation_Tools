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