from junospyez_ossh_server import about
import logging

# TODO: add logging.conf for debug purposes ...

# import logging
# logging_conf_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '../logging.conf'))
# logging.config.fileConfig(logging_conf_path)
# log = logging.getLogger(__name__)


log = logging.getLogger(about.package_name)
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler())
