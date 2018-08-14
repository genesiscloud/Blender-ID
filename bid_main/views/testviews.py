"""Views for testing certain functionality."""


def test_mail_email_changed(request):
    """View for designing the email without having to send it all the time."""
    from django.http import HttpResponse
    from ..email import construct_email_changed_mail

    email_body_html, *_ = construct_email_changed_mail(request.user, 'old@email.nl')

    return HttpResponse(email_body_html)


def test_mail_verify_address(request):
    """View for designing the email without having to send it all the time."""
    from django.http import HttpResponse
    from ..email import construct_verify_address

    email_body_html, *_ = construct_verify_address(request.user, request.scheme)
    return HttpResponse(email_body_html)


def test_error(request, code):
    from django.core import exceptions
    from django.http import response, Http404

    codes = {
        403: exceptions.PermissionDenied,
        404: Http404,
        500: exceptions.ImproperlyConfigured,
    }
    try:
        exc = codes[int(code)]
    except KeyError:
        return response.HttpResponse(f'error test for code {code}', status=int(code))
    else:
        raise exc(f'exception test for code {code}')
