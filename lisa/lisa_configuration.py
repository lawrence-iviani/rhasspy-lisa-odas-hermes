from configparser import ConfigParser
import logging

# TODO: most of these fields are duplicated from odas config and must be the same here. So it would make sense to
# parse the odas config file

# Default values if ini file is not found
DEFAULTCONFIG_MAX_ODAS_SOURCES = 4
DEFAULTCONFIG_SST_TAG_LEN = 20  # as in common.h
# this is connect to the n bits in the output configuration of odas modules (SSS_x) (16 bits)
DEFAULTCONFIG_SAMPLE_RATE_INCOME_STREAM = 16000  # This the value defined as fs  in odas config sss separated or postfiltered
DEFAULTCONFIG_CHUNK_SIZE_INCOME_STREAM = 128  # This the value defined as hopSize  in odas config sss separated or postfiltered
DEFAULTCONFIG_N_BITS_INCOME_STREAM = 16  # This the value defined as nBits  in odas config sss separated or postfiltered
DEFAULTCONFIG_ODAS_RCV_LIB = '../lisa-odas/lib/liblisarcv'  # the location of liblisarcv.so, wrapper for ODAS. Compiled from source in the same repos
DEFAULTCONFIG_ODAS_CONFIG = 'lisa-odas/config/matrix-lisa/matrix_voice_LISA_1.cfg'
DEFAULTCONFIG_ODAS_EXE = 'lisa-odas/bin/odaslive'
# TODO: merge this in one file!
DEFAULTCONFIG_CONFIG_FILE = 'rhasspy_lisa_odas_hermes/config/lisa.cfg'
DEFAULTCONFIG_ODAS_RCV_CONFIG_FILE = "lisa-odas/config/matrix-lisa/odas-rcv.cfg"

_LOGGER = logging.getLogger("rhasspy-lisa-odas-hermes")

def get_configuration(file_name, save_default=True):
    try:
        _LOGGER.info('Loading configuration: ' + file_name)
        config = load_configuration(file_name)
    except FileNotFoundError as e:
        _LOGGER.warning('Config file not found, using default configuration')
        config = get_default_configuration()
        if save_default:
            save_configuration(file_name, config)
    return config


def get_default_configuration():
    config = ConfigParser()
    config['INCOME_STREAM'] = {'sample_rate': DEFAULTCONFIG_SAMPLE_RATE_INCOME_STREAM,
                               'chunk_size': DEFAULTCONFIG_CHUNK_SIZE_INCOME_STREAM,
                               'n_bits': DEFAULTCONFIG_N_BITS_INCOME_STREAM,
                               'n_sources': DEFAULTCONFIG_MAX_ODAS_SOURCES}
    config['ODAS'] = {'library': DEFAULTCONFIG_ODAS_RCV_LIB,
                      'SST_tag_len': DEFAULTCONFIG_SST_TAG_LEN,
                      'odas_exe': DEFAULTCONFIG_ODAS_EXE,
                      'odas_config': DEFAULTCONFIG_ODAS_CONFIG,
                      'odas_rcv_config': DEFAULTCONFIG_ODAS_RCV_CONFIG_FILE}

    return config


def save_configuration(file_name, config):
    _LOGGER.debug('Saving configuration in ' + file_name)
    with open(file_name, 'w') as configfile:
        config.write(configfile)


def load_configuration(file_name):
    config = ConfigParser()
    _LOGGER.debug('Open config file {}'.format(file_name))
    config.read_file(open(file_name))
    for s in config.sections():
        for i in config.items(s):
            _LOGGER.debug('[{}:{}]\t\t{}'.format(s, i[0], i[1]))
    return config


# load the configuration as defined in config file
config = get_configuration(DEFAULTCONFIG_CONFIG_FILE)
