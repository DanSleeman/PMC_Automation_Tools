# Plex Automation Tools

This library provides functionality to log into Plex Manufacturing Cloud and automate tasks under a user's account.

Supports classic and UX.

This is basically a wrapper around Selenium with specific functions designed around how the PMC screens behave.

## Requirements

* Selenium
* pywin32

Optional:
* Pillow

Used for saving images of screen elements.

## Usage

Automate data entry into screens which do not support or have an upload, datasource, or API to make the updates.

```python

from plex_login_ux import PlexAutomate

# UX screens
pa = PlexAutomate('UX')
driver, url_comb, token = pa.login(username,password,company_code,pcn,db)
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

### PlexAutomate Functions
`wait_for_element`

Waits for until an element condition is met.

Parameters
* Selector - Selenium tuple selector
* Driver - WebDriver or WebElement as starting point for locating the element
* Timeout - How long to wait until the condition is met
* Type - What type of condition
    * Visible (default)
    * Invisible
    * Clickable

Returns PlexElement object
```python 
checklist_box = p.wait_for_element((By.NAME,'ChecklistKey'))
```
`wait_for_gears`

Waits for the visibiility and then invisibility of the "gears" gif that shows when pages load.

`wait_for_banner`

Waits for the banner to appear after a record is updated or if there is an error.

`login`

Log in to Plex with the provided credentials.

`token_get`

Return the current session token from the URL.

This is needed in order to maintain the proper PCN when navigating between them.

Otherwise, the screens may revert back to your home PCN.

`pcn_switch` alias `switch_pcn`

Switch to the PCN provided

Paramters
* PCN
    * PCN number for the destination PCN

`ux_click_button`

`ux_click_action_bar_item`

`edi_upload`

`create_batch_folder`

`setup_logger`

### PlexElement Functions
`sync_picker`

`sync_textbox`

`sync_checkbox`

`save_element_image`
