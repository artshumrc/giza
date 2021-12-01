$(document).foundation()

$(document).ready(() => {

    saved_searches = JSON.parse($(searches).text())

    // COPY SEARCH LINK TO THE CLIPBOARD
    $('#copy_to_clipboard').on('click', e => navigator.clipboard.writeText($(e.currentTarget).data('id')))

    // UPDATE SAVED SEARCH
    $('.accordion-menu input').on('click', e => {
        key = true
        if ($(e.currentTarget).attr('type') == 'text') {
            keycode = (e.keyCode ? e.keyCode : e.which) && e.keyCode
            key = keycode != '13' ? false : true
        }

        if (key) {
            $('.accordion-menu input').attr('disabled', true)
            $.post('/search/all/update/', { 'id' : $('li.is-active[name]').attr('name'), 'param' : $(e.currentTarget).attr('id') })
            .done(response => {
                if (response.success) {
                    console.log(response)
                    id = $('li.is-active[name]').attr('name')
                    $('.accordion-menu input').attr('disabled', false)
                    $('#' + id + '_total').text(`${response['search']['result']['total']}/${response['search']['result']['overall']}`)
                    // UPDATE SEARCH STATISTICS
                }
            }).fail(response => {
            console.log(response)
            })
        }
    })

    // DELETE SAVED SEARCH
    $('.del_search').on('click', e => {
        $.post('/search/all/del/', { 'id' : $(e.currentTarget).data('id') })
        .done(response => {
            if (response.success) {
                $('#saved_searches').empty().html(response.html)      
                $('#saved_searches_total').text(`${response.total} Saved Search${response.total == 1 ? '' : 'es'}`)
            } else {
                console.log(response)
            }
        })
        .fail(response => {
        console.log(response)
        })
    })

    // RUN SAVED SEARCH
    $('.run_search').on('click', e => {
        console.log('ok')
        $.get('/search/lookup/', { 'token' : $(e.currentTarget).data('id') })
        .done(response => {
        //     console.log(response)
            $('body').empty().html(response)
        }).fail(response => {
            console.log(response)
        })
    })
})