import os
import logging

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a handler that writes log messages to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create a formatter to format the log messages
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add the console handler to the logger
logger.addHandler(console_handler)

def load_styles(styles_dir):
    """
    Loads CSS styles from files in the specified directory.

    Args:
        styles_dir (str): The path to the directory containing the CSS files.

    Returns:
        dict: A dictionary where keys are style names and values are the corresponding CSS content.
    """
    styles = {}
    logger.debug(f"Reading styles directory: {styles_dir}")
    try:
        files = os.listdir(styles_dir)
        logger.debug(f"Files found: {files}")
        for file in files:
            if file.endswith('.css'):
                file_path = os.path.join(styles_dir, file)
                logger.debug(f"Processing file: {file_path}")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        first_line = f.readline().strip()
                        logger.debug(f"First line of file {file}: {first_line}")
                        parts = first_line.split('$')
                        if len(parts) == 2:
                            style_name = parts[0].replace('/*', '').strip()
                            author_info = parts[1].strip()
                            with open(file_path, 'r', encoding='utf-8') as f:
                                css_content = f.read()
                            styles[style_name] = {'content': css_content, 'author': author_info}
                            logger.info(f"Added style: {style_name} by {author_info}")
                        else:
                            logger.warning(f"Skipping file {file} due to invalid header format.")
                except Exception as e:
                    logger.error(f"Error reading file {file}: {e}")
    except FileNotFoundError:
        logger.error(f"Directory not found: {styles_dir}")
    except Exception as e:
        logger.error(f"Error reading styles directory: {e}")
    return styles

# Example usage (when this file is run as a script)
if __name__ == "__main__":
    styles_dir = os.path.dirname(os.path.abspath(__file__))
    loaded_styles = load_styles(styles_dir)
    for style_name, style_data in loaded_styles.items():
        print(f"Style: {style_name}, Author: {style_data['author']}")
