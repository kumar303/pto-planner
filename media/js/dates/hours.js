var Hours = (function() {
  return {
     sum: function() {
       var counter = $('#date_discriminator_hours');
       counter.fadeOut(200, function() {
         var total = 0, hours;
         $('input.hours:checked').each(function() {
           hours = parseInt($(this).val(), 10);
           if (hours == -1) {
             // make sure only one is filled in
             if ($('input.hours[value="-1"]:checked').size() > 1) {
               this.checked = false;
               alert("You can only have 1 birthday buster!");
             }
           } else if (hours > 0) {
             total += hours;
           }
         });
         counter.text('' + total);
         counter.fadeIn(200);
       });
     }
  }
})();

$(function() {
  $('input.hours').change(function() {
    Hours.sum();
  });
  if ($('input.hours').size() >= 1) {
    Hours.sum();
  }
});
