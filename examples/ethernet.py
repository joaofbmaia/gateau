"""10G Ethernet / IPv4 / UDP, receive and transmit (alexforencich/verilog-ethernet, MIT), as in study 03.

64-bit datapath modules. PTP timestamps, ARP request generation and statistics omitted.
Defaults from the RTL: RX/TX frame FIFOs 4096 bytes, UDP checksum FIFO 2048 × 64-bit beats,
ARP cache 2^9 entries.
"""
from gateau import Buffer, Design

OUTSIDE = ("SERDES", "APP")
MAX_FRAME = 1518         # bytes, standard Ethernet frame including FCS
MAX_DATAGRAM = 1480      # bytes, UDP header + payload inside a 1500-byte IP MTU


def build() -> Design:
    d = Design("ethernet", axes=dict(byte=8))
    d.domains += ["clk"]

    # receive carriers: blocks, then a packet bus above a beat bus
    d.carrier("blk_rx", "one 66-bit block per cycle", "clk")
    d.carrier("pkt_rx", "one received packet", "clk")
    d.carrier("beat_rx", "one 64-bit beat", "clk", parent="pkt_rx")
    # transmit carriers
    d.carrier("pkt_tx", "one packet to send", "clk")
    d.carrier("beat_tx", "one 64-bit beat", "clk", parent="pkt_tx")
    d.carrier("blk_tx", "one 66-bit block per cycle", "clk")

    for side in ("rx", "tx"):
        d.field(f"blk_{side}", "data", 64)
        d.field(f"blk_{side}", "hdr", 2)
        d.field(f"beat_{side}", "tdata", 8, ("byte",))
        d.field(f"beat_{side}", "tkeep", 1, ("byte",))
        d.field(f"beat_{side}", "tlast", 1)
    d.field("pkt_rx", "fcs_ok", 1, availability="tail")
    d.field("pkt_tx", "fcs", 32, availability="tail")
    for side in ("rx", "tx"):
        pkt = f"pkt_{side}"
        for n, w in (("dest_mac", 48), ("src_mac", 48), ("type", 16)):
            d.field(pkt, n, w, group="eth")
        for n, w in (("version", 4), ("ihl", 4), ("dscp", 6), ("ecn", 2), ("length", 16), ("id", 16),
                     ("flags", 3), ("frag", 13), ("ttl", 8), ("proto", 8), ("hdr_csum", 16),
                     ("src_ip", 32), ("dst_ip", 32)):
            d.field(pkt, n, w, group="ip")
        for n, w in (("sport", 16), ("dport", 16), ("udp_len", 16)):
            d.field(pkt, n, w, group="udp")
        d.field(pkt, "checksum", 16, group="udp", availability="tail" if side == "tx" else "whole")

    d.state("arp", "shared")                             # 512-entry cache: RX fills it, TX reads it

    # receive boundaries: rigid up to the frame FIFO
    d.boundary("r1", coupling="rigid")                   # MAC input
    d.boundary("r3", after="r1", latency=2, coupling="rigid")
    d.boundary("rf", coupling="elastic")                 # RX frame FIFO output
    # transmit boundaries: rigid from the frame FIFO on
    d.boundary("t0", coupling="elastic")
    d.boundary("t1", coupling="rigid")
    d.boundary("t2", coupling="rigid")

    # receive stages
    d.stage("PHY_RX", "blk_rx", reads=["hdr"], writes=["data"], note="block lock, descramble")
    d.stage("MAC_DLY", "blk_rx", out="beat_rx", between=("r1", "r3"), reads=["data"],
            creates=["tdata", "tkeep", "tlast"], note="data held 2 blocks; preamble and FCS stripped")
    d.stage("MAC_CRC", "blk_rx", out="pkt_rx", between=("r1", "r3"), reads=["data"], creates=["fcs_ok"])
    d.stage("FIFO_RX", "beat_rx", between=("r3", "rf"), reads=["pkt_rx.fcs_ok"],
            buffer=Buffer(depth=4096, unit="byte", policy="drop", item_max=MAX_FRAME))
    d.stage("ETH_RX", "beat_rx", out="pkt_rx", reads=["tdata"], creates=["eth.*"], note="14 B; realign 6")
    d.stage("IP_RX", "beat_rx", out="pkt_rx", reads=["tdata"], creates=["ip.*"],
            note="20 B; realign 4; trim to ip.length; drop on bad header checksum")
    d.stage("UDP_RX", "beat_rx", out="pkt_rx", reads=["tdata"], creates=["udp.*"],
            note="8 B; trim to udp_len; checksum passed through unverified")
    d.stage("ARP_RX", "pkt_rx", reads=["type"], state_writes=["arp"])

    # transmit stages
    d.stage("CSUM", "pkt_tx", creates=["checksum"],
            buffer=Buffer(depth=2048 * 8, unit="byte", policy="prebuffer", item_max=MAX_DATAGRAM),
            note="sums the payload while it waits in the FIFO")
    d.stage("UDP_TX", "pkt_tx", out="beat_tx", reads_at_head=["udp.*"], consumes=["udp.*"])
    d.stage("ARP_TX", "pkt_tx", reads=["dst_ip"], state_reads=["arp"], writes=["dest_mac"])
    d.stage("IP_TX", "pkt_tx", out="beat_tx", reads_at_head=["ip.*"], consumes=["ip.*"],
            note="header checksum from fields only")
    d.stage("ETH_TX", "pkt_tx", out="beat_tx", reads_at_head=["eth.*"], consumes=["eth.*"])
    d.stage("FIFO_TX", "beat_tx", between=("t0", "t1"),
            buffer=Buffer(depth=4096, unit="byte", policy="prebuffer", item_max=MAX_FRAME))
    d.stage("MAC_TX", "beat_tx", out="blk_tx", between=("t1", "t2"), creates=["pkt_tx.fcs"],
            note="preamble, pad to 64 B, FCS appended at the tail, IFG/DIC")

    d.join("crc-verdict-meets-data", "lat", ["MAC_DLY", "MAC_CRC"],
           evidence="input_data_d0 / input_data_d1 in axis_baser_rx_64.v")
    d.join("header-meets-payload", "fifo", ["UDP_RX"])

    d.fb("ctrl", "PHY_RX", "SERDES", note="bitslip until block lock")
    d.fb("flow", "ETH_RX", "FIFO_RX", note="tready")
    d.fb("ctrl", "ARP_TX", "APP", note="ARP miss: wait for a reply on the RX path")
    return d
