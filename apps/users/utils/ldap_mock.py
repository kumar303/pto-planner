import ldap
from django.conf import settings


class MockLDAP:  # pragma: no cover
    def __init__(self, search_result, credentials=None):
        self.search_result = search_result
        self.credentials = credentials

    def search_s(self, search, scope, filter=None, attrs=None):
        #print "INPUT", (search, filter)
        o = self._search_s(search, scope, filter=filter, attrs=attrs)
        #print "OUTPUT", o
        return o

    def _search_s(self, search, scope, filter=None, attrs=None):
        if search in self.search_result:
            return self.search_result[search]

        if filter:
            try:
                return self.search_result[filter]
            except KeyError:
                pass
        return []

    def simple_bind_s(self, dn, password):
        #print "Input", (dn, password)
        try:
            o = self._simple_bind_s(dn, password)
            #print "Output", None, ":)"
        except:
            #print "Output EXCEPTION  :("
            raise

    def _simple_bind_s(self, dn, password):
        if self.credentials is None:
            # password check passed
            return
        if dn == getattr(settings, 'AUTH_LDAP_BIND_DN', None):
            # sure, pretend we can connect successfully
            return
        try:
            if self.credentials[dn] != password:
                raise ldap.INVALID_CREDENTIALS
        except KeyError:
            raise ldap.UNWILLING_TO_PERFORM

    def void(self, *args, **kwargs):
        pass

    set_option = unbind_s = start_tls_s = void
