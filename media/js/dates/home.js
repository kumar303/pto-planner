$(function() {
  $('#calendar').fullCalendar({
    editable: false,
    events: "/calendar/events/",
    firstDay: CALENDAR_FIRST_DAY,
    selectable: true,
    selectHelper: true,
    select: function(start, end, allDay) {
      url = '/notify/?start=' + start.getTime() + '&end=' + end.getTime();
      location.href = url;
      calendar.fullCalendar('unselect');
    }
  });

  $('<a href="#rightnow"></a>')
    .html($('#rightnow h2').text() + ' &darr;')
      .addClass('rightnow-anchor')
        .prependTo($('#content'));
});
