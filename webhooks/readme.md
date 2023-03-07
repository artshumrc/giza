# Webhook based deploys

## Resources
- https://github.com/adnanh/webhook
- https://maximorlov.com/automated-deployments-from-github-with-webhook/
- https://www.overflowedminds.net/writings/continuous-deployment-with-github-actions-and-webhook
 
 ## Setup
- Assumes you've already set up the webhook on Github. If not, see [here](https://docs.github.com/en/developers/webhooks-and-events/creating-webhooks).
- Assumes you've configured AWS credentials for an fasrc_cd profile

1. Install `go` and webhook server - https://github.com/adnanh/webhook. May get installed at `~/go/bin/webhook`
2. Create or copy hooks file at `~/hooks.json`. Add the `GITHUB_SECRET` here or set up environment variables
3. Make sure `docker/redeploy.sh` is executable: `chmod a+x redeploy.sh`. This is the only webhook related file not in this directory as it is more closely related to the docker context.
4. Run webhook server with the following command: `webhook -hooks ~/hooks.json -logfile /var/log/webhook/giza-deploy/giza-deploy.log -verbose`. If using an environment variable for `GITHUB_SECRET`, add `-template` to the command
5. Make sure Apache or Nginx are proxying `:9000` requests to the webhook server
6. Test the webhook server by running `curl -X POST http://localhost:9000/hooks/giza-deploy`
7. Set up webhook server as a `systemd` service
    - Copy the `webhook.service` file to `/etc/systemd/system/`
    - Copy `redeploy.sh` to `/usr/local/bin/` and ensure it is owned by `giza:giza` and executable
    - Ensure 
    - `sudo systemctl enable webhook.service`
    - `sudo systemctl start webhook.service`
8. Check status of the service and troubleshoot
    - `sudo systemctl status webhook.service`
    - `sudo journalctl -u webhook.service`
    - `sudo lsof -i:9000`