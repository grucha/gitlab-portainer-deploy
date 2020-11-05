# gitlab-portainer-deploy

This tool makes it easy to deploy from CI to Portainer, without loosing original
compose file (stackfile) contents in Portainer.

All it does is read the compose file, replace the image of given service 
(in a very naive way) and shove updated compose file back into Portainer.

This fork is based on vvarp's gitlab-portainer-deploy, which doesn't preserve compose-file
and requires local compose file in repository.

## Usage

In `.gitlab-ci.yml`:

```yaml
deploy:
  stage: deploy
  image: gruszex/gitlab-portainer-deploy
  variables:
    PORTAINER_URL: ""
    PORTAINER_USERNAME: ""
    PORTAINER_PASSWORD: ""
  script:
    - deploy --stack_name=xxx --service-name=yyy --new-image=zzz:1.0 -e SOME_STACKFILE_VAR=value
    - OR:
    - deploy --stack_name=xxx --service-name=yyy,aaa --new-image=zzz:1.0 -e SOME_STACKFILE_VAR=value
  tags:
    - docker
```

## Why

Rationale for this kind of behaviour is not to loose, often complex,
compose file from eyesight and to still be able to update it manually
inside Portainer. Also not to have to sync common parts of compose file (e.g.
networks, volumes, anchors) between multiple repositories that push 
services to the same stack.

The reason for not parsing yaml is keeping anchors and links untouched.
Yaml parsers expand anchors and links, destroying original compose file 
(ruamel.yaml was supposed to manage this without expanding them
but failed with real world compose files).

This introduced a constraint to compose yaml: `image` must be specified as first item
in service definition.

## Local development

For easy local testing, make a virtualenv and install the code
with the following command:
`pip install --editable . `

From now on you have `deploy` command available in this env.
