# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
# 
# The Original Code is Mozilla Sheriff Duty.
# 
# The Initial Developer of the Original Code is Mozilla Corporation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
# 
# Contributor(s):
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

from django.template import loader
from django.template.response import SimpleTemplateResponse

import jingo


def jinja_for_django(template_name, context=None, **kw):
    """
    If you want to use some built in logic (or a contrib app) but need to
    override the templates to work with Jinja, replace the object's
    render_to_response function with this one. That will render a Jinja
    template through Django's functions. An example can be found in the users
    app.
    """
    if context is None:
        context = {}
    context_instance = kw.pop('context_instance')
    request = context_instance['request']
    for d in context_instance.dicts:
        context.update(d)
    return jingo.render(request, template_name, context, **kw)


## We monkeypatch SimpleTemplateResponse.rendered_content to use our jinja
## rendering pipeline (most of the time). The exception is the admin app, where
## we render their Django templates and pipe the result through jinja to render
## our page skeleton.
#def rendered_content(self):
#    template = self.template_name
#    context_instance = self.resolve_context(self.context_data)
#    request = context_instance['request']
#
#    # Gross, let's figure out if we're in the admin.
#    if self._current_app == 'admin':
#        source = loader.render_to_string(template, context_instance)
#        template = jingo.env.from_string(source)
#        # This interferes with our media() helper.
#        if 'media' in self.context_data:
#            del self.context_data['media']
#
#    return jingo.render_to_string(request, template, self.context_data)
#
#SimpleTemplateResponse.rendered_content = property(rendered_content)
#
