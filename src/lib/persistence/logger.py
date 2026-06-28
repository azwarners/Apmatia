import logging
import os

# Create a logger
logger = logging.getLogger('apmatia')
logger.setLevel(logging.DEBUG)

# Create a file handler
file_handler = logging.FileHandler(os.path.join(os.getcwd(), 'apmatia.log'))
file_handler.setLevel(logging.DEBUG)

# Create a console handler
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)

# Create a formatter and set it for the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Example usage
# logger.debug('This is a debug message')