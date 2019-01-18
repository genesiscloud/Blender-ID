# Blender ID Authorisation Token Scopes

This document describes the OAuth token scopes used by Blender ID.

## API users / services

These scopes are assigned to tokens owned by API users. These are generally not
real flesh-and-blood users, but system accounts.

-   **badger**: Grants the owner of this token to assign and revoke roles. The
    set of allowed roles is determined by the roles of the owner (for example,
    the Blender Store system user has the `cloud_badger`, which allows assigning
    and revoking the `cloud_has_subscription` and `cloud_subscriber` roles).
-   **usercreate**: Grants the owner of this token the possibility to create
    new users, and to check for user existence. This is used by Blender Store.
-   **authenticate**: Grants the possibility to check an email/password combination
    for validity. This is used by Blender Store.
-   **userinfo**: Grants the caller to access user info of arbitrary users.
    This is used by Blender Cloud.

## User tokens

These scopes are assigned to tokens owned by regular users of Blender ID.

-   **email**: The default scope for any token given to a user upon login.
    Grants access to the basic user information, such as email address,
    full name, and nickname.
-   **badge**: Grants the caller access to badge info (as JSON and HTML) of
    the user who owns the token.
