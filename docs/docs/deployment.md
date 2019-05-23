# Deployment

How to deploy Blender ID in production and how to push updates.


## Standard deploy playbook

* Merge the required commits from `master` into `production` branch
* Run unittests
* Push `production` to origin
* Run `cd docker; ./deploy.sh full`


## Documentation deploy playbook

* Move to `docs`, run `mkdocs serve` and check that the docs look good at the address provided by `mkdocs`.
* `export RSYNC_PASSWORD=secret`
* `rsync -azP site/ rsync://blenderid@www.blender.org/id/`


## Full setup from scratch

See [docker/README.md](https://developer.blender.org/diffusion/BID/browse/master/docker/README.md?as=remarkup)
in the Blender ID sources.
