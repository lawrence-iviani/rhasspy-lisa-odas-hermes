from configparser import ConfigParser

# Default values if ini file is not found
MAX_ODAS_SOURCES = 4
SST_TAG_LEN = 20  # as in common.h
# this is connect to the n bits in the output configuration of odas modules (SSS_x) (16 bits)
SAMPLE_RATE_INCOME_STREAM = 16000  # This the value defined as fs  in odas config sss separated or postfiltered
CHUNK_SIZE_INCOME_STREAM = 128  # This the value defined as hopSize  in odas config sss separated or postfiltered
N_BITS_INCOME_STREAM = 16  # This the value defined as nBits  in odas config sss separated or postfiltered
ODAS_RCV_LIB = '../lisa-odas/lib/liblisarcv'  # the location of liblisarcv.so, wrapper for ODAS. Compiled from source in the same repos
ODAS_CONFIG = 'lisa-odas/config/matrix-lisa/matrix_voice_LISA_1.cfg'
ODAS_EXE = 'lisa-odas/bin/odaslive'
CONFIG_FILE = 'config_file/lisa.cfg'
# BYTES_PER_SAMPLE_INCOME_STREAM = N_BITS_INCOME_STREAM // 8


def get_configuration(file_name):
    try:
        config = load_configuration(file_name)
    except FileNotFoundError as e:
        print('Config file not found, using default configuration')
        config = get_default_configuration()
    print(config)
    return config


def get_default_configuration():
    config = ConfigParser()
    config['INCOME_STREAM'] = {'sample_rate': SAMPLE_RATE_INCOME_STREAM,
                               'chunk_size': CHUNK_SIZE_INCOME_STREAM,
                               'n_bits': N_BITS_INCOME_STREAM,
                               'n_sources': MAX_ODAS_SOURCES}
    config['ODAS'] = {'library': ODAS_RCV_LIB,
                      'SST_tag_len': SST_TAG_LEN,
                      'odas_exe': ODAS_EXE,
                      'odas_config': ODAS_CONFIG}

    return config


def save_configuration(file_name, config):
    with open(file_name, 'w') as configfile:
        config.write(configfile)


def load_configuration(file_name):
    config = ConfigParser()
    config.read_file(open(file_name))
    return config


# load the configuration as defined in config file
config = get_configuration(CONFIG_FILE)
save_configuration(CONFIG_FILE, config)
