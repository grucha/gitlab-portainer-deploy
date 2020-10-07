import json
import re
import sys

import click
import requests


@click.command()
@click.option("--portainer-url", envvar="PORTAINER_URL", required=True, help="Portainer instance URL")
@click.option("--portainer-username", envvar="PORTAINER_USERNAME", required=True, help="Portainer username")
@click.option("--portainer-password", envvar="PORTAINER_PASSWORD", required=True, help="Portainer password")
@click.option("--stack-name", envvar="STACK_NAME", default=None, required=True)
@click.option("--service-name", envvar="SERVICE_NAME", default=None, required=True)
@click.option("--new-image", envvar="NEW_IMAGE", default=None, required=True)
@click.option("--env-var", "-e", multiple=True, default=[], required=False)
@click.option("--verbose", "-v", default=False, required=False)
def main(portainer_url, portainer_username, portainer_password, stack_name, service_name, new_image, env_var, verbose):
    # Build list of env vars to be passed on to Portainer
    stack_env = []
    if len(env_var) > 0:
        click.echo("Environment variables for stackfile:\n")
        for e in env_var:
            name = e.split("=")[0]
            value = "=".join(e.split("=")[1:])
            stack_env.append({
                "name": name,
                "value": value,
            })
            click.echo(f"  {name}: {value}")
    else:
        click.echo("No environment variables for stackfile.")

    # Get auth token
    click.echo(click.style("\nGetting auth token...", fg="yellow"), nl=False)
    auth = requests.post(f"{portainer_url}/auth", json={
        "Username": portainer_username,
        "Password": portainer_password,
    })

    if auth.status_code != 200:
        click.echo(click.style(f"\nHTTP {auth.status_code} error while trying to obtain JWT token", fg="red"))
        sys.exit(1)

    headers = {"Authorization": "Bearer " + auth.json()["jwt"]}
    click.echo(click.style(" done", fg="green"))

    # Get IDs for target endpoint and stack
    click.echo(click.style("Getting target stack ID...", fg="yellow"), nl=False)
    stacks = requests.get(f"{portainer_url}/stacks", headers=headers)
    if stacks.status_code != 200:
        click.echo(f"\nHTTP {stacks.status_code} error while trying to get list of Portainer stacks")
        sys.exit(1)

    stack_id = None
    for s in stacks.json():
        if s["Name"] == stack_name:
            stack_id = str(s["Id"])
            endpoint_id = str(s["EndpointId"])

    if stack_id is None:
        click.echo(click.style(f" can't find stack \"{stack_name}\" in Portainer", fg="red"))
        sys.exit(1)

    click.echo(click.style(" done", fg="green"))

    # Try to read stackfile contents
    click.echo(click.style("Getting stackfile...", fg="yellow"), nl=False)
    stackfile = requests.get(f"{portainer_url}/stacks/{stack_id}/file", headers=headers)
    if stackfile.status_code != 200:
        click.echo(f"\nHTTP {stackfile.status_code} error while trying to get stack compose file contents")
        print(stackfile.request.url)
        sys.exit(1)

    stackfile_content = stackfile.json()["StackFileContent"]
    updated_stackfile_lines = []
    click.echo(click.style(" done", fg="green"))

    # Now go through yaml lines and update image line of requested service
    current_image = None
    found_service = False
    for line in stackfile_content.splitlines():
        if found_service:  # Service definition started in previous line
            if "image:" not in line:
                click.echo(click.style(
                    f"\nFirst line of service {service_name} definition was not `image` key. "
                    f"Can't proceed with update.", fg="red"))
                sys.exit(1)
            whitespace, current_image = line.split("image:", maxsplit=1)
            updated_stackfile_lines.append(f"{whitespace}image: {new_image}")
            found_service = False
            continue

        # Mark service definition to know that in next line there should be image specified
        # (yep, very naive approach but works, we just always specify image as first line
        #  of service definition)
        if re.match(f"^\\s+{service_name}:", line):
            found_service = True
        else:
            found_service = False

        updated_stackfile_lines.append(line)

    if current_image is None:
        click.echo(click.style(
            f"\nService {service_name} definition was not found in stack yaml.", fg="red"))
        sys.exit(1)

    # Update stack
    click.echo(click.style("Requesting stack update...", fg="yellow"), nl=False)
    r = requests.put(
        f"{portainer_url}/stacks/{stack_id}?endpointId={endpoint_id}",
        headers=headers,
        json={
            "StackFileContent": "\n".join(updated_stackfile_lines),
            "Env": stack_env,
            "Prune": False
        }
    )
    click.echo(click.style(" done", fg="green"))

    click.echo(f"\nRequest to update stack finished with HTTP {r.status_code}")
    if verbose:
        click.echo(f"\n{json.dumps(r.json(), indent=4)}")

    if r.status_code != 200:
        click.echo(click.style(f"Deployment failed", fg="red"))
        sys.exit(1)

    click.echo(click.style(f"\nUpdated service {service_name}:"
                           f"\n  from: {current_image.strip()}"
                           f"\n    to: {new_image.strip()}", fg="green"))
