"""Hermes MQTT service for Rhasspy TTS with PyAudio."""
import argparse
import asyncio
import logging
import sys
from os import path
import paho.mqtt.client as mqtt
import rhasspyhermes.cli as hermes_cli
from lisa.lisa_configuration import config
from . import LisaHermesMqtt

_LOGGER = logging.getLogger("rhasspy-lisa-odas-hermes")


def main():
    """Main method."""

    # TODO: these should be imported as well
    # MAX_ODAS_SOURCES = int(config['INCOME_STREAM']['n_sources'])
    # CHUNK_SIZE_INCOME_STREAM = int(config['INCOME_STREAM']['chunk_size'])

    # Get some of the default values (config file ovveride it)
    SAMPLE_RATE_INCOME_STREAM = int(config['INCOME_STREAM']['sample_rate'])
    BYTES_PER_SAMPLE_INCOME_STREAM = int(config['INCOME_STREAM']['n_bits']) // 8
    ODAS_CONFIG = (config['ODAS']['odas_config'])
    ODAS_RCV_CONFIG_FILE = (config['ODAS']['odas_rcv_config'])

    parser = argparse.ArgumentParser(prog="rhasspy-lisa-odas-hermes")
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=SAMPLE_RATE_INCOME_STREAM,
        help="Sample rate of recorded audio in hertz (e.g., 16000)",
    )
    parser.add_argument(
        "--sample-width",
        type=int,
        default=BYTES_PER_SAMPLE_INCOME_STREAM,
        help="Sample width of recorded audio in bytes (e.g., 2)",
    )
    parser.add_argument(
        "--channels",
        type=int,
        default=1, # or MAX_ODAS_SOURCES,
        help="Number of channels in recorded audio (e.g. 1)"
    )
    parser.add_argument(
        "--demux",
        action='store_const', const=True,
        default=False,  
        help="Stream always one channel out by selecting the one with higher priority (priority mode latest source). "
             "If channels is provided is then discarded and only one streamed"
    )
    parser.add_argument(
        "--dump-detected",
        default=None,  
        help="If a proper path dir is provided a dump of the audio signal sent to Rhasspy is created. The file will contain the wave header"
    )
    parser.add_argument(
        "--output-site-id", help="If set, output audio data to a different site id"
    )
    parser.add_argument(
        "--udp-audio-host",
        default="127.0.0.1",
        help="Host for UDP audio (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--udp-audio-port",
        type=int,
        help="Send raw audio to UDP port outside ASR listening",
    )
    # TODO: merge in one config all the odas params (lisa rcv + wrapper)
    # TODO: reload from file with filename from argparse when merged
    parser.add_argument(
        "--odas-config",
        default=ODAS_CONFIG,
        help="ODAS configuration, default is: " + str(ODAS_CONFIG),
    )
    parser.add_argument(
        "--odas-rcv-config",
        default=ODAS_RCV_CONFIG_FILE,
        help="ODAS receiver configuration, default is: " + str(ODAS_RCV_CONFIG_FILE),
    )

    hermes_cli.add_hermes_args(parser)
    args = parser.parse_args()
    # TODO: reload if args.odas_config is not null, call load_configuration(file_name):

    hermes_cli.setup_logging(args)
    _LOGGER.debug(args)

    # Verify arguments
    if (args.sample_rate is None) or (args.sample_width is None) or (args.channels is None):
        print("--sample-rate, --sample-width, and --channels are required")
        _LOGGER.fatal("--sample-rate, --sample-width, and --channels are required")
        sys.exit(-1)
    if args.demux and args.channels > 1:
        print("In demux mode mode only one channel is streamed, channels arguments ignored")
        _LOGGER.fatal("In demux mode mode only one channel is streamed, channels arguments is ignored")
        sys.exit(-2)
    if args.dump_detected is not None:
        if not path.isdir(args.dump_detected):
            _LOGGER.fatal("A non existing folder for dump the output chunks is provided, but it is not a valid folder: " + str(args.dump_detected))
            sys.exit(-3)
    # Listen for messages
    client = mqtt.Client()
    hermes = LisaHermesMqtt(
        client,
        sample_rate=args.sample_rate,
        sample_width=args.sample_width,
        channels=args.channels,
        site_ids=args.site_id,
        output_site_id=args.output_site_id,
        udp_audio_host=args.udp_audio_host,
        udp_audio_port=args.udp_audio_port,
        odas_config=args.odas_config,
        demux=args.demux,
        odas_rcv_config=args.odas_rcv_config,
        dump_out_dir=args.dump_detected
    )

    _LOGGER.info("Connecting to %s:%s", args.host, args.port)
    hermes_cli.connect(client, args)
    client.loop_start()

    try:
        # Run event loop
        print("Ctrl-C to exit")
        asyncio.run(hermes.handle_messages_async())
    except KeyboardInterrupt:
        client.exit_request = True
        print('Ctrl-C detected')
    finally:
        _LOGGER.debug("Shutting down")
        client.loop_stop()


if __name__ == "__main__":
    main()
