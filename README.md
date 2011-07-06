PTO Planner
===========

No more confusing math!  This is a small web app (with a dumb name) to help
you figure out how much PTO you'll have available on a given future date.

Install
=======

To install, run:

    pip install -r requirements/compiled.txt -r requirements/dev.txt
    cp settings_local.py-dist settings_local.py
    mysql -u root -e "create database pto_planner"

Edit settings_local.py with the database credentials:

    'NAME': 'pto_planner',
    'USER': 'root',
    'PASSWORD': '',
    ...

Then start the web server:

    python manage.py runserver

Begin Slacking Off
==================

Open http://localhost:8000/ and start planning your next vacation.

Playdoh
=======

This site is built with Mozilla's Playdoh, a web application template
based on [Django][django].

Full [documentation][docs] for Playdoh is available.

[django]: http://www.djangoproject.com/
[gh-playdoh]: https://github.com/mozilla/playdoh
[docs]: http://playdoh.rtfd.org/


License
-------
This software is licensed under the [New BSD License][BSD]. For more
information, read the file ``LICENSE``.

[BSD]: http://creativecommons.org/licenses/BSD/

