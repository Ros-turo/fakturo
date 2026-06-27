import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(fmt="%(asctime)s | %(levelname)s | %(message)s",
                              datefmt="%Y-%m-%d %H:%M:%S")

handler = logging.FileHandler("app.log")
handler.setLevel(logging.NOTSET)
handler.setFormatter(fmt=formatter)

logger.addHandler(handler)