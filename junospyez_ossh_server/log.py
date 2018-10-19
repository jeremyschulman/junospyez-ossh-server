from junospyez_ossh_server import about
import logging

# TODO: add logging.conf for debug purposes ...

# import logging
# logging_conf_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '../logging.conf'))
# logging.config.fileConfig(logging_conf_path)
# logger = logging.getLogger(__name__)


logger = logging.getLogger(about.package_name)


def basic():
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
