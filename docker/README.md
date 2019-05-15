# Blender ID deployment

Deployment is done via Docker, and uses two images. The `blenderinstitute/blender-id-base`
image contains all the dependencies, including the virtual environment. The
`blenderinstitute/blender-id` image builds up from this, and adds the project sources.

There are two ways of deployment, 'quick' and 'full'. Either approach will use the current
`origin/production` branch to create the docker images.

## Full Deployment

Use this method when you've never built the docker images, or when you have a reason to
rebuild the base image (security updates, dependency changes).

## Quick Deployment

Use this method to quickly deploy a new version of just the project files. If you don't know
if the dependencies changed, just use the full build.

## Deployment Steps

Run these scripts from the `docker` directory.

For a **quick** deployment:

- `./deploy.sh sintel.blender.org`

For a **full** deployment:

- `./prep_docker_img.sh`
- `./build_docker_img.sh full`
- `./2server.sh sintel.blender.org`


## TLS Certificates

TLS certificates for HTTPS traffic are managed via the Træfik docker image.


## First install

The `MYSQL_ROOT_PASSWORD` environment variable (can be stored in a `.env` file) determines the MySQL
root password. Note that this is only used when there is no root user yet, so after the mysql
container has sucesfully started we recommend setting it to something humourous but otherwise
unusable for any attacker. Do note it down somewhere secure, though.

To create a new Blender ID database, run this as the MySQL root user:

    CREATE DATABASE blender_id CHARACTER SET=utf8;
    CREATE USER 'blender_id'@'%' IDENTIFIED BY 'jemoeder';
    GRANT ALL ON blender_id.* to 'blender_id'@'%';
    FLUSH PRIVILEGES;
    SHOW GRANTS FOR 'blender_id'@'%';

and change `jemoeder` to a random password that you also store in the Blender ID settings.
Alternatively, change the password using:

    SET PASSWORD FOR 'blender_id'@'%' = 'new_password';
