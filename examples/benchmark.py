"""
pyrtcm Performance benchmarking utility

Usage (kwargs optional): python3 benchmark.py cycles=10000

Created on 18 Feb 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""
# pylint: disable=line-too-long

from sys import argv
from datetime import datetime
from platform import version as osver, python_version
from pyrtcm.rtcmreader import RTCMReader
from pyrtcm._version import __version__ as rtcmver

RTCMMESSAGES = [
    b"\xd3\x00\x13>\xd0\x00\x03\x8aX\xd9I<\x87/4\x10\x9d\x07\xd6\xafH Z\xd7\xf7",
    b"\xd3\x00\x08>\xf4\xd2\x03ABC\xeapo\xc7",
    b"\xd3\x00\x12B\x91\x81\xc9\x84\x00\x04B\xb8\x88\x008\x80\t\xd0F\x00(\xf0kf",
    b"\xd3\x00\x13>\xd0\x00\x03\x8aX\xd9I<\x87/4\x10\x9d\x07\xd6\xafH Z\xd7\xf7",
    b"\xd3\x00>\xfe\x80\x01\x00\x00\x00\x13\n\xb8\x8a@\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00\x01\xff\x9f\x00\x16\x02\x00\xfe\\\x00\x19\x02\x01\xfe\xdd\x00\x1d\x03\x00\x02\x86\x00\x13\x05\x00\x00\x00\x01\x90\x06\x00\x03\xf7\x00\x1a\x06\x01\x04%\x00\x1e\xd2O,",
    b"\xd3\x01\rCP\x000\xab\x88\xa6\x00\x00\x05GX\x02\x00\x00\x00\x00 \x00\x80\x00\x7f\x7fZZZ\x8aB\x1a\x82Z\x92Z8\x00\x00\x00\x00\x00\r\x11\xe1\xa4tf:f\xe3L,\xb1~\x9d\xf6\x87\xaf\xa0\xee\xff\x98\x14(B!A\xfc\xa9\xfaX\x96\n\x89K\x91\x971\x19c\xb6\x04\xa9\xe1F9l\xc3\x8ee\xd8\xe1\xaas\xa5\x1f?\xe9yc\x97\x98\xc6\x1f`)\xc9\xdck\xa5\x8e\xbcZ\x02SP\x82Yu\x06ex\x06Y\x00x\x10N\xf8T\x00\x05\xb0\xfa\x83\x90\xa2\x83\x89\xdc\xfc\xf1l|\xfeW~\\\xdb~h\x1c\x06\xc3\x82\x07#\x07\xfa\xe6pz\xf0\x03\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xa9:\xaa\xaa\xaa\xa0\x00\x0bB`\xac'\t\xc2P\xb4.\x0b\x82p\x88-\t\x81\xf0\xb4.\nB\xdf\x8d\xc1k\xef\xf7\xde\xb7\xfa\xf0\x18\x13'\xf5/\xea\xa2J\xe4\x99\"T\x04\xb8\x19\xec\xb5Y\xdes\xbc\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa9t\xd0",
    b"\xd3\x00\xc3C\xf0\x00J\n\xbdf\x00\x00\x1c\x07\x01\x00\x00\x00\x00\x00 \x80\x00\x00\x7f\xfc\x8a\x80\x92\x98\x84\x8c\x9d\x9b\n\x0fTJ\xbe\x82'\xd0n\x9f\xc4\xfa\xce\x00\xe8T\x1e\xe1\xfeZ\t\xc0'\xa4\x15\xe6A\xd7_;\xc1\xf2\x85`.\xbe\x05\xa3'\xb6\xa6}\xb2y\xa4\xf5\x9dl\x84\x8a\x98KE\xfc!\xa6\x10W\xc8\x10oM\xfc\xd4\xe9\xfc\xa4<\x00\xbb\x0e\x01m\xcc\x1e\xd1\xb6\x1f\xc6\x0f\xe6\x98\xf1\xe7_4\x126\x18\x12\xe1\x05\xf0x\x14\xaa\xaa\xaa\xa2\xa8\xaa\xaa\xaa\xa2\xaa\xaa\xaa\xaa\xaa\xaa\xaa\x00\x02\xf0\xa0/\n\x82\xf0\x9c$\x08C\x00\xac0\n\x02\x90\xbf\xff\x80M\n\xda\x13S\x94\xa7#\xfb!\xf6\x11\xef%\xdd\xf8z\xa0\xf6\xb3\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00v'\xaf",
    b"\xd3\x00\x91D\x90\x000\xab\x88\xa6\x00\x00\x01\x80\x04\x12\x00\x00\x00\x00 \x01\x00\x00\x7f\xe9\xea\x8b)\xca`\x00\x00P +Z\xf8\x85~u\xef\xe04\xe0\x1f\xfd\x01\xf4\x19\x7f\x89\x81\xa5N:\xa52~\x15h6e\xdc\x18\xdd\xefY\xfb*\x9f\xf3?\xfd\x16Q\xfe$K\xe8\xe5;\xea\x9c\\\x1f\x97D \xd2\xc9\xf6\xfb\xf5\xf7\xb8\x19\xfe\xd1a\xff\xc8\xc2\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xa0\x05\xc1\x88R\x15\x85aXZ\x18\x85axiR\xd2s\x83\xd7\x07\xc9\xc4\xb3\x80\xc5g\x8a\xd4\xe1\xd2\xc3\x96\x00\x08y",
    b'\xd3\x01\rFp\x000\xaa\xad\xe4\x00\x00\x01`\t\x08\x84\x90\x00\x00 \x02\x00\x00/UT\x0c#\xf2Z\x8a\xa2rT\x12\xb0\x00\x00\x00\x00\x00\xf0\xf6\xa7\xb7;I$G\xaaT\xa1Y~\xfd\xfe7\xf5\xe0\x10|\xe4\r\xa7\xbe\xbf\xdf\xfe\x94\x02~h\x96\x0e\xe5\x89\xa7E\x19\xf4\xf7Q\x0e|\xe29\x81Q\x91s\xc6\xf9\x95\xf8C\xae\xcb\xf6\xf9\xa3\xbd\x83\xb5\xfb\x06\x9b"\x86~\xb7}C\xca\x7f4\xa1\x06\x0e\xb2\x84Y6\xfb\xe2\x95~\x0e6{*\xdc\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\x00-\nB\xa0\xb40\x0b\x82\xa0\xbc0\x0b\x02\xb0\xd3\xad\xa0c\xd4\xc7\xac\xc2\xed\x18\xdc\x03bo,\xd1S\x96\xcc\xbfP\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xb2X\xbc',
    b"\xd3\x00\x04L\xe0\x00\x80\xed\xed\xd6",
    b"\xd3\x00\x08>\xf4\xd2\x03ABC\xeapo\xc7",
]


def progbar(i: int, lim: int, inc: int = 20):
    """
    Display progress bar on console.

    :param int i: iteration
    :param int lim: max iterations
    :param int inc: bar increments (20)
    """

    i = min(i, lim)
    pct = int(i * inc / lim)
    if not i % int(lim / inc):
        print(
            f"{int(pct*100/inc):02}% " + "\u2593" * pct + "\u2591" * (inc - pct),
            end="\r",
        )


def benchmark(**kwargs) -> float:
    """
    pyrtcm Performance benchmark test.

    :param int cycles: (kwarg) number of test cycles (10,000)
    :returns: benchmark as transactions/second
    :rtype: float
    :raises: UBXStreamError
    """

    cyc = int(kwargs.get("cycles", 10000))
    txnc = len(RTCMMESSAGES)
    txnt = txnc * cyc

    print(
        f"\nOperating system: {osver()}",
        f"\nPython version: {python_version()}",
        f"\npyrtcm version: {rtcmver}",
        f"\nTest cycles: {cyc:,}",
        f"\nTxn per cycle: {txnc:,}",
    )

    start = datetime.now()
    print(f"\nBenchmark test started at {start}")
    for i in range(cyc):
        progbar(i, cyc)
        for msg in RTCMMESSAGES:
            _ = RTCMReader.parse(msg)
    end = datetime.now()
    print(f"Benchmark test ended at {end}.")
    duration = (end - start).total_seconds()
    rate = round(txnt / duration, 2)

    print(
        f"\n{txnt:,} messages processed in {duration:,.3f} seconds = {rate:,.2f} txns/second.\n"
    )

    return rate


def main():
    """
    CLI Entry point.

    args as benchmark() method
    """

    benchmark(**dict(arg.split("=") for arg in argv[1:]))


if __name__ == "__main__":

    main()
