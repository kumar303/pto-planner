from django.conf import settings

def get_managers(user):
    if not getattr(settings, 'AUTH_LDAP_USER_SEARCH', None):
        return None
    return

#    print settings.AUTH_LDAP_USER_SEARCH
#    print dir(settings.AUTH_LDAP_USER_SEARCH)
#    print settings.AUTH_LDAP_USER_SEARCH.search(
    search = settings.AUTH_LDAP_USER_SEARCH
    from django_auth_ldap.backend import LDAPBackend
    #print dir(LDAPBackend)
    backend = LDAPBackend()

    #u = backend.populate_user(user.username)
    #print repr(u)
    #backend.get_user(user.pk)

    #print dir(backend)
    #print dir(user)
    #print user.ldap_user

    print dir(backend)
    print settings.AUTH_LDAP_BIND_PASSWORD
    connection = backend.ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
    for opt, value in getattr(settings, 'AUTH_LDAP_CONNECTION_OPTIONS', {}).iteritems():
        connection.set_option(opt, value)

    if settings.AUTH_LDAP_START_TLS:
        #logger.debug("Initiating TLS")
        connection.start_tls_s()

    results = search.execute(connection, {'user': user.email})
