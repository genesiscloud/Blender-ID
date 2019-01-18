# Welcome to the Blender ID Documentation

Here is a growing collection of docs and development notes for the 
[Blender ID](https://www.blender.org/id/) project.


## Project layout and modules

    bid_api/                    # Django app for APIs that are neither OAuth2 nor Blender ID add-on support
    bid_main/                   # Main Django app, taking care of the web interface and OAuth2 authentication.
    bid_addon_support/          # Django app for the Blender ID add-on API (see below).
    blenderid/                  # Django project, includes all the settings and top-level URL config.
        __settings.py           # Example development settings
    docs/                       # Project documentation
    websrc/                     # Asset sources (CSS, JS, etc.).
    __deploy.sh__               # Run this to deploy


## OAuth Applications

You can use Blender ID as OAuth provider for your application. In order to do so:

* Request (via mail to production at blender.org) Blender ID Application credentials by providing:
    * The name of the Application
    * The URL of the Application
    * The return URL
    * And image to be used in the OAuth screen
* Define the scopes of the Application and use the API endpoints accordingly

The main benefits of using Blender ID for your Application are:

* Use a service trusted within the Blender Community
* Access to Blender ID badges associated to a user (Blender Development Fund Membership, Blender Cloud subscriptions,
etc.)

## API endpoints

* `https://www.blender.org/id/oauth/authorize`: Authorization endpoint
* `https://www.blender.org/id/oauth/token`: OAuth token validation endpoint
* `https://www.blender.org/id/api/me`: Retrieve info about the current user. Returns a JSON doc with the following keys:
    * `id`: User ID (this will not change - use to create a reference to the user in your Application)
    * `full_name`: User full name
    * `email`: User email address
    * `nickname`: User nickname
    * `roles`: Dictionary with active public roles associated with the user
        * TODO: specify which roles are currently available
* `https://www.blender.org/id/api/user/<user_id>`: Retrieve info about any user (requires userinfo scope)
* `https://www.blender.org/id/api/badges/<user_id>`: Retrieve badges for the user (requires matchin token). Returns a 
JSON doc with the following keys:
    * `label`: Human readable name
    * `link` (optional): URL to a website relevant to the badge
    * `description` (optional): Short description of the badge
    * `image` (optional): URL to the badge image
    * `image_width` (optional): Image width
    * `image_height` (optional): Image height

## TODO

The following areas could be documented next:

* Extend development installation
* Extend deployment playbook
* Overall architecture
