var delay = 0.1,
    keep_going = true,
    circles = [3,4,5,6,7],
    radiuses = [20,40,60,80]
  ;

function shuffle(o) { //v1.0
  for (var j, x, i = o.length; i;
       j = parseInt(Math.random() * i), x = o[--i], o[i] = o[j], o[j] = x);
  return o;
}

function fire() {
  if (!keep_going) return;
  createFirework(radiuses[0],186,circles[0],3,null,null,null,null,false,false);

  setTimeout(function() {
    fire();
    delay += 0.1;
  }, 2000 + (1000 * delay));
  circles = shuffle(circles);
  radiuses = shuffle(radiuses);
}

$(function() {
  if ($('#fireworks-template').size()) {
    soundManager.onready(function() {
      fire();
      var f = $('<form action="#" method="post">')
        .css('margin-top','150px')
          .css('float','right')
            .appendTo($('#page section'));
      f.append($('<input type="checkbox" name="toggle">',
                 {'id': "toggle-fireworks"})
               .change(function() {
                 var on_https = 'https:' == document.location.protocol
                 $.cookie('no_fw', '1', {expires:30, path:'/', secure:on_https});
                 $('#page section form').remove();
                 keep_going = false;
               }));
      f.append($('<label>',
                 {'for':'toggle-fireworks', text:" I hate fireworks"})
               .css('font-size', '10px'));

    });
  }
});
