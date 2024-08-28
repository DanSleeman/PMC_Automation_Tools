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