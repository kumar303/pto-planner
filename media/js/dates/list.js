function L() {
   if (window.console && window.console.log)
     console.log.apply(console, arguments);
}

var Dates = (function() {
  var _prefixes
    , _dateformat
    , _previous_values = {};

  function getAdjacentInput(input) {
    if (input.attr('id').search(/_from/) > -1) {
      return $('#' + input.attr('id').replace('_from', '_to'));
    } else {
      return $('#' + input.attr('id').replace('_to', '_from'));
    }
  }

  function daysDiff(d1, d2) {
    return  Math.floor((d2.getTime() - d1.getTime()) / 86400000);
  }

  return {
     change: function (input) {
       var is_leftmost = input.attr('id').search('_from') > -1;
       var adjacent = getAdjacentInput(input);
       var diff;
       if (input.val() && adjacent.val()) {
         if (is_leftmost) {
           diff = daysDiff(input.datepicker('getDate'), adjacent.datepicker('getDate'));
         } else {
           diff = daysDiff(adjacent.datepicker('getDate'), input.datepicker('getDate'));
         }
         if (diff < 0) {
           adjacent.val(input.val());
         }
         //
       }
       // lastly
       _previous_values[input.attr('id')] = input.val();
     },
     init: function (prefixes, dateformat) {
       _dateformat = dateformat;

       var input, minDate, maxDate;
       $.each(prefixes, function(i, prefix) {
         $.each(['_from', '_to'], function (i, suffix) {
           if (prefix == 'date') {
             if (suffix == '_from') {
               minDate = DATE_MIN;
               maxDate = DATE_MAX;
             } else {
               minDate = DATE_MIN;
               //maxDate = THEORETICAL_DATE_MAX;
               maxDate = DATE_MAX;
             }
           } else {
             if (suffix == '_from') {
               minDate = FILED_MIN;
             } else {
               maxDate = FILED_MAX;
             }
           }
           input = $('#id_' + prefix + suffix)
             .datepicker({
                dateFormat: _dateformat,
                minDate: minDate,
                maxDate: maxDate,
                showAnim: 'fadeIn',
                numberOfMonths: 3,
                showButtonPanel: true,
                beforeShow: function () {
                  //
                },
                onClose: function () {
                  //
                }
               })
               .change(function() {
                 Dates.change($(this));
               });
           _previous_values[input.attr('id')] = '';
         });
       });

       var _triggered;
       $.each(prefixes, function(i, prefix) {
         _triggered = false;
         $.each(['_from', '_to'], function (i, suffix) {
           input = $('#id_' + prefix + suffix);
           if (input.val() && !_triggered) {
             input.trigger('change');
             _triggered = true;
             _previous_values[input.attr('id')] = input.val();
           }
         });
       });

     }
  }
})();

var dateFormat = 'd MM yy';

var Data = (function() {
  return {
     href: function() {
       return DATA_URL + location.search;
     }
  }
})(DATA_URL);

$(function() {
  Dates.init(['date', 'date_filed'], dateFormat);


  $('#pto_table').dataTable({
    bProcessing: true,
    //bServerSide: true,  // more scalable but more work (for later)
    sAjaxSource: Data.href(),
    //aaSorting: [[ 2, 'asc' ],[ 1, 'asc' ],[ 3, 'desc' ]],
    aaSorting: [[ 5, 'asc' ],],
    //aoColumnDefs: [{'bSearchable' : false, 'bVisible' : false, 'aTargets' : [ 0 ] }],
    //sPaginationType: 'full_numbers',
    headers: {
       5: {sorter: false}
    }
  });
});
