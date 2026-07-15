#!/bin/bash
set -e

MOODLE_DIR="/var/www/html"
MOODLE_DATA="/var/www/moodledata"

wait_for_db() {
    echo "Waiting for MariaDB to be ready..."
    local retries=30
    while ! php -r "
        \$conn = @mysqli_connect(
            '${MOODLE_DB_HOST}', '${MOODLE_DB_USER}',
            '${MOODLE_DB_PASSWORD}', '${MOODLE_DB_NAME}', ${MOODLE_DB_PORT:-3306}
        );
        exit(\$conn ? 0 : 1);
    " 2>/dev/null; do
        retries=$((retries - 1))
        if [ $retries -le 0 ]; then
            echo "ERROR: MariaDB not available after 30 attempts"
            exit 1
        fi
        echo "  Waiting... ($retries attempts left)"
        sleep 3
    done
    echo "MariaDB is ready."
}

install_moodle() {
    echo "Running Moodle CLI installer..."
    php "${MOODLE_DIR}/admin/cli/install.php" \
        --wwwroot="${MOODLE_WWWROOT}" \
        --dataroot="${MOODLE_DATA}" \
        --dbtype="mariadb" \
        --dbhost="${MOODLE_DB_HOST}" \
        --dbname="${MOODLE_DB_NAME}" \
        --dbuser="${MOODLE_DB_USER}" \
        --dbpass="${MOODLE_DB_PASSWORD}" \
        --dbport="${MOODLE_DB_PORT:-3306}" \
        --fullname="${MOODLE_SITE_FULLNAME:-FCIM ELSE Platform}" \
        --shortname="${MOODLE_SITE_SHORTNAME:-ELSE}" \
        --adminuser="${MOODLE_ADMIN_USER:-admin}" \
        --adminpass="${MOODLE_ADMIN_PASSWORD}" \
        --adminemail="${MOODLE_ADMIN_EMAIL:-admin@fcim.utm.md}" \
        --lang="${MOODLE_LANG:-en}" \
        --agree-license \
        --non-interactive

    chown www-data:www-data "${MOODLE_DIR}/config.php"
    chmod 644 "${MOODLE_DIR}/config.php"
    echo "Moodle installation complete."
}

setup_cron() {
    echo "* * * * * www-data /usr/local/bin/php ${MOODLE_DIR}/admin/cli/cron.php >/dev/null 2>&1" \
        > /etc/cron.d/moodle
    chmod 644 /etc/cron.d/moodle
    cron
}

wait_for_db

if [ ! -f "${MOODLE_DIR}/config.php" ]; then
    install_moodle
fi

setup_cron

exec apache2-foreground
