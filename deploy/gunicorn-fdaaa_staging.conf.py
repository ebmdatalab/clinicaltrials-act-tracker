bind = "unix:/tmp/gunicorn-fdaaa_staging.sock"
workers = 2
timeout = 6000  # 100 minutes so we have time for the management command to return
