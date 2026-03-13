FROM postgres:13-alpine

RUN apk add --no-cache python3 py3-pip && \
    pip3 install --no-cache-dir --break-system-packages openpyxl

# Copy init scripts into the image and fix line endings
COPY convert_xlsx.py /docker-entrypoint-initdb.d/convert_xlsx.py
COPY init.sh /docker-entrypoint-initdb.d/init.sh
COPY setup.sql /docker-entrypoint-initdb.d/setup.sql

# Fix Windows CRLF line endings and make shell script executable
RUN sed -i 's/\r$//' /docker-entrypoint-initdb.d/init.sh && \
    chmod +x /docker-entrypoint-initdb.d/init.sh && \
    sed -i 's/\r$//' /docker-entrypoint-initdb.d/convert_xlsx.py && \
    sed -i 's/\r$//' /docker-entrypoint-initdb.d/setup.sql
