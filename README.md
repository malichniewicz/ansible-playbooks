# Repo configuration
`cp .githooks/pre-commit .git/hooks`

# Setting up
## Ansible additional packages
* `ansible-pylibssh` - the default `paramiko` does not works well with the routerOS user/password method (required to setup an ansible user)
