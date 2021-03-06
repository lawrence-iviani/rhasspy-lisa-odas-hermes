# rhasspy-lisa-odas-hermes

An input module of ODAS beamformed sources for [Rhasspy](https://rhasspy.readthedocs.io/en/latest/#services)  and a sensor with DOA capabilities and activity identification. In the direction of providing a more robust signal to noise ratio for infering specific intents with rhasspy. 

This module is based on the rhasspy-pyaudio module and records audio from [ODAS](https://github.com/introlab/odas) and publishes WAV chunks according to the [Hermes protocol](https://docs.snips.ai/reference/hermes).
Furthermore, specific messages for the DOA from ODAS of localized (potential) sources and tracked sources are produced.
See [lisa rhasppy messages](https://github.com/lawrence-iviani/rhasspy-lisa-odas-hermes/blob/master/lisa/rhasppy_messages.py)

# Run the module

## Build ODAS

See [lisa-ODAS-receiver](https://github.com/lawrence-iviani/lisa-odas)

~~**VERY IMPORTANT, in all cases at today the lisa-odas library must be build separately**~~

Adjustment in the path could be necessary

## Requirements

* Python 3.7

```bash
$ docker run -it rhasspy/rhasspy-lisa-odas-hermes:<VERSION> <ARGS>
```

## Building From Source

Clone (including submodules) the repository and create the virtual environment:

```bash
$ git clone --recurse-submodules https://github.com/lawrence-iviani/rhasspy-lisa-odas-hermes.git
$ cd rhasspy-lisa-odas-hermes
## rhasspy run in virtual env
$ ./configure
## or use the system environment
$ ./configure --enable-in-place

$ make
$ make install
```

Run the `rhasspy-lisa-odas-hermes` script to access the command-line interface:

```bash
$ ./rhasspy-lisa-odas-hermes --help
```

## Building the Docker Image

**NOT TESTED**

Run `scripts/build-docker.sh` with a local docker registry:

## Deployment

```bash
$ make dist
```

## Running


```bash
$ bin/rhasspy-lisa-odas-hermes <ARGS>
```



Requires [Docker Buildx](https://docs.docker.com/buildx/working-with-buildx/). Set `PLATFORMS` environment to only build for specific platforms (e.g., `linux/amd64`).

This will create a Docker image tagged `rhasspy/rhasspy-lisa-odas-hermes:<VERSION>` where `VERSION` comes from the file of the same name in the source root directory.

NOTE: If you add things to the Docker image, make sure to whitelist them in `.dockerignore`.


## Command-Line Options

Based on the pyaudio module, although they are tunable with several personalization they must be equal as defined in the ODAS revceiver. The default values are defined in [config_file/lisa.cfg](https://github.com/lawrence-iviani/rhasspy-lisa-odas-hermes/blob/master/config_file/lisa.cfg) and must match the ODAS configuration file as defined in the field [ODAS] odas_config.

```

usage: rhasspy-lisa-odas-hermes [-h] [--sample-rate SAMPLE_RATE]
                                [--sample-width SAMPLE_WIDTH]
                                [--channels CHANNELS] [--demux]
                                [--output-site-id OUTPUT_SITE_ID]
                                [--udp-audio-host UDP_AUDIO_HOST]
                                [--udp-audio-port UDP_AUDIO_PORT]
                                [--odas-config ODAS_CONFIG] [--host HOST]
                                [--port PORT] [--username USERNAME]
                                [--password PASSWORD] [--tls]
                                [--tls-ca-certs TLS_CA_CERTS]
                                [--tls-certfile TLS_CERTFILE]
                                [--tls-keyfile TLS_KEYFILE]
                                [--tls-cert-reqs {CERT_REQUIRED,CERT_OPTIONAL,CERT_NONE}]
                                [--tls-version TLS_VERSION]
                                [--tls-ciphers TLS_CIPHERS]
                                [--site-id SITE_ID] [--debug]
                                [--log-format LOG_FORMAT]


optional arguments:
  -h, --help            show this help message and exit
  --sample-rate SAMPLE_RATE
                        Sample rate of recorded audio in hertz (e.g., 16000)
  --sample-width SAMPLE_WIDTH
                        Sample width of recorded audio in bytes (e.g., 2)
  --channels CHANNELS   Number of channels in recorded audio (e.g., 1)
  --demux               Stream always one channel out by selecting the one
                        with higher priority (priority mode latest source). If
                        channels is provided is then discarded and only one
                        streamed
  --output-site-id OUTPUT_SITE_ID
                        If set, output audio data to a different site id
  --udp-audio-host UDP_AUDIO_HOST
                        Host for UDP audio (default: 127.0.0.1)
  --udp-audio-port UDP_AUDIO_PORT
                        Send raw audio to UDP port outside ASR listening
  --odas-config ODAS_CONFIG
                        ODAS configuration, default is: lisa-
                        odas/config/matrix-lisa/matrix_voice_LISA_1.cfg
  --host HOST           MQTT host (default: localhost)
  --port PORT           MQTT port (default: 1883)
  --username USERNAME   MQTT username
  --password PASSWORD   MQTT password
  --tls                 Enable MQTT TLS
  --tls-ca-certs TLS_CA_CERTS
                        MQTT TLS Certificate Authority certificate files
  --tls-certfile TLS_CERTFILE
                        MQTT TLS certificate file (PEM)
  --tls-keyfile TLS_KEYFILE
                        MQTT TLS key file (PEM)
  --tls-cert-reqs {CERT_REQUIRED,CERT_OPTIONAL,CERT_NONE}
                        MQTT TLS certificate requirements (default:
                        CERT_REQUIRED)
  --tls-version TLS_VERSION
                        MQTT TLS version (default: highest)
  --tls-ciphers TLS_CIPHERS
                        MQTT TLS ciphers to use
  --site-id SITE_ID     Hermes site id(s) to listen for (default: all)
  --debug               Print DEBUG messages to the console
  --log-format LOG_FORMAT
                        Python logger format

```

# SW References 


#### Paper

https://arxiv.org/abs/1412.5567


## Based onRhasspy PyAudio Hermes MQTT Service

**As an example from the forked repos, CI not implemented yet**

[![Continous Integration](https://github.com/rhasspy/rhasspy-microphone-pyaudio-hermes/workflows/Tests/badge.svg)](https://github.com/rhasspy/rhasspy-microphone-pyaudio-hermes/actions)
[![GitHub license](https://img.shields.io/github/license/rhasspy/rhasspy-microphone-pyaudio-hermes.svg)](https://github.com/rhasspy/rhasspy-microphone-pyaudio-hermes/blob/master/LICENSE)

