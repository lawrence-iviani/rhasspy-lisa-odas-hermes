"""Hermes MQTT server for Rhasspy TTS using external program"""
import io
import logging
import socket
import threading
import time
import typing
import wave
from queue import Queue, Full
import webrtcvad
import os.path

# Import for odas
import numpy as np
from multiprocessing import Process, RawValue, Lock
from sys import exit
from time import sleep
from _collections import deque
from copy import deepcopy
from subprocess import Popen

from rhasspyhermes.asr import AsrStartListening, AsrStopListening
from rhasspyhermes.audioserver import (
    AudioDevice,  # Returned in handle_get_devices
    AudioDeviceMode,  # same
    AudioDevices, # same
    AudioFrame,  # publish_chunks
    AudioGetDevices,
    AudioRecordError,
    AudioSummary,
    SummaryToggleOff,  # Print details
    SummaryToggleOn,  # Print details
)
from rhasspyhermes.base import Message
from rhasspyhermes.client import GeneratorType, HermesClient


from lisa.lisa_switcher_bindings import SSL_struct, SSL_src_struct, SST_struct, SST_src_struct
from lisa.lisa_switcher_bindings import callback_SSL_func, callback_SST_func, callback_SSS_S_func, lib_lisa_rcv
# from lisa.lisa_configuration import MAX_ODAS_SOURCES, N_BITS_INCOME_STREAM, CHUNK_SIZE_INCOME_STREAM, \
#     SAMPLE_RATE_INCOME_STREAM, BYTES_PER_SAMPLE_INCOME_STREAM
from lisa.lisa_configuration import config

MAX_ODAS_SOURCES = int(config['INCOME_STREAM']['n_sources'])
N_BITS_INCOME_STREAM = int(config['INCOME_STREAM']['n_bits'])
CHUNK_SIZE_INCOME_STREAM = int(config['INCOME_STREAM']['chunk_size'])
SAMPLE_RATE_INCOME_STREAM = int(config['INCOME_STREAM']['sample_rate'])
ODAS_EXE = config['ODAS']['odas_exe']
DEFAULT_ODAS_CONFIG = config['ODAS']['odas_config']
BYTES_PER_SAMPLE_INCOME_STREAM = N_BITS_INCOME_STREAM // 8

_LOGGER = logging.getLogger("rhasspy-lisa-odas-hermes")

# Set aggressiveness of VAD:
# an integer between 0 and 3, 0 being the least aggressive about filtering out non-speech, 3 the most aggressive.
DEFAULT_VAD_AGGRESSIVENESS = 3

# to be parametrized
MEDIAN_WEIGHTS = [1/4, 1/2, 1/4]  # Set to none to skip, apply a median filter
ACTIVITY_THRESHOLD = 0.1  # the min threshold for a source to being considered as active (override a bit odas behavior)

# Params for collecting queue from ODAS callbacks
MAX_QUEUE_SIZE = 10
SLEEP_BEFORE_START_CLIENT = 0.5 # sec sync between odas tx/rx. The rx (server) is spawned first and then the tx
# TODO: change the MULTI_THREAD in something like DEMULTIPLEXER . THis means one source is selected (e.g latest it)
# and streamed, reagardless the number of channel
# MULTI_THREAD = False  # TODO: This influence also how the raw data  streaming are collected
# GLOBAL VARIABLES USED TO SHARE INFORMATION AMONG THREADS
SSL_queue = [deque(maxlen=len(MEDIAN_WEIGHTS)) for _q in range(MAX_ODAS_SOURCES)]
SST_queue = [deque(maxlen=len(MEDIAN_WEIGHTS)) for _q in range(MAX_ODAS_SOURCES)]
SSL_latest = [None for _q in range(MAX_ODAS_SOURCES)]
SST_latest = [None for _q in range(MAX_ODAS_SOURCES)]
SSS_queue = None # Decided at runtime


##########################
## callback definitions ##
##########################
@callback_SSL_func
def callback_SSL(pSSL_struct):
    ssl_str = pSSL_struct[0]
    # print('callback_SSL')
    # msg = ["+++ Python SSL Struct ts={}".format(ssl_str.timestamp)]
    # TODO: use timestamp for checking insertion??
    for i in range(0, MAX_ODAS_SOURCES):
        try:
            if MEDIAN_WEIGHTS is None:
                # Calculate the weighted median filter
                SSL_latest[i] = (ssl_str.timestamp / 100.0, deepcopy(ssl_str.src[i]))
            else:
                # Calculate the weighted median filter
                SSL_queue[i].append((ssl_str.timestamp / 100.0, deepcopy(ssl_str.src[i])))
                x = y = z = E = 0.0
                ts = ssl_str.timestamp / 100.0
                for ii in range(len(SSL_queue[i])):
                    w = MEDIAN_WEIGHTS[ii]
                    # ts = ts + SSL_queue[i][ii][0] * w
                    x = x + SSL_queue[i][ii][1].x * w
                    y = y + SSL_queue[i][ii][1].y * w
                    z = z + SSL_queue[i][ii][1].z * w
                    E = E + SSL_queue[i][ii][1].E * w
                SSL_latest[i] = (ts, SSL_src_struct(x=x, y=y, z=z, E=E))
            # print("SSL_latest[{}]: {}".format(i, SSL_latest[i]))
        except Full:
            _LOGGER.warning("SSL queue is Full, this should not happen with deque")
            pass


@callback_SST_func
def callback_SST(pSST_struct):
    # print('callback_SST')
    sst_str = pSST_struct[0]
    for i in range(0, MAX_ODAS_SOURCES):
        try:
            if MEDIAN_WEIGHTS is None:
                # Calculate the weighted median filter
                SST_latest[i] = (sst_str.timestamp / 100.0, deepcopy(sst_str.src[i]))
            else:
                # Calculate the weighted median filter
                SST_queue[i].append((sst_str.timestamp / 100.0, deepcopy(sst_str.src[i])))
                x = y = z = activity = 0.0
                ts = sst_str.timestamp / 100.0
                id = []
                for ii in range(len(SST_queue[i])):
                    w = MEDIAN_WEIGHTS[ii]
                    # ts = ts + SST_queue[i][ii][0] * w
                    x = x + SST_queue[i][ii][1].x * w
                    y = y + SST_queue[i][ii][1].y * w
                    z = z + SST_queue[i][ii][1].z * w
                    activity = activity + SST_queue[i][ii][1].activity * w
                    id.append(SST_queue[i][ii][1].id)
                id = np.argmax(np.bincount(id))  # The more probable
                SST_latest[i] = (ts, SST_src_struct(x=x,y=y,z=z,activity=activity, id=id, tag=SST_queue[i][-1][1].tag)) # For tag take the latest inserted
            # print("[{}]-SST_latest[{}]: {}".format(SST_latest[i][0], i, SST_latest[i][1]))
        except Full:
            _LOGGER.warning("SST queue is Full, this should not happen with deque")
            pass


@callback_SSS_S_func
def callback_SSS_S(n_bytes, x):
    """"
    Called by the relative odas switcher stream, save in the proper SSS_queue[] the received data.
    """
    # print('callback_SSS_S')
    # print("+++ Python SSS_S {} bytes in x={}".format(n_bytes, x))
    shp = (n_bytes // BYTES_PER_SAMPLE_INCOME_STREAM // MAX_ODAS_SOURCES, MAX_ODAS_SOURCES) # shape
    n_frames = shp[0] // CHUNK_SIZE_INCOME_STREAM  # I assume shp[0] is always a multiple integer, which in my understanding seems to be the case with odas
    buf = np.ctypeslib.as_array(x, shape=shp)
    # if MULTI_THREAD:
    assert SSS_queue is not None
    if isinstance(SSS_queue, list): # It means we want to demux the signal
        for i in range(0, MAX_ODAS_SOURCES):
            try:
                for _fr in range(n_frames):  # there could be more than one frame so put in queue with the expected length
                    _idl = _fr * CHUNK_SIZE_INCOME_STREAM
                    _idh = _idl + CHUNK_SIZE_INCOME_STREAM
                    _ch_buf = buf[_idl:_idh, i]
                    # print("extract buffer source {} - frame {}. 3 samples  {} ...".format(i, _fr, _ch_buf[0:3]))
                    SSS_queue[i].put_nowait(
                        _ch_buf)  # eventually_ch_buf this has to be transformed in bytes or store as a byte IO?
                # manage full queue is required?
            except Full:
                _LOGGER.warning("SSS_S receiving Queue_" + str(i) + " is Full, skipping frame (TODO: lost for now, change in deque!)")
                # do nothing for now, perhaps extract the first to make space? Kind of circular queue behavior.....
                pass
    else:
        try:
            SSS_queue.put_nowait(buf)
        except Full:
            _LOGGER.warning("SSS_S receiving Queue is Full, skipping frame (TODO: lost for now, change in deque!)")
            # do nothing for now, perhaps extract the first to make space? Kind of circular queue behavior.....
            pass


# A shared counter for higher id policy
class _HigherID(object):
    def __init__(self, value=0):
        # RawValue because we don't need it to create a Lock:
        self.val = RawValue('i', value)
        self.lock = Lock()

    def increment(self):
        with self.lock:
            self.val.value += 1

    @property
    def value(self):
        with self.lock:
            return self.val.value


    def set_value(self, value):
        assert isinstance(value, int), "Wrong type: " + str(value.__class__)
        with self.lock:
            self.val.value = value


###################
## Hermes Client ##
###################
class LisaHermesMqtt(HermesClient):
    """Hermes MQTT server for Rhasspy Lisa ODAS input using external lib."""

    def __init__(
        self,
        client,
        sample_rate: int = SAMPLE_RATE_INCOME_STREAM,
        sample_width: int = BYTES_PER_SAMPLE_INCOME_STREAM,
        channels: int = MAX_ODAS_SOURCES,
        device_index: typing.Optional[int] = None,
        chunk_size: int = CHUNK_SIZE_INCOME_STREAM, #,2048,
        site_ids: typing.Optional[typing.List[str]] = None,
        output_site_id: typing.Optional[str] = None,
        udp_audio_host: str = "127.0.0.1",
        udp_audio_port: typing.Optional[int] = None,
        vad_mode: int = DEFAULT_VAD_AGGRESSIVENESS,
        demux: bool = False,
        odas_config: str = DEFAULT_ODAS_CONFIG
    ):
        assert 0 < channels <= MAX_ODAS_SOURCES, "Invalid number of channels {}, max is {}".format(channels,
                                                                                                   MAX_ODAS_SOURCES)
        super().__init__(
            "rhasspy-lisa-odas-hermes",
            client,
            # TODO: mmm is it needed
            sample_rate=sample_rate,
            sample_width=sample_width,
            channels=channels,
            site_ids=site_ids,
        )
        global SSS_queue
        if demux:
            SSS_queue = [Queue(maxsize=MAX_QUEUE_SIZE) for _q in range(MAX_ODAS_SOURCES)]
        else:
            SSS_queue = Queue(maxsize=MAX_QUEUE_SIZE)
        self.subscribe(AudioGetDevices, SummaryToggleOn, SummaryToggleOff)

        self.sample_rate = sample_rate  # incoming stream
        self.sample_width = sample_width # ODAS
        if demux:
            assert channels == 1, 'In multiplex mode only one channel is steamed, received channels=' + str(channels)
            self.channels = 1
        else:
            self.channels = channels
        self.device_index = device_index
        self.chunk_size = chunk_size
        self.frames_per_buffer = chunk_size // sample_width
        self.output_site_id = output_site_id or self.site_id
        self.demux = demux
        self.odas_config = odas_config

        self.udp_audio_host = udp_audio_host
        self.udp_audio_port = udp_audio_port
        self.udp_output = False
        self.udp_socket: typing.Optional[socket.socket] = None

        self.chunk_queue: Queue = Queue()

        # Send audio summaries
        self.enable_summary = False
        self.vad: typing.Optional[webrtcvad.Vad] = None
        self.vad_mode = vad_mode
        self.vad_audio_data = bytes()
        self.vad_chunk_size: int = 960  # 30ms

        # Frames to skip between audio summaries
        self.summary_skip_frames = 5
        self.summary_frames_left = self.summary_skip_frames

        # Register callbacks for ODAS streaming
        lib_lisa_rcv.register_callback_SST(callback_SST)
        lib_lisa_rcv.register_callback_SSL(callback_SSL)
        lib_lisa_rcv.register_callback_SSS_S(callback_SSS_S)

        # Start threads
        self._exit_requested = False  # A flag to check if an exit is necessary
        if self.udp_audio_port is not None:
            self.udp_output = True
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            _LOGGER.debug("Audio will also be sent to UDP %s:%s", self.udp_audio_host, self.udp_audio_port,)
            self.subscribe(AsrStartListening, AsrStopListening)
        threading.Thread(target=self._thread_start_odas_switcher,  daemon=True).start()
        threading.Thread(target=self.publish_chunks, daemon=True).start()
        threading.Thread(target=self.record, daemon=True).start()

    @property
    def exit_request(self):
        _LOGGER.debug("Exit requested")
        self._exit_requested = True

    def _thread_start_odas_switcher(self):
        def _delayed_odas_client():
            sleep(SLEEP_BEFORE_START_CLIENT)
            p = Popen([ODAS_EXE, '-c', self.odas_config])

        while not self._exit_requested:
            threading.Thread(target=_delayed_odas_client, daemon=True).start()
            retval = lib_lisa_rcv.main_loop()
            # TODO: some time the odas subsystem crash, should be re-spawned here
            print("Exit thread odas loop with {}".format(retval))

    # -------------------------------------------------------------------------
    def record(self):
        """Record audio from ODAS receiver."""
        _HIGHER_ID = _HigherID()

        def _get_postion_message(source_id):
            return {"SST": SST_latest[source_id], "SSL": SSL_latest[source_id]}

        def _print_localization(n, position, audio_chunk):
            if position['SST'] is not None and (
                    len(position['SST'][1].tag) or position['SST'][1].activity > ACTIVITY_THRESHOLD):
                # print(position['SST'][1].tag)
                # print("[{}]-SST_latest_".format(position['SST'][0], _n,))
                #  position['SST'][1].tag,
                #  position['SST'][1].activity))

                print("[{}]-SST_latest_{}-id_{}: {} {}".format(position['SST'][0], n,
                                                               position['SST'][1].id,
                                                               position['SST'][1].tag,
                                                               position['SST'][1].activity))
                # print(str(audio_chunk) + '\n---------------------')

        def _acquire_streaming_id(position, higher_id):
            if position['SST'] is not None and (len(position['SST'][1].tag) or position['SST'][1].activity > ACTIVITY_THRESHOLD):
                if position['SST'][1].id >= higher_id.value:
                    higher_id.set_value(position['SST'][1].id )
                    # print(position['SST'][1].id , higher_id.value)
                    return True
                else:
                    return False
            else:
                return False

        # Only for demux operations, every thread listen to one channel
        def _source_listening(source_id, higher_id):
            _LOGGER.debug("Recording audio {}".format(source_id))
            try:
                while not self._exit_requested:
                    audio_chunk = SSS_queue[source_id].get().tobytes()
                    self.raw_queue.task_done()  # sign the last job as done
                    position = _get_postion_message(source_id)  # metadata with position. to add a subscriber
                    if audio_chunk is None:
                        raise Exception("Received buffer none for source_id_{}".format(
                            source_id))  # stop processing if the main thread is done. this means data are not anymore a
                    if _acquire_streaming_id(position, higher_id):  # source_id >= higher_id.value():
                        self.chunk_queue.put(audio_chunk)  # + position?
                        _print_localization(str(source_id) + '_Acquired Priority', position, audio_chunk)
                    else:
                        _print_localization(str(source_id) + '_Discarded(Higher is ' + str(higher_id.value) +
                                            ')', position, audio_chunk)
            except Exception as e:
                print("_source_listening(" + str(source_id) + "), exception: " + str(e))
            finally:
                pass
            # TODO: Profiling?
            print("+-+-+-+-+-+-+-+-+-+-+ Stop recording audio {}, exit thread".format(source_id))
            _LOGGER.debug("Stop recording audio {}, exit thread".format(source_id))

        try:
            # Start Thread
            listener_threads = []
            try:
                # I need to retrieve ALL available channels and simply discard (this looks not very efficient though)
                if self.demux:
                    for _n in range(MAX_ODAS_SOURCES):  # What about range(channels)? TODO: channels < MAX_ODAS_SOURCES in init
                        listener_threads.append(threading.Thread(target=_source_listening, args=(_n,_HIGHER_ID,), daemon=True))
                        listener_threads[-1].start()
                        # listener_threads.append(_th)
                    while not self._exit_requested:
                        sleep(0.5)
                        # TODO: should I  do some check for exit?
                else:
                    loop = 0
                    assert N_BITS_INCOME_STREAM == 16, \
                        "Unsupported format, only 16 bits are accepted (this condition should be removed in future with a local cast)"
                    while not self._exit_requested:
                        loop += 1
                        audio_chunk = SSS_queue.get()
                        # prints are for debug
                        # print("audio_chunk_shape=" + str(audio_chunk.shape) + "\n" +str(audio_chunk)[:100] )
                        out_chunk = np.zeros(shape=(audio_chunk.shape[0], self.channels), dtype=np.int16)
                        for _n in range(MAX_ODAS_SOURCES):
                            if _n < self.channels:
                                out_chunk[:, _n] = audio_chunk[:, _n]
                        # print("out_chunk_shape=" + str(out_chunk.shape) + "\n" + str(out_chunk)[:100] +
                        # "\n--------------------------------------------------------\n")
                        self.chunk_queue.put(out_chunk.tobytes())

            except Exception as e:
                print("record, exception: " + str(e))
                _LOGGER.debug("Recording got an exception: {}".format(e))
            finally:
                if self.demux:
                    for _n in range(MAX_ODAS_SOURCES):
                        _LOGGER.debug("Recording shutdown, wait for exit acquistion thread {}".format(_n))
                        listener_threads[_n].join()
                        _LOGGER.debug("Thread {} exit done".format(_n))
                    else:
                        _LOGGER.debug("Recording shutdown")
        except Exception as e:
            _LOGGER.exception("record")
            self.publish(
                AudioRecordError(
                    error=str(e),
                    context=f"Device index: {self.device_index}",
                    site_id=self.output_site_id,
                )
            )

    def publish_chunks(self):
        """Publish audio chunks to MQTT or UDP."""
        try:
            udp_dest = (self.udp_audio_host, self.udp_audio_port)

            while not self._exit_requested:
                chunk = self.chunk_queue.get()
                if chunk:
                    # MQTT output
                    with io.BytesIO() as wav_buffer:
                        wav_file: wave.Wave_write = wave.open(wav_buffer, "wb")
                        with wav_file:
                            wav_file.setframerate(self.sample_rate)
                            wav_file.setsampwidth(self.sample_width)
                            wav_file.setnchannels(self.channels)
                            wav_file.writeframes(chunk)

                        wav_bytes = wav_buffer.getvalue()

                        if self.udp_output:
                            # UDP output
                            self.udp_socket.sendto(wav_bytes, udp_dest)
                        else:
                            # Publish to output site_id
                            self.publish(
                                AudioFrame(wav_bytes=wav_bytes),
                                site_id=self.output_site_id,
                            )

                    if self.enable_summary:
                        self.summary_frames_left -= 1
                        if self.summary_frames_left > 0:
                            continue

                        self.summary_frames_left = self.summary_skip_frames
                        if not self.vad:
                            # Create voice activity detector
                            self.vad = webrtcvad.Vad()
                            self.vad.set_mode(self.vad_mode)

                        # webrtcvad needs 16-bit 16Khz mono
                        self.vad_audio_data += self.maybe_convert_wav(
                            wav_bytes, sample_rate=16000, sample_width=2, channels=1
                        )

                        is_speech = False

                        # Process in chunks of 30ms for webrtcvad
                        while len(self.vad_audio_data) >= self.vad_chunk_size:
                            vad_chunk = self.vad_audio_data[: self.vad_chunk_size]
                            self.vad_audio_data = self.vad_audio_data[
                                self.vad_chunk_size :
                            ]

                            # Speech in any chunk counts as speech
                            is_speech = is_speech or self.vad.is_speech(
                                vad_chunk, 16000
                            )

                        # Publish audio summary
                        self.publish(
                            AudioSummary(
                                debiased_energy=AudioSummary.get_debiased_energy(chunk),
                                is_speech=is_speech,
                            ),
                            site_id=self.output_site_id,
                        )

        except Exception as e:
            _LOGGER.exception("publish_chunks")
            self.publish(
                AudioRecordError(
                    error=str(e), context="publish_chunks", site_id=self.site_id
                )
            )

    async def handle_get_devices(
        self, get_devices: AudioGetDevices
    ) -> typing.AsyncIterable[typing.Union[AudioDevices, AudioRecordError]]:
        """Get available microphones and optionally test them."""
        if get_devices.modes and (AudioDeviceMode.INPUT not in get_devices.modes):
            _LOGGER.debug("Not a request for input devices")
            return
        # TODO: set this with the connection from odas if it is working
        working = True
        devices: typing.List[AudioDevice] = []
        devices.append(
            AudioDevice(
                mode=AudioDeviceMode.INPUT,
                id=str(0),
                name="ODAS_LISA Receiver",
                description="A demultiplexer for receive multiple channel",
                working=working,
            )
        )

        yield AudioDevices(
            devices=devices, id=get_devices.id, site_id=get_devices.site_id
        )

    async def on_message_blocking(
        self,
        message: Message,
        site_id: typing.Optional[str] = None,
        session_id: typing.Optional[str] = None,
        topic: typing.Optional[str] = None,
    ) -> GeneratorType:
        """Received message from MQTT broker."""
        if isinstance(message, AudioGetDevices):
            async for device_result in self.handle_get_devices(message):
                yield device_result
        elif isinstance(message, AsrStartListening):
            if self.udp_audio_port is not None:
                self.udp_output = False
                _LOGGER.debug("Disable UDP output")
        elif isinstance(message, AsrStopListening):
            if self.udp_audio_port is not None:
                self.udp_output = True
                _LOGGER.debug("Enable UDP output")
        elif isinstance(message, SummaryToggleOn):
            self.enable_summary = True
            _LOGGER.debug("Enable audio summaries")
        elif isinstance(message, SummaryToggleOff):
            self.enable_summary = False
            _LOGGER.debug("Disable audio summaries")
        else:
            _LOGGER.warning("Unexpected message: %s", message)
