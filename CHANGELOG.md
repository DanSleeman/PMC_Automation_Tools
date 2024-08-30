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