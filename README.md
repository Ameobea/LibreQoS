# LibreQoS
![Banner](docs/Banner.png "Banner")
LibreQoS is an application that allows you to apply fq_codel traffic shaping to hundreds of clients. <a href="https://www.bufferbloat.net/projects/codel/wiki/">Fq_codel</a> is a Free and Open Source Active Queue Management algorithm that reduces bufferbloat, and can improve the quality of customer connections significantly. LibreQoS works with both IPv4 and IPv6. It apples hundreds of filter rules to direct customer traffic through individual fq_codel instances within an <a href="https://linux.die.net/man/8/tc-htb">HTB</a> (HTB+fq_codel). By utilizing <a href="https://tldp.org/HOWTO/Adv-Routing-HOWTO/lartc.adv-filter.hashing.html">hashing filters</a>, thousands of rules can be applied with minimal impact on traffic throughput or CPU use. This is beta software - please do not deploy in production without testing to ensure compatability with your network architecture and design.
## Who is LibreQoS for?
This software is intended for small Internet Service Providers (<1000 subscribers). Larger Internet Service Providers may benefit more from using commercially supported alternatives with better NMS/CRM integrations such as Preseem or Saisei. Individuals wanting to reduce bufferbloat or latency on their home internet connections may want to try a home router supporting fq_codel, such as Ubiquiti's EdgeRouter-X (must enable advanced queue fq_codel).
## How does fq_codel work?
Fq_codel distinguishes interactive flows of traffic (web browsing, audio streaming, VoIP, gaming) from bulk traffic (streaming video services, software updates). Interactive flows are prioritized to optimize their performance, while bulk traffic gets steady throughput and variable latency. The general reduction of connection latency offered by fq_codel is highly beneficial to end-users.

<img src="docs/latency.png" width="900">

The impact of fq_codel on a 3000Mbps connection vs hard rate limiting — a 30x latency reduction.
>“FQ_Codel provides great isolation... if you've got low-rate videoconferencing and low rate web traffic they never get dropped. A lot of issues with IW10 go away, because all the other traffic sees is the front of the queue. You don't know how big its window is, but you don't care because you are not affected by it. FQ_Codel increases utilization across your entire networking fabric, especially for bidirectional traffic... If we're sticking code into boxes to deploy codel, don't do that. Deploy fq_codel. It's just an across the board win.”
> - Van Jacobson | IETF 84 Talk

# Network Design
* Edge and Core routers with MTU 1500 on links between them
   * If you use MPLS, you would terminate MPLS traffic at the core router. LibreQoS cannot decapsulate MPLS on its own.
* OSPF primary link (low cost) through the server running LibreQoS
* OSPF backup link
![Diagram](docs/diagram.png?raw=true "Diagram")

# v0.8
## Features
* Dual stack: client can be shaped by same qdisc for both IPv4 and IPv6
* Up to 1000 clients (IPv4/IPv6)
* Up to 4Gbps throughput
* HTB+fq_codel
* Shape Clients by Access Point / Node capacity
* Experimental support for CAKE (Common Applications Kept Enhanced)
* TC filters split into groups through hashing filters to significantly increase throughput
* Simple client management via csv file
* Simple statistics - table shows top 20 subscribers by packet loss, with APs listed
## Limitations
* Tested up to 4Gbps/500Mbps asymmetrical throughput with NVIDIA MCX4121A-XCAT. Tested using <a href="https://github.com/microsoft/ethr">Microsoft Ethr</a> with n=500 streams. Throughput is noticably superior with NVIDIA/Mellanox cards vs Intel X710 for some reason. Qdisc locking problem will require integrating <a href="https://github.com/netoptimizer/xdp-cpumap-tc">xdp-cpumap-tc</a> or <a href="https://lwn.net/Articles/840244/">HTB offload</a> feature in future verions to increase bandwidth capacity.
* Linux tc hash tables can only handle ~4000 rules each. This limits total possible clients to 1000 at this time. Eventually we will rework the code to allow for more clients by linking more hash tables.

# v0.9 (Alpha/testing)
## Features
* <a href="https://github.com/xdp-project/xdp-cpumap-tc">XDP-CPUMAP-TC</a> integration greatly improves throughput, allows many more IPv4 clients, and lowers CPU use
* HTB+fq_codel or HTB+cake
* Shape Clients by Access Point / Node capacity
* APs equally distributed among CPUs / NIC queues to greatly increase throughput
* Simple client management via csv file
## Limitations
* Not dual stack, clients can only be shaped by IPv4 address for now in v0.9. Once IPv6 support is added to <a href="https://github.com/xdp-project/xdp-cpumap-tc">XDP-CPUMAP-TC</a> we can then shape IPv6 as well.
* Working on stats feature
## Requirements
* Requires XDP-CPUMAP-TC. <a href="https://github.com/rchac/LibreQoS/tree/main/v0.9-alpha">See here</a> for details.
* Requires kernel version 5.12 or above. <a href="https://ubuntuhandbook.org/index.php/2021/04/linux-kernel-5-12-released/">Tip</a> for installing kernel verion 5.12.
* Only works on dedicated linux machines at the moment, not on VMs. Will soon work on VMs once <a href="https://www.spinics.net/lists/bpf/msg42260.html">this patch</a> is part of the mainline linux kernel.

## General Requirements
* VM or physical server (versions up to v0.8)
* Physical server only (v0.9 and above)
* One management network interface, completely seperate from the traffic shaping interface NIC.
* NIC supporting two interfaces for traffic shaping
  * <a href="https://store.mellanox.com/categories/products/adapter-cards.html?_bc_fsnf=1&Technology=Ethernet&Ports=Dual">NVIDIA ConnectX</a>,
  * Intel X520
  * Intel X710
* Tested with Ubuntu Server 20.04.1+, which is recommended. Ubuntu Desktop not recommended as it uses NetworkManager instead of Netplan.
* Python 3, PIP, and some modules (listed in respective guides)

### Server CPU Recommendations
* Choose a CPU with solid single-thread performance within your budget
* Generally speaking any new CPU above $200 can probably handle shaping over 2Gbps
https://www.cpubenchmark.net/singleThread.html

## Installation and Usage Guide
📄 <a href="https://github.com/rchac/LibreQoS/wiki/LibreQoS-v0.80-Installation-&-Usage-Guide----Proxmox-and-Ubuntu-20.04">LibreQoS 0.80 Installation and Usage Guide - Proxmox and Ubuntu 20.04 LTS</a>

📄 <a href="https://github.com/rchac/LibreQoS/wiki/LibreQoS-v0.78-Installation-&-Usage-Guide----Proxmox-and-Ubuntu-20.04">LibreQoS 0.78 Installation and Usage Guide - Proxmox and Ubuntu 20.04 LTS</a>

## Donate
LibreQoS is based on fq_codel - an open source project led by Dave Taht, and contrinuted to by dozens of others. Without Dave's work, there would be no LibreQoS, Preseem, or Saisei. Please contribute to Dave's patreon here: https://www.patreon.com/dtaht

To support 1000 subscribers using proprietary wrappers for fq_codel would cost the average small ISP $6000 per year. If this application helps your network, please consider donating to Dave's patreon. Donating just $0.2/sub/month ($100/month for 500 subs) comes out to be 60% less than any proprietary solution, and you get to ensure continued development of fq_codel's successor, CAKE.

## Special Thanks
Special thanks to Dave Taht, Jesper Dangaard Brouer, Toke Høiland-Jørgensen, Maxim Mikityanskiy, Yossi Kuperman, and Rony Efraim and Kumar Kartikeya Dwivedi for their many contributions to the linux networking stack. Thank you Phil Sutter, Bert Hubert, Gregory Maxwell, Remco van Mook, Martijn van Oosterhout, Paul B Schroeder, and Jasper Spaans for contributing to the guides and documentation listed below. Thanks to Leo Manuel Magpayo for his help improving documentation and for testing. Thanks to everyone on the <a href="https://lists.bufferbloat.net/listinfo/">Bufferbloat mailing list</a> for your help and contibutions.

## References
* https://tldp.org/HOWTO/Adv-Routing-HOWTO/lartc.adv-filter.hashing.html
* http://linux-ip.net/gl/tc-filters/tc-filters.html
* http://linux-tc-notes.sourceforge.net/tc/doc/cls_u32.txt
* https://github.com/netoptimizer/xdp-cpumap-tc
* https://stackoverflow.com/questions/21454155/linux-tc-u32-filters-strange-error
* https://netdevconf.info/0x14/pub/papers/44/0x14-paper44-talk-paper.pdf

## License
Copyright (C) 2020-2021 Robert Chacón

LibreQoS is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

LibreQoS is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with LibreQoS.  If not, see <http://www.gnu.org/licenses/>.
