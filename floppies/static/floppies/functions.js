function reorderSelectedOptions(selectId) {
    var select = document.getElementById(selectId);

    function reorder() {
        var selectedOptions = [];
        var unselectedOptions = [];

        // Separate selected and unselected options
        for (var i = 0; i < select.options.length; i++) {
            if (select.options[i].selected) {
                selectedOptions.push(select.options[i]);
            } else {
                unselectedOptions.push(select.options[i]);
            }
        }

        // Clear the select box
        select.innerHTML = '';
        
        // Sort the options
        selectedOptions.sort(function(a,b) {
            if (a.text.toUpperCase() > b.text.toUpperCase()) return 1;
            else if (a.text.toUpperCase() < b.text.toUpperCase()) return -1;
            else return 0;
        });
        
        unselectedOptions.sort(function(a,b) {
            if (a.text.toUpperCase() > b.text.toUpperCase()) return 1;
            else if (a.text.toUpperCase() < b.text.toUpperCase()) return -1;
            else return 0;
        });
        
        
        

        // Add the selected options to the top
        selectedOptions.forEach(function(option) {
            select.appendChild(option);
        });

        // Add the unselected options below
        unselectedOptions.forEach(function(option) {
            select.appendChild(option);
        });
    }

    // Run the reorder function on page load
    reorder();

    // Also run the reorder function whenever the selection changes
    select.addEventListener('change', reorder);
}


document.addEventListener('DOMContentLoaded', function() {
    reorderSelectedOptions('id_subjects');
    reorderSelectedOptions('id_creators');
    reorderSelectedOptions('id_contributors');
    reorderSelectedOptions('id_collections');
    reorderSelectedOptions('id_photos');
});
