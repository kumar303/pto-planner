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
                        var hrs = format(ngettext('You will have {0} hour of PTO available',
                                                  'You will have {0} hours of PTO available',
                                                  data.hours_available_on_start),
                                         [data.hours_available_on_start]),
                            days = format(ngettext('{0} day', '{0} days',
                                                   data.days_available_on_start),
                                         [data.days_available_on_start]);
                        $('#result').text(hrs + ' (' + days + ')');
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
