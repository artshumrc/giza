$(document).foundation()

$(document).ready(() => {

    // ADVANCED SEARCH: SHOW/HIDE SECTIONS FOR SEARCHING IN CATEGORIES
    $('fieldset#category-radio-selector input').click(e => showHideMenu(e))

    // This function shows/hides parts of the advanced search categories
    showHideMenu = e => {
        if (e != undefined) {
        // RETAIN REFERENCE OF CURRENT CATEGORY
            selected_option = $('input.advanced_search_field:checked').val()
        
            $('#advanced-search-form').trigger("reset") // RESET THE SEARCH FORM WHEN CHANGING SEARCH OPTION
            $('.category-section').hide()               // HIDE THE SECTIONS
        
            // DETERMINE TARGET SECTION
            target = e.type == "click" ? $(e.currentTarget).attr('data-for-id') : e
        
            // SHOW RELEVANT ITEMS
            $('#'+selected_option).prop('checked', true)
            $('#'+target).show()                        // SHOW RELEVANT SECTION ONLY
        }
    }

    addHidden = elem => {
        hidden = $('<input>').attr('type', 'hidden').addClass('hidden_field').attr('name', elem.attr('name')).val(elem.val())

        if (elem.parent().find(`.hidden_field[name=${elem.attr('name')}]`).length) {
            elem.parent().find(`.hidden_field[name=${elem.attr('name')}]`).remove()
        }

        elem.parent().append(hidden)
    }


    // SHOW DEFAULT ADVANCED SEARCH OPTION
    selected_option = $('input.advanced_search_field:checked').attr('data-for-id')
    if (!$($('#'+selected_option)).is(':visible')) showHideMenu($('#'+selected_option).attr('id'))
    addHidden($('#'+selected_option))
})