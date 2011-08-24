var AutocompleteNotify = (function() {
  function split( val ) {
    return val.split(/;\s*/);
  }
  function extractLast( term ) {
    return split( term ).pop();
  }

  return {
     init: function(input_id, remote_url) {
       $('#' + input_id)
         // don't navigate away from the field on tab when selecting an item
         .bind( "keydown", function( event ) {
           if ( event.keyCode === $.ui.keyCode.TAB &&
                $( this ).data( "autocomplete" ).menu.active ) {
             event.preventDefault();
           }
         })
           .autocomplete({
              source: function( request, response ) {
                $.getJSON(remote_url, {
                   term: extractLast( request.term )
                }, response );
              },
             search: function() {
               // custom minLength
               var term = extractLast( this.value );
               if ( term.length < 2 ) {
                 return false;
               }
             },
             focus: function() {
               // prevent value inserted on focus
               return false;
             },
             select: function( event, ui ) {
               var terms = split( this.value );
               // remove the current input
               terms.pop();
               // add the selected item
               terms.push( ui.item.value );
               // add placeholder to get the comma-and-space at the end
               terms.push( "" );
               this.value = terms.join( "; " );
               return false;
             }
           });
     }
  }
})();


var StartEndDatepickers = (function() {
  var start
    , end
    , _dateformat
    , start_date
    , end_date
    , days;

  function show_days(days) {
    var container = $('#show-days');
    if (!container.size()) {
      container = $('<span>')
        .attr('id', 'show-days')
          .addClass('date-hint');
      container.insertAfter($('#id_end'));
    }
    container.text(days + (days == 1 ? ' day' : ' days'));
  }

  function show_today_tip() {
    var container = $('#today-hint');
    if (!container.size()) {
      container = $('<a>', {text: 'today?'})
        .attr('id', 'today-hint')
          .attr('href', '#')
            .attr('title', 'Click for 1 day starting today')
              .addClass('date-hint');
      container.insertAfter($('#id_start'));
    }
    container.click(function() {
      var date = new Date();
      start.val($.datepicker.formatDate(_dateformat, date));
      start.trigger('change');
      $(this).remove();
      return false;
    });
  }

  function daysDiff(d1, d2) {
    return  Math.floor((d2.getTime() - d1.getTime()) / 86400000);
  }

  function _init() {
    // onchange for start
    start.change(function() {
      $('#today-hint').remove();
      start_date = $.datepicker.parseDate(_dateformat, start.val());
      if (end.val()) {
        end_date = $.datepicker.parseDate(_dateformat, end.val());
        days = daysDiff(start_date, end_date);
        if (days < 0) {
          end.val($(this).val());
          show_days(1);
        } else {
          show_days(days + 1);
        }
      } else {
        end.val($(this).val());
        show_days(1);
      }
    });

    // onchange for end
    end.change(function() {
      $('#today-hint').remove();
      end_date = $.datepicker.parseDate(_dateformat, end.val());
      if (start.val()) {
        start_date = $.datepicker.parseDate(_dateformat, start.val());
        days = daysDiff(start_date, end_date);
        if (days < 0) {
          start.val($(this).val());
          show_days(1);
        } else {
          show_days(days + 1);
        }
      }
    });

    // first load
    if (start.val() && end.val()) {
      start_date = $.datepicker.parseDate(_dateformat, start.val());
      end_date = $.datepicker.parseDate(_dateformat, end.val());
      days = daysDiff(start_date, end_date);
      if (days < 0) {
        end.val('');
      } else {
        show_days(days + 1);
      }
    } else if (!start.val() && !end.val()) {
      show_today_tip();
    }
  }

  return {
     init: function (start_id, end_id, dateformat) {
       start = $('#' + start_id);
       end = $('#' + end_id);
       _dateformat = dateformat;
       _init();
     }
  }
})();

function moveManagersNotified() {
  var tr_extra = $('#id_notify').parents('tr');
  var new_tr = $('<tr>');
  $('#managers-notified td').each(function(i, td) {
    $(td).detach().appendTo(new_tr);
  });
  new_tr.insertBefore(tr_extra);
  $('label', tr_extra).text("Additional to notify");
}

var dateFormat = 'DD, MM d, yy';
$(function() {
  $('input.date').datepicker({
    dateFormat: dateFormat
  });

  if ($('#id_start').size() && $('#id_end').size()) {
    StartEndDatepickers.init('id_start', 'id_end', dateFormat);
  }

  AutocompleteNotify.init('id_notify', '/users/ldap-search/');
  moveManagersNotified();
});
