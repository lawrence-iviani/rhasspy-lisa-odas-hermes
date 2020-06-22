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
from lisa.lisa_configuration import config

MAX_ODAS_SOURCES = int(config['INCOME_STREAM']['n_sources'])
N_BITS_INCOME_STREAM = int(config['INCOME_STREAM']['n_bits'])
CHUNK_SIZE_INCOME_STREAM = int(config['INCOME_STREAM']['chunk_size'])
SAMPLE_RATE_INCOME_STREAM = int(config['INCOME_STREAM']['sample_rate'])
ODAS_EXE = config['ODAS']['odas_exe']
DEFAULT_ODAS_CONFIG = config['ODAS']['odas_config']
BYTES_PER_SAMPLE_INCOME_STREAM = N_BITS_INCOME_STREAM // 8
ODAS_RCV_CONFIG_FILE = config['ODAS']['odas_rcv_config']

_LOGGER = logging.getLogger("rhasspy-lisa-odas-hermes")

# Set aggressiveness of VAD:
# an integer between 0 and 3, 0 being the least aggressive about filtering out non-speech, 3 the most aggressive.
DEFAULT_VAD_AGGRESSIVENESS = 3

# TODO: to be parametrized
MEDIAN_WEIGHTS = [1/4, 1/2, 1/4]  # Set to none to skip, apply a median filter
# BETWEEN 0..1 a little bit magic number actually
ACTIVITY_THRESHOLD = 0.01  #  the min threshold for a source to being considered as tracked active (override a bit odas behavior)
ENERGY_THRESHOLD = 0.3  # The energy to be considered a potential localized source
REFRESH_RATE = 10  # 20  # in hertz 10Hz -> 100ms, 20Hz -> 50ms, ... interval btw messages

# Params for collecting queue from ODAS callbacks
MAX_QUEUE_SIZE = 10
SLEEP_BEFORE_START_CLIENT = 0.5  # sec sync between odas tx/rx. The rx (server) is spawned first and then the tx
# TODO: change the MULTI_THREAD in something like DEMULTIPLEXER . THis means one source is selected (e.g latest it)
# and streamed, reagardless the number of channel
# MULTI_THREAD = False  # TODO: This influence also how the raw data  streaming are collected
# GLOBAL VARIABLES USED TO SHARE INFORMATION AMONG THREADS
SSL_queue = [deque(maxlen=len(MEDIAN_WEIGHTS)) for _q in range(MAX_ODAS_SOURCES)]
SST_queue = [deque(maxlen=len(MEDIAN_WEIGHTS)) for _q in range(MAX_ODAS_SOURCES)]
SSL_latest = [None for _q in range(MAX_ODAS_SOURCES)]
SST_latest = [None for _q in range(MAX_ODAS_SOURCES)]
SSS_queue = None  # Decided at runtime

# other options
DEBUG_LOCALIZATION = False  # a number of debug prints with the


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
        odas_config: str = DEFAULT_ODAS_CONFIG,
        odas_rcv_config: str = ODAS_RCV_CONFIG_FILE
    ):
        assert 0 < channels <= MAX_ODAS_SOURCES, "Invalid number of channels {}, max is {}".format(channels,
                                                                                                   MAX_ODAS_SOURCES)
        if demux:
            assert channels == 1, 'In multiplex mode only one channel is steamed, received channels=' + str(channels)
            self.channels = 1
        else:
            self.channels = channels
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
        self.sample_width = sample_width  # ODAS

        self.device_index = device_index
        self.chunk_size = chunk_size
        self.frames_per_buffer = chunk_size // sample_width
        self.output_site_id = output_site_id or self.site_id
        self.demux = demux
        self.odas_config = odas_config
        self.odas_rcv_config = odas_rcv_config

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
        _LOGGER.info("Firing threads for...")
        print("+-+-+-+-+-+-+-+-+ ready for _thread_start_odas_switcher", _LOGGER.info)
        threading.Thread(target=self._thread_start_odas_switcher,  daemon=True).start()
        threading.Thread(target=self.publish_chunks, daemon=True).start()
        threading.Thread(target=self.record, daemon=True).start()
        threading.Thread(target=self.publish_odas, daemon=True).start()

    # HERE something is wrong...
    @property
    def exit_request(self):
        _LOGGER.debug("Exit requested")
        return self._exit_requested

    @exit_request.setter
    def exit_request(self, value):
        self._exit_requested = value

    def _thread_start_odas_switcher(self):
        def _delayed_odas_client():
            sleep(SLEEP_BEFORE_START_CLIENT)
            cmd = [ODAS_EXE, '-c', self.odas_config]
            p = Popen(cmd)
            _LOGGER.info(str(cmd) + " exit, " + str(p))

        while not self._exit_requested:
            _LOGGER.info("Starting  thread odas loop")
            threading.Thread(target=_delayed_odas_client, daemon=True).start()
            retval = lib_lisa_rcv.start_main_loop(self.odas_rcv_config.encode('utf-8'))
            # TODO: some time the odas subsystem crash, should be re-spawned here
            # note: crashed, but didnt exit. So probably is necessary a watch dog for p if exit?
            if not self._exit_requested:
                _LOGGER.error('TODO: this should not happen. Furthermore the thread is relaunched but with no effect.. Sleep? sync problem? who dies?')
            _LOGGER.info("Exit thread odas loop with {}".format(retval))

    # -------------------------------------------------------------------------
    def _is_source_localized(self, ssl_src):
        """
        :param ssl_src: a lisa.lisa_switcher_bindings.SSL_src_struct
        :return: True if Energy > ENERGY_THRESHOLD
        """
        if ssl_src is None:
            return False
        return ssl_src[1].E > ENERGY_THRESHOLD

    def _is_source_tracked(self, sst_src):
        """
        :param sst_src: a lisa.lisa_switcher_bindings.SST_src_struct
        :return: True if tag is dynamic (should be removed?) and activity > ACTIVITY_THRESHOLD
        """
        if sst_src is None:
            return False
        return len(sst_src[1].tag) or sst_src[1].activity > ACTIVITY_THRESHOLD

    def record(self):
        """Record audio from ODAS receiver."""
        _HIGHER_ID = _HigherID()

        def _get_postion_message(source_id=None):
            if source_id is None:
                return {"SST": SST_latest, "SSL": SSL_latest}
            else:
                return {"SST": SST_latest[source_id], "SSL": SSL_latest[source_id]}

        def _print_localization(n, position, audio_chunk):
            """Debug only purpose"""
            PRINT_AUDIO_CHUNK = True
            def _print(n_id, pos, aud_cnk = None):
                print("[{}]-SST_latest_{}-id_{}: {} {} - Audio Chunk len={}".format(pos[0], n_id,
                                                               pos[1].id,
                                                               pos[1].tag,
                                                               pos[1].activity, len(aud_cnk)))
                if PRINT_AUDIO_CHUNK:
                    print('{}...{}\n---------------------'.format(aud_cnk[:30], aud_cnk[-10:]))
            if isinstance(position, tuple):
                p = position
            elif position['SST'] is not None:
                p = position['SST']
            if len(p[1].tag) or p[1].activity > ACTIVITY_THRESHOLD:
                _print(n, p, audio_chunk)

        def _acquire_streaming_id(position, higher_id):
            """Determine the stream with the higher id (latest)
                TODO: here could stay the speaker identification process? How?"""
            if position['SST'] is not None and self._is_source_tracked(position['SST']): # position['SST'] is not None and (len(position['SST'][1].tag) or position['SST'][1].activity > ACTIVITY_THRESHOLD):
                if position['SST'][1].id >= _HIGHER_ID.value:
                    _HIGHER_ID.set_value(position['SST'][1].id )
                    # print(position['SST'][1].id , higher_id.value)
                    return True
                else:
                    return False
            else:
                return False

        def _source_listening(source_id, higher_id):
            """Only for demux operations, used as a thread listen to one channel and the source with a certain policy
            is """
            _LOGGER.debug("Recording audio {}".format(source_id))
            try:
                while not self._exit_requested:
                    audio_chunk = SSS_queue[source_id].get().tobytes()
                    SSS_queue[source_id].task_done()  # sign the last job as done
                    position = _get_postion_message(source_id)  # metadata with position. to add a subscriber
                    if audio_chunk is None:
                        raise Exception("Received buffer none for source_id_{}".format(
                            source_id))  # stop processing if the main thread is done. this means data are not anymore a
                    if _acquire_streaming_id(position, _HIGHER_ID):  # source_id >= higher_id.value():
                        if self._is_source_tracked(position['SST']):
                            self.chunk_queue.put(audio_chunk)
                            if DEBUG_LOCALIZATION:
                                _print_localization(str(source_id) + '_Acquired Priority', position, audio_chunk)
                    else:
                        if DEBUG_LOCALIZATION:
                            _print_localization(str(source_id) + '_Discarded(Higher is ' + str(higher_id.value) +
                                                ')', position, audio_chunk)
            except Exception as e:
                _LOGGER.warning("Got an error listening source {} -> {}".format(source_id, e))
            finally:
                pass
            # TODO: Profiling?
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
                    while not self._exit_requested:
                        sleep(1.0/REFRESH_RATE)  # Refresh rate
                        # check and in case reset the max id (e.g. a higher id source terminated)
                        _max_ID = -1
                        positions = _get_postion_message()
                        for _n in range(MAX_ODAS_SOURCES):
                            if self._is_source_tracked(positions['SST'][_n]):
                                _max_ID = max(positions['SST'][_n][1].id, _max_ID)
                        if _HIGHER_ID.value > _max_ID:
                            # reset the max id with the actual higher value
                            if DEBUG_LOCALIZATION:
                                print("Reset max id from {} to {}".format(_HIGHER_ID.value, _max_ID))
                            _HIGHER_ID.set_value(_max_ID)
                else:
                    loop = 0
                    assert N_BITS_INCOME_STREAM == 16, \
                        "Unsupported format, only 16 bits are accepted (this condition should be removed in future with a local cast)"
                    while not self._exit_requested:
                        loop += 1
                        audio_chunk = SSS_queue.get()  # It will wait until data are available
                        out_chunk = np.zeros(shape=(audio_chunk.shape[0], self.channels), dtype=np.int16)
                        positions = _get_postion_message()  # metadata with position. to add a subscriber
                        for _n in range(MAX_ODAS_SOURCES):
                            if _n < self.channels:
                                # the channel is added only if the activity threshold is above a certain level
                                if self._is_source_tracked(positions['SST'][_n]): #   len(positions['SST'][_n][1].tag) or positions['SST'][_n][1].activity > ACTIVITY_THRESHOLD:
                                    out_chunk[:, _n] = audio_chunk[:, _n]
                                    if DEBUG_LOCALIZATION:
                                        _print_localization('CH_' + str(_n), positions['SST'][_n], out_chunk[:, _n])
                                else:
                                    if DEBUG_LOCALIZATION:
                                        print("CH_" + str(_n) + " Discarded, activity=" + str(positions['SST'][_n][1].activity))
                        self.chunk_queue.put(out_chunk.tobytes())

            except Exception as e:
                _LOGGER.warning("Got an error recording -> {}".format(e))
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

    def publish_odas(self):
        """Publish the latest ."""

        from lisa.rhasppy_messages import SSL_src_msg, SST_src_msg
        try:
            while not self._exit_requested:
                for _n in range(MAX_ODAS_SOURCES):
                    _ssl_latest = SSL_latest[_n]
                    if self._is_source_localized(_ssl_latest):
                        _ts = _ssl_latest[0]
                        _ssl_latest = _ssl_latest[1]
                        _publish = SSL_src_msg(timestamp=_ts,
                                               channel=_n,
                                               E=_ssl_latest.E,
                                               x=_ssl_latest.x,
                                               y=_ssl_latest.y,
                                               z=_ssl_latest.z)
                        self.publish(
                            _publish,
                            site_id=self.output_site_id,
                        )
                        # print('Published SSL', _publish.topic(), _publish)
                    _sst_latest = SST_latest[_n]
                    if self._is_source_tracked(_sst_latest):
                        _ts = _sst_latest[0]
                        _sst_latest = _sst_latest[1]
                        _publish = SST_src_msg(timestamp=_ts,
                                               channel=_n,
                                               activity=_sst_latest.activity,
                                               x=_sst_latest.x,
                                               y=_sst_latest.y,
                                               z=_sst_latest.z,
                                               id=_sst_latest.id)
                        self.publish(
                            _publish,
                            site_id=self.output_site_id,
                        )
                        # print('Published SST', _publish.topic(), _publish)
                sleep(1.0/REFRESH_RATE)

        except Exception as e:
            _LOGGER.exception("publish_odas: " + str(e))
            self.publish(
                AudioRecordError(
                    error=str(e), context="publish_chunks", site_id=self.site_id
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
                        # TODO: would be possible to split here if demux is not selected? this would avoid resampling,
                        # which is called continuously. (uncomment this code). With the switch --demux a proper channel
                        # is produced
                        # with io.BytesIO(wav_bytes) as wav_io:
                        #     with wave.open(wav_io, "rb") as wav_file:
                        #         if (wav_file.getframerate() != 16000) or \
                        #                 (wav_file.getsampwidth() != 2) or \
                        #                 (wav_file.getnchannels() != 1):
                        #             print("Need Resample: sr={}, width={}, n_ch={}".format(wav_file.getframerate(),
                        #                                                                    wav_file.getsampwidth(),
                        #                                                                    wav_file.getnchannels()))
                        #         else:
                        #             print("No resample")
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
