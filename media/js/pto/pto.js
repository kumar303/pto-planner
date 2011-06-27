(function() {
"use strict";

$(function() {
    if ($('#pto_planner').length) {
        initDatepickers();
    }
});

function initDatepickers() {
    $('.datepicker').datepicker({
        dateFormat: 'yy-mm-dd', // note yy is YYYY (i.e. 2011)
        onSelect: function(dateText) {
            var $form = $('#planner');
            $.ajax({type: 'GET',
                    url: $form.attr('data-url'),
                    data: $form.serialize(),
                    cache: false,
                    success: function(data) {
                        $('#result').text(format(ngettext('You will have {0} day of PTO available',
                                                          'You will have {0} days of PTO available',
                                                          data.days_available_on_start),
                                                 [data.days_available_on_start]));
                    },
                    error: function(XMLHttpRequest, textStatus, errorThrown) {
                        if (typeof console !== 'undefined') {
                            console.log('Ajax error: ' + textStatus + ' ' + errorThrown);
                        }
                    },
                    dataType: 'json'});
        }
    });
}

})();
