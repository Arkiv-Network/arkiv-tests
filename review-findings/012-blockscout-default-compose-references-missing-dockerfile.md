# Blockscout default compose build references a missing Dockerfile

**Severity:** Medium

## Affected files

- `blockscout/docker-compose.yml:21`
- `blockscout/no-services.yml:29`
- `blockscout/README.md:20`

## Problem

The Blockscout README tells users to run the default compose file with `up --build`, and the default compose file tries to build the backend from `./docker/Dockerfile` relative to the repository root. This repository does not contain a `docker/` directory or `docker/Dockerfile`.

`blockscout/no-services.yml` has the same build reference.

## Impact

The documented default Blockscout startup path fails before containers are created. Users must know to choose one of the image-only compose files or provide an external Blockscout source tree, but that requirement is not reflected in the local docs.

## Evidence

`blockscout/docker-compose.yml:21-25` configures:

```yaml
build:
  context: ..
  dockerfile: ./docker/Dockerfile
```

`blockscout/no-services.yml:29-34` repeats the same build path.

`blockscout/README.md:20-29` documents `docker-compose up --build` as the default launch command.

`rg --files -g 'docker/**'` returns no files in this repository.

## Suggested fix

Either add the required Dockerfile/source tree, switch the default compose path to an image that exists, or update the README to make clear which compose files work standalone in this repository.
