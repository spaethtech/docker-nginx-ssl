#!/usr/bin/env python3

import argparse, glob, os, shutil, subprocess
from urllib.request import urlretrieve

BASE_PATH = os.path.abspath(os.path.dirname(__file__))
NGINX_DIR = os.path.abspath(f"{BASE_PATH}/nginx")
CERTS_DIR = os.path.abspath(f"{BASE_PATH}/certbot")
CERT_SIZE = 4096

certbot_entrypoint = [
    "docker", "compose", "run",
    "--rm", # Automatically remove the container when it exits
    "--entrypoint", "certbot", # Use the certbot entrypoint
    "certbot" # The container name
]

#region Parse arguments

parser = argparse.ArgumentParser(
    prog='certificates',
    description='Configures SSL certificates for nginx in Docker'
)

parser.add_argument(
    "domains",
    type=str,
    nargs="+",
    help="The domains to certify"
)

parser.add_argument(
    "--email",
    type=str,
    help='Webmaster email address',
    default="rspaeth@spaethtech.com"
)

parser.add_argument(
    "--force",
    action="store_true",
    help="Force replacement of existing certificates",
    default=False
)

parser.add_argument(
    "--staging",
    action="store_true",
    help="Use staging environment",
    default=False
)

args = parser.parse_args()

#endregion

#region Check for Docker

if subprocess.run([ "which", "docker" ], stdout=subprocess.PIPE).returncode != 0:
    print("Error: Docker is not installed.")
    exit(1)

#endregion

#region Check firewall

ufw = subprocess.check_output(["sudo", "ufw", "status", "numbered"], text=True)

if "80/tcp" not in ufw and "443/tcp" not in ufw and "80,443/tcp" not in ufw:
    #print("Error: Firewall is blocking HTTP and HTTPS traffic.")
    #print("Try running the following commands:")
    #print(" - sudo ufw allow 80/tcp")
    #print(" - sudo ufw allow 443/tcp")
    #exit(1)
    subprocess.run([ "ufw", "allow", "80,443/tcp" ])

#endregion

#region Cleanup from previous runs

subprocess.run([ "docker", "compose", "down", "nginx" ])

print("Removing existing certbot/conf directory...")
shutil.rmtree(f"{CERTS_DIR}/conf", ignore_errors=True)
os.makedirs(f"{CERTS_DIR}/conf")
with open(f"{CERTS_DIR}/conf/.gitignore", "w") as file:
    file.write("*\n")
    file.write("!.gitignore\n")

print("Removing existing certbot/logs directory...")
shutil.rmtree(f"{CERTS_DIR}/logs", ignore_errors=True)
os.makedirs(f"{CERTS_DIR}/logs")
with open(f"{CERTS_DIR}/logs/.gitignore", "w") as file:
    file.write("*\n")
    file.write("!.gitignore\n")

print("Removing existing certbot/www directory...")
shutil.rmtree(f"{CERTS_DIR}/www", ignore_errors=True)
os.makedirs(f"{CERTS_DIR}/www")
with open(f"{CERTS_DIR}/www/.gitignore", "w") as file:
    file.write("*\n")
    file.write("!.gitignore\n")

print("Removing existing nginx/conf.d directory...")
shutil.rmtree(f"{NGINX_DIR}/conf.d", ignore_errors=True)

#endregion

#region Reverse proxy configuration (HTTP only)

print("Creating nginx/conf.d directory...")
if not os.path.exists(f"{NGINX_DIR}/conf.d/"):
    os.makedirs(f"{NGINX_DIR}/conf.d/")

print("Creating nginx/conf.d/default.conf...")
with open(f"{NGINX_DIR}/conf/default.conf", "r") as src_file:
    with open(f"{NGINX_DIR}/conf.d/default.conf", "w") as dst_file:
        default_conf = src_file.read()
        default_conf = default_conf.replace("__SERVER_NAME__", args.domains[0])
        dst_file.write(default_conf)

print("Starting nginx with HTTP only...")
subprocess.run([ "docker", "compose", "up", "--force-recreate", "-d", "nginx" ])

#endregion

#region Request certificates

print(f"Requesting Let's Encrypt certificates for {args.domains[0]}...")
domains = ["-d " + domain for domain in args.domains]

certonly_command = [
    "certonly",
    "--webroot",
    "--webroot-path", "/var/www/certbot",
    "--email", f"{args.email}",
    "--non-interactive",
    "--no-eff-email",
    "--rsa-key-size", f"{CERT_SIZE}",
    "--agree-tos",
    "--force-renewal",
    *domains
]

if args.staging:
    certonly_command.append("--staging")

subprocess.run([ *certbot_entrypoint, *certonly_command ])

#endregion

#region Download recommended SSL options and parameters

GIT_BASE = "https://raw.githubusercontent.com/certbot/certbot/master"

SSL_REPO = "certbot-nginx/certbot_nginx"
SSL_NAME = "options-ssl-nginx.conf"
SSL_PATH = f"{GIT_BASE}/{SSL_REPO}/_internal/tls_configs/{SSL_NAME}"

PEM_REPO = "certbot/certbot"
PEM_NAME = "ssl-dhparams.pem"
PEM_PATH = f"{GIT_BASE}/{PEM_REPO}/{PEM_NAME}"

if not os.path.exists(f"{CERTS_DIR}/conf/{SSL_NAME}"):
    print("Downloading recommended SSL Options...")
    urlretrieve(SSL_PATH, f"{CERTS_DIR}/conf/{SSL_NAME}")

if not os.path.exists(f"{CERTS_DIR}/conf/{PEM_NAME}"):
    print("Downloading recommended Diffie-Hellman Parameters...")
    urlretrieve(PEM_PATH, f"{CERTS_DIR}/conf/{PEM_NAME}")

#endregion

#region Configure nginx for HTTPS

print("Creating nginx/conf.d/default-ssl.conf...")
with open(f"{NGINX_DIR}/conf/default-ssl.conf", "r") as src_file:
    with open(f"{NGINX_DIR}/conf.d/default-ssl.conf", "w") as dst_file:
        ssl_conf = src_file.read()
        ssl_conf = ssl_conf.replace("__SERVER_NAME__", args.domains[0])
        dst_file.write(ssl_conf)

print("Starting nginx with HTTPS...")
subprocess.run([ "docker", "compose", "up", "--force-recreate", "-d", "nginx" ])
