function L() {
   if (window.console && window.console.log)
     console.log.apply(console, arguments);
}

// XXX TODO: fix these ugly names
function __sum_hours() {
  var counter = $('#date_discriminator_hours');
  counter.fadeOut(200, function() {
    var total = 0;
    $('input.hours:checked').each(function() {
      total += parseInt($(this).val(), 10);
    });
    counter.text('' + total);
    counter.fadeIn(200);
  });
}

$(function() {
  $('input.hours').change(function() {
    __sum_hours();
  });
  if ($('input.hours').size() >= 1) {
    __sum_hours();
  }
});
