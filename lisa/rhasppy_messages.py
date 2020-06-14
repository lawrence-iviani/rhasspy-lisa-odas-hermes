
"""MQTT messages used within the Lisa Hermes Module"""
from dataclasses import dataclass
import typing

from rhasspyhermes.base import Message


@dataclass
class SSL_src_msg(Message):
    """Tell a possible source is localized
    Attributes
    ----------
    site_id: str = "default"
        The site that must be listened too
    session_id: Optional[str] = None
        An optional session id if there is a related session

    timestamp: float
        the value in seconds from latest ODAS beamforming start
    channel: int
        ODAS input channel (0-index) (0..MAX_ODAS_SOURCE)
    E: float
        Energy source
    x: float
        x DOA
    y: float
        y axis DOA
    z: float
        z axis DOA
    """

    site_id: str = "default"
    session_id: typing.Optional[str] = None

    # ------------
    # Rhasspy only
    # ------------

    timestamp: float = 0.0
    E: float = 0.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    channel: int = 0

    @classmethod
    def topic(cls, **kwargs) -> str:
        """Get MQTT topic for this message type."""
        return "lisa/ssl/source"


@dataclass
class SST_src_msg(Message):
    """Tell the source is tracked
    Attributes
    ----------
    site_id: str = "default"
        The site that must be listened too
    session_id: Optional[str] = None
        An optional session id if there is a related session

    timestamp: float
        the value in seconds from latest ODAS beamforming start
    channel: int
        ODAS input channel (0-index) (0..MAX_ODAS_SOURCE)
    id: int
        The tracked source with ID (is an integer assigned by ODAS to identify a tracked source)
    activity: float
        Energy source
    tag: str
        Source Type (limited, depending on ODAS)
    x: float
        x DOA
    y: float
        y axis DOA
    z: float
        z axis DOA
    """

    # unsigned int id;
    # char tag[SST_TAG_LEN]; // TODO, VERIFY THIS IS NOT BUGGY, NO IDEA WHAT IS THE MAX LEN!!!
    # float x;
    # float y;
    # float z;
    # float activity;

    site_id: str = "default"
    session_id: typing.Optional[str] = None

    # ------------
    # Rhasspy only
    # ------------

    timestamp: float = 0.0
    id: int = 0
    activity: float = 0.0
    tag: str = ''
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    channel: int = 0

    @classmethod
    def topic(cls, **kwargs) -> str:
        """Get MQTT topic for this message type."""
        return "lisa/sst/source"


