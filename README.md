# rhasspy-lisa-odas-hermes

An input module of ODAS beamformed sources for Rhasspy  and a sensor with DOA capabilities and activity identification. In the direction of providing a more robust signal for  infering specific intents.

This module is based on the rhasspy-pyaudio module and records audio from [ODAS](https://github.com/introlab/odas) and publishes WAV chunks according to the [Hermes protocol](https://docs.snips.ai/reference/hermes).
Furthermore, specific messages for the DOA from ODAS of localized (potential) sources and tracked sources are produced.
See [lisa rhasppy messages](https://github.com/lawrence-iviani/rhasspy-lisa-odas-hermes/blob/master/lisa/rhasppy_messages.py)

# Run the module

## Build ODAS

See [lisa-ODAS-receiver](https://github.com/lawrence-iviani/rhasspy-lisa-odas-hermes/tree/master/lisa-odas/demo/lisa-ODAS-receiver)

**VERY IMPORTANT, in all cases at today the lisa-odas library must be build separately **

Adjustment in the path could be necessary

## Running With Docker

```bash
$ docker run -it rhasspy/rhasspy-lisa-odas-hermes:<VERSION> <ARGS>
```

## Building From Source

Clone the repository and create the virtual environment:

```bash
$ git clone https://github.com/rhasspy/rhasspy-lisa-odas-hermes.git
$ cd rhasspy-lisa-odas-hermes
$ ./configure --enable-in-place
$ make
$ make install
```


Run the `rhasspy-lisa-odas-hermes` script to access the command-line interface:

```bash
$ ./rhasspy-lisa-odas-hermes --help
```

## Building the Docker Image

Run `scripts/build-docker.sh` with a local docker registry:

```bash
$ DOCKER_REGISTRY=myregistry:12345 scripts/build-docker.sh
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

## RHASSPY 

Rhasspy (pronounced RAH-SPEE) is an open source, fully offline voice assistant toolkit for many languages that works well with Home Assistant, Hass.io, and Node-RED.

https://rhasspy.readthedocs.io/en/latest/

## Speech Recognition

Part of rhasspy. This part will be moved

### KALDI 

[Kaldi](https://kaldi-asr.org/)
Kaldi is a toolkit for speech recognition, intended for use by speech recognition researchers and professionals. Find the code repository on [git](http://github.com/kaldi-asr/kaldi)

### DEEPSPEECH

[Git DeepSpeech](https://github.com/mozilla/DeepSpeech)

DeepSpeech is an open source Speech-To-Text engine, using a model trained by machine learning techniques based on Baidu's Deep Speech research paper. Project DeepSpeech uses Google's TensorFlow to make the implementation easier.

Documentation for installation, usage, and training models is available on [deepspeech.readthedocs.io](http://deepspeech.readthedocs.io/?badge=latest)

#### Paper

https://arxiv.org/abs/1412.5567


## Based onRhasspy PyAudio Hermes MQTT Service

**As an example from the forked repos, CI not implemented yet**

[![Continous Integration](https://github.com/rhasspy/rhasspy-microphone-pyaudio-hermes/workflows/Tests/badge.svg)](https://github.com/rhasspy/rhasspy-microphone-pyaudio-hermes/actions)
[![GitHub license](https://img.shields.io/github/license/rhasspy/rhasspy-microphone-pyaudio-hermes.svg)](https://github.com/rhasspy/rhasspy-microphone-pyaudio-hermes/blob/master/LICENSE)

