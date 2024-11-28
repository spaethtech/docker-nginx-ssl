
```
services:
    nginx:
        image: nginx:latest
        container_name: nginx
        ports:
            - "80:80"
            - "443:443"
        restart: unless-stopped
        volumes:
            - ./docker/nginx/conf.d/:/etc/nginx/conf.d/:ro
            - ./docker/nginx/html/:/var/www/html/:ro
            - ./docker/certbot/www/:/var/www/certbot/:ro
            - ./docker/certbot/conf/:/etc/letsencrypt/:ro
        command: "/bin/sh -c 'while :; do sleep 6h & wait $${!}; nginx -s reload; done & nginx -g \"daemon off;\"'"

    certbot:
        image: certbot/certbot:latest
        container_name: certbot
        restart: no
        volumes:
            - ./docker/certbot/www/:/var/www/certbot/:rw
            - ./docker/certbot/conf/:/etc/letsencrypt/:rw
            - ./docker/certbot/logs/:/var/log/letsencrypt/:rw
        entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
```

```bash

```
