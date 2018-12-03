from configparser import ConfigParser
import os.path


def get_config(section='postgresql', filename='config.ini'):
    """
    Parses config.ini file
    :return: parameters from the required section of config.ini file
    """
    config_path = os.path.dirname(os.path.realpath(__file__))
    os.chdir(config_path)

    if os.path.exists('config.mine.ini'):
        filename = 'config.mine.ini'
    parser = ConfigParser()
    parser.read(filename)

    config = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            config[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return config
