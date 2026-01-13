import os
import shutil


def initialize_config():
    """
    Initialize config.toml from config.toml.example if config.toml doesn't exist
    """
    config_path = os.path.join(os.path.dirname(__file__), "config.toml")
    example_config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config.toml.example",
    )

    # Check if config.toml exists, if not copy from config.toml.example
    if not os.path.exists(config_path):
        if os.path.exists(example_config_path):
            shutil.copy(example_config_path, config_path)
            print(f"Created {config_path} from example configuration")
        else:
            print(f"Error: Neither {config_path} nor {example_config_path} exist.")


# Initialize the configuration when the module is imported
initialize_config()
