
/* Returns a more-or-less reasonable message given an error response object. */
function xhrErrorResponseMessage(err) {
	if (err.status == 0)
		return 'Unable to connect to the server, check your internet connection and try again.';

    if (typeof err.responseJSON == 'undefined')
        return err.statusText;

    if (typeof err.responseJSON._error != 'undefined' && typeof err.responseJSON._error.message != 'undefined')
        return err.responseJSON._error.message;

    if (typeof err.responseJSON._message != 'undefined')
        return err.responseJSON._message

    return err.statusText;
}
