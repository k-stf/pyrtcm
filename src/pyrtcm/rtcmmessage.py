"""
Main RTCM Message Protocol Class.

Created on 14 Feb 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

import pyrtcm.exceptions as rte
import pyrtcm.rtcmtypes_get as rtg
from pyrtcm.rtcmhelpers import (
    att2idx,
    att2name,
    attsiz,
    bits2val,
    cell2prn,
    crc2bytes,
    escapeall,
    len2bytes,
    sat2prn,
)
from pyrtcm.rtcmtypes_core import (
    ATT_NCELL,
    ATT_NSAT,
    NCELL,
    NHARMCOEFFC,
    NHARMCOEFFS,
    NSAT,
    NSIG,
    RTCM_DATA_FIELDS,
    RTCM_HDR,
    RTCM_MSGIDS,
)

BOOL = "B"


class RTCMMessage:
    """RTCM Message Class."""

    def __init__(self, payload: bytes = None, scaling: bool = True, labelmsm: int = 1):
        """Constructor.

        :param bytes payload: message payload (mandatory)
        :param bool scaling: whether to apply attribute scaling True/False (True)
        :param int labelmsm: MSM NSAT and NCELL attribute label (0 = none, 1 = RINEX, 2 = freq)
        :raises: RTCMMessageError
        """

        # object is mutable during initialisation only
        super().__setattr__("_immutable", False)

        self._payload = payload
        if self._payload is None:
            raise rte.RTCMMessageError("Payload must be specified")
        self._payblen = len(self._payload) * 8  # length of payload in bits
        self._scaling = scaling
        self._labelmsm = labelmsm
        self._unknown = False
        self._do_attributes()

        self._immutable = True  # once initialised, object is immutable

    def _do_attributes(self):
        """
        Populate RTCMMessage attributes from payload.

        :raises: RTCMTypeError
        """

        offset = 0  # payload offset in bits
        index = []  # array of (nested) group indices

        try:
            # get payload definition dict for this message identity
            pdict = self._get_dict()
            if pdict is None:  # unknown (or not yet implemented) message identity
                self._do_unknown()
                return
            for anam in pdict:  # process each attribute in dict
                (offset, index) = self._set_attribute(anam, pdict, offset, index)

        except Exception as err:
            raise rte.RTCMTypeError(
                (
                    f"Error processing attribute '{anam}' "
                    f"in message type {self.identity} {err}"
                )
            ) from err

    def _set_attribute(self, anam: str, pdict: dict, offset: int, index: list) -> tuple:
        """
        Recursive routine to set individual, conditional or grouped payload attributes.

        :param str anam: attribute name
        :param dict pdict: dict representing payload definition
        :param int offset: payload offset in bits
        :param list index: repeating group index array
        :return: (offset, index[])
        :rtype: tuple

        """

        atyp = pdict[anam]  # get attribute type
        if isinstance(atyp, tuple):  # attribute group
            asiz, _ = atyp
            if isinstance(asiz, tuple):  # conditional group of attributes
                (offset, index) = self._set_attribute_optional(atyp, offset, index)
            else:  # repeating group of attributes
                (offset, index) = self._set_attribute_group(atyp, offset, index)
        else:  # single attribute
            offset = self._set_attribute_single(anam, offset, index)

        return (offset, index)

    def _set_attribute_optional(self, atyp: tuple, offset: int, index: list) -> tuple:
        """
        Process conditional group of attributes - group is present if attribute value
        = specific value, otherwise absent.

        :param tuple atyp: attribute type - tuple of ((attribute name, condition), group dict)
        :param int offset: payload offset in bits
        :param list index: repeating group index array
        :return: (offset, index[])
        :rtype: tuple
        """

        (anam, con), gdict = atyp  # (attribute, condition), group dictionary
        # "+n" suffix signifies that one or more nested group indices
        # must be appended to name e.g. "DF379_01", "IDF023_03"
        # if "+" in anam:
        #     anam, nestlevel = anam.split("+")
        #     for i in range(int(nestlevel)):
        #        anam += f"_{index[i]:02d}"

        if getattr(self, anam) == con:  # if condition is met...
            # recursively process each group attribute,
            # incrementing the payload offset as we go
            for anamg in gdict:
                (offset, index) = self._set_attribute(anamg, gdict, offset, index)

        return (offset, index)

    def _set_attribute_group(self, atyp: tuple, offset: int, index: list) -> tuple:
        """
        Process (nested) group of attributes.

        :param tuple atyp: attribute group - tuple of (attr name, attribute dict)
        :param int offset: payload offset in bits
        :param list index: repeating group index array
        :return: (offset, index[])
        :rtype: tuple

        """

        anam, gdict = atyp  # attribute name, attribute dictionary
        # derive or retrieve number of items in group
        if isinstance(anam, int):  # fixed number of repeats
            gsiz = anam
        else:  # number of repeats is defined in named attribute
            # "+n" suffix signifies that one or more nested group indices
            # must be appended to name e.g. "DF379_01", "IDF023_03"
            if "+" in anam:
                anam, nestlevel = anam.split("+")
                for i in range(int(nestlevel)):
                    anam += f"_{index[i]:02d}"
            gsiz = getattr(self, anam)
            if anam == "IDF035":  # 4076_201 range is N-1
                gsiz += 1

        index.append(0)  # add a (nested) group index level
        # recursively process each group attribute,
        # incrementing the payload offset and index as we go
        for i in range(gsiz):
            index[-1] = i + 1
            for anamg in gdict:
                (offset, index) = self._set_attribute(anamg, gdict, offset, index)

        index.pop()  # remove this (nested) group index

        return (offset, index)

    def _set_attribute_single(
        self,
        anam: str,
        offset: int,
        index: list,
    ) -> int:
        """
        Set individual attribute value, applying scaling where appropriate.

        :param str anam: attribute name
        :param int offset: payload offset in bits
        :param list index: repeating group index array
        :return: offset
        :rtype: int

        """

        # pylint: disable=invalid-name

        # if attribute is part of a (nested) repeating group, suffix name with index
        anami = anam
        for i in index:  # one index for each nested level
            if i > 0:
                anami += f"_{i:02d}"

        # get value of required number of bits at current payload offset
        atyp, ares, _ = RTCM_DATA_FIELDS[anam]
        if not self._scaling:
            ares = 0
        if anam == "DF396":  # this MSM attribute has variable length
            asiz = getattr(self, NSAT) * getattr(self, NSIG)
        else:
            asiz = attsiz(atyp)
        bitfield = self._getbits(offset, asiz)
        val = bits2val(atyp, ares, bitfield)

        setattr(self, anami, val)
        offset += asiz

        # add special attributes to keep track of
        # MSM message group sizes
        # NB: This is predicated on MSM payload dictionaries
        # always having attributes DF394, DF395 and DF396
        # in that order
        if anam in ("DF394", "DF395", "DF396"):
            nbits = bin(bitfield).count("1")  # number of bits set
            if anam == "DF394":  # num of satellites in MSM message
                setattr(self, NSAT, nbits)
            elif anam == "DF395":  # num of signals in MSM message
                setattr(self, NSIG, nbits)
            elif anam == "DF396":  # num of cells in MSM message
                setattr(self, NCELL, nbits)
        # add special coefficient attributes for message 4076_201
        if anam == "IDF038":
            i = index[0]
            N = getattr(self, f"IDF037_{i:02d}") + 1
            M = getattr(self, f"IDF038_{i:02d}") + 1
            nc = int(((N + 1) * (N + 2) / 2) - ((N - M) * (N - M + 1) / 2))
            ns = int(nc - (N + 1))
            # ncs = (N + 1) * (N + 1) - (N - M) * (N - M + 1)
            # print(f"DEBUG nc {nc} ns {ns} ncs {ncs} nc+ns {nc+ns}")
            setattr(self, NHARMCOEFFC, nc)
            setattr(self, NHARMCOEFFS, ns)

        return offset

    def _getbits(self, position: int, length: int) -> int:
        """
        Get unsigned integer value of masked bits in bytes.

        :param int position: position in bitfield, from leftmost bit
        :param int length: length of masked bits
        :return: value
        :rtype: int
        """

        if position + length > self._payblen:
            raise rte.RTCMMessageError(
                f"Attribute size {length} exceeds remaining "
                + f"payload length {self._payblen - position}"
            )

        return int.from_bytes(self._payload, "big") >> (
            self._payblen - position - length
        ) & (2**length - 1)

    def _get_dict(self) -> dict:
        """
        Get payload dictionary corresponding to message identity
        (or None if message type not defined)

        :return: dictionary representing payload definition
        :rtype: dict or None
        """

        return rtg.RTCM_PAYLOADS_GET.get(self.identity, None)

    def _do_unknown(self):
        """
        Handle unknown message type.
        """

        setattr(self, "DF002", self.identity)
        self._unknown = True

    def __str__(self) -> str:
        """
        Human readable representation.

        :return: human readable representation
        :rtype: str
        """

        # if MSM message and labelmsm flag is set,
        # label NSAT and NCELL group attributes with
        # corresponding satellite PRN and signal ID (RINEX code or freq band)
        if not self._unknown:
            if self._labelmsm and self.ismsm:
                sats = sat2prn(self)
                cells = cell2prn(self, 0 if self._labelmsm == 2 else 1)

        stg = f"<RTCM({self.identity}, "
        for i, att in enumerate(self.__dict__):
            if att[0] != "_":  # only show public attributes
                val = self.__dict__[att]
                # escape all byte chars
                if isinstance(val, bytes):
                    val = escapeall(val)
                # label MSM NSAT and NCELL group attributes
                lbl = ""
                if self._labelmsm and self.ismsm:
                    aname = att2name(att)
                    if aname in ATT_NSAT:
                        prn = sats[att2idx(att)]
                        lbl = f"({prn})"
                    if aname in ATT_NCELL:
                        prn, sig = cells[att2idx(att)]
                        lbl = f"({prn},{sig})"

                stg += att + lbl + "=" + str(val)
                if i < len(self.__dict__) - 1:
                    stg += ", "
        if self._unknown:
            stg += ", Not_Yet_Implemented"
        stg += ")>"

        return stg

    def __repr__(self) -> str:
        """
        Machine readable representation.

        eval(repr(obj)) = obj

        :return: machine readable representation
        :rtype: str
        """

        return f"RTCMMessage(payload={self._payload})"

    def __setattr__(self, name, value):
        """
        Override setattr to make object immutable after instantiation.

        :param str name: attribute name
        :param object value: attribute value
        :raises: rtcmMessageError
        """

        if self._immutable:
            raise rte.RTCMMessageError(
                f"Object is immutable. Updates to {name} not permitted after initialisation."
            )

        super().__setattr__(name, value)

    def serialize(self) -> bytes:
        """
        Serialize message.

        :return: serialized output
        :rtype: bytes
        """

        size = len2bytes(self._payload)
        message = RTCM_HDR + size + self._payload
        crc = crc2bytes(message)
        return message + crc

    @property
    def identity(self) -> str:
        """
        Getter for identity.

        :return: message identity e.g. "1005"
        :rtype: str
        """

        mid = self._payload[0] << 4 | self._payload[1] >> 4

        if mid == 4076:  # proprietary IGS SSR message type
            subtype = (self._payload[1] & 0x1) << 7 | self._payload[2] >> 1
            mid = f"{mid}_{subtype:03d}"

        return str(mid)

    @property
    def payload(self) -> bytes:
        """
        Payload getter - returns the raw payload bytes.

        :return: raw payload as bytes
        :rtype: bytes

        """

        return self._payload

    @property
    def ismsm(self) -> bool:
        """
        Check if message is Multiple Signal Message (MSM) type.

        :return: True/False
        :rtype: bool
        """

        try:
            return "MSM" in RTCM_MSGIDS[self.identity]
        except KeyError:
            return False
