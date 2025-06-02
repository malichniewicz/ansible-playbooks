# Repo configuration
`cp .githooks/pre-commit .git/hooks`

# Setting up
## Ansible additional packages
* `ansible-pylibssh` - the default `paramiko` does not works well with the routerOS user/password method (required to setup an ansible user)
## error in libcrypto
ensure that RSA key used to authenticate has extra LF on the end of the file
## Cloudflare tunnel configuration
* For each domain service should be set to `https://traefik` (where `traefik` is a Traefik container name)
* When configuring public hostname for Cloudflare tunnel, make sure that `Additional application settings` -> `TLS` -> `No TLS Verify` option is checked. There will be some hostname mismatch between container and expected value