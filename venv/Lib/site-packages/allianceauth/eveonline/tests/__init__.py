import logging
import os


def set_logger(logger_name: str, name: str) -> object:
    """set logger for current test module

    Args:
    - logger: current logger object
    - name: name of current module, e.g. __file__

    Returns:
    - amended logger
    """

    # reconfigure logger so we get logging from tested module
    f_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(module)s:%(funcName)s - %(message)s'
    )
    f_handler = logging.FileHandler(
        f'{os.path.splitext(name)[0]}.log',
        'w+'
    )
    f_handler.setFormatter(f_format)
    logger = logging.getLogger(logger_name)
    logger.level = logging.DEBUG
    logger.addHandler(f_handler)
    logger.propagate = False
    return logger
