FROM php:7.4-apache

RUN apt-get update && apt-get install -y \
    libxml2-dev \
    libzip-dev \
    libpng-dev \
    libjpeg-dev \
    libfreetype6-dev \
    libicu-dev \
    libldap2-dev \
    libonig-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    wget \
    unzip \
    git \
    cron \
    && rm -rf /var/lib/apt/lists/*

RUN docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-configure ldap --with-libdir=lib/x86_64-linux-gnu \
    && docker-php-ext-install -j$(nproc) \
        gd \
        intl \
        mbstring \
        mysqli \
        pdo_mysql \
        soap \
        tokenizer \
        xml \
        xmlrpc \
        zip \
        fileinfo \
        opcache \
        curl \
        ldap \
        exif

RUN a2enmod rewrite expires headers

COPY apache-moodle.conf /etc/apache2/sites-available/000-default.conf
COPY php.ini /usr/local/etc/php/conf.d/moodle.ini
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN wget -q -O /tmp/moodle.tgz \
    "https://download.moodle.org/download.php/direct/stable39/moodle-3.9.24.tgz" \
    && tar -xzf /tmp/moodle.tgz -C /var/www/html --strip-components=1 \
    && rm /tmp/moodle.tgz \
    && find /var/www/html -type d -exec chmod 755 {} \; \
    && find /var/www/html -type f -exec chmod 644 {} \; \
    && chown -R www-data:www-data /var/www/html

RUN mkdir -p /var/www/moodledata \
    && chown -R www-data:www-data /var/www/moodledata \
    && chmod 777 /var/www/moodledata

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
