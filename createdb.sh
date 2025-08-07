#!/bin/bash
set -euo pipefail

source .env

if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${CLINICALTRIALS_DB_NAME}'" | grep -q 1; then
    echo "Creating user ${CLINICALTRIALS_DB_NAME}..."
    sudo -u postgres createuser --superuser ${CLINICALTRIALS_DB_NAME}
else
    echo "User ${CLINICALTRIALS_DB_NAME} already exists, skipping creation..."
fi

# Set the password (works whether user was just created or already existed)
sudo -u postgres psql -c "ALTER USER ${CLINICALTRIALS_DB_NAME} PASSWORD '${CLINICALTRIALS_DB_PASS}';"

# Check if database exists, create only if it doesn't
if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw ${CLINICALTRIALS_DB}; then
    echo "Creating database ${CLINICALTRIALS_DB}..."
    sudo -u postgres createdb --owner=${CLINICALTRIALS_DB_NAME} ${CLINICALTRIALS_DB}
else
    echo "Database ${CLINICALTRIALS_DB} already exists, skipping creation..."
fi

# 3. Test the connection
echo "Testing database connection..."
PGPASSWORD=${CLINICALTRIALS_DB_PASS} psql -h localhost -U ${CLINICALTRIALS_DB_NAME} -d ${CLINICALTRIALS_DB} -c "SELECT version();"

echo "Database setup complete!"
echo "Connection details:"
echo "  Host: localhost"
echo "  Port: 5432 (default)"
echo "  Database: ${CLINICALTRIALS_DB}"
echo "  User: ${CLINICALTRIALS_DB_NAME}"
echo "  Password: ${CLINICALTRIALS_DB_PASS}"
