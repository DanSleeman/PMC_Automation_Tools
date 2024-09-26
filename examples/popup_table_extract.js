/*
This is for UX upload popup validation windows.
There is no export option on the popup, so it can be hard to review the errors.
Update the columnIndicies array to be the column indexes for the popup columns that you want to extract.
Copy this file content into the browser dev tools and run it.
Paste the copied variable into a json file. e.g. popup_errors.json
Run the popup_table_extract_format.py script
*/


// Assuming tbl is defined as:
var tbl = $(jQuery('div.plex-grid-wrapper > table')[1]);
// This selector should get the popup window data.
// The base selector will return two tables since it sees the normal screen grid as well.
// There are no good IDs to use for selecting the popup

// Specify the indices of the columns you want to extract
var columnIndices = [1, 2, 11, 17, 30, 70];

//Pass true if you want to extract the whole popup into a json object.
var allColumns = false; 

var rowDataList = [];

var headers = [];
tbl.find('thead tr th').each(function(index) {
    headers[index] = $(this).text().trim();
});

if (allColumns){
    columnIndices = Array.from({length: headers.length}, (_, index) => index);
}

tbl.find('tbody tr').each(function() {
    var rowData = {}; 
    var cells = $(this).find('td'); 

    // Loop through the specified column indices and store the values in the object
    columnIndices.forEach(function(index) {
        if (cells.eq(index).length) {
            // Use the header text as the key and the cell content as the value
            // Header index is one ahead of row index for some reason.
            var headerText = headers[index+1] || ('column' + (index+1)); // Fallback to 'columnX' if no header. 
            rowData[headerText] = cells.eq(index).text().trim();
        }
    });

    // Add the object to the list if it has any data
    if (Object.keys(rowData).length > 0) {
        rowDataList.push(rowData);
    }
});

console.log('Extracted row data with headers as keys:', rowDataList);

copy(rowDataList);