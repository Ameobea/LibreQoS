#!/usr/bin/python3
# v1.2 alpha

import csv
import io
import ipaddress
import json
import os
import subprocess
from datetime import datetime
import multiprocessing
import warnings

from ispConfig import fqOrCAKE, upstreamBandwidthCapacityDownloadMbps, upstreamBandwidthCapacityUploadMbps, \
	defaultClassCapacityDownloadMbps, defaultClassCapacityUploadMbps, interfaceA, interfaceB, enableActualShellCommands, \
	runShellCommandsAsSudo, generatedPNDownloadMbps, generatedPNUploadMbps


def shell(command):
	if enableActualShellCommands:
		if runShellCommandsAsSudo:
			command = 'sudo ' + command
		commands = command.split(' ')
		#print(command)
		proc = subprocess.Popen(commands, stdout=subprocess.PIPE)
		for line in io.TextIOWrapper(proc.stdout, encoding="utf-8"):  # or another encoding
			result = line
		
def clearPriorSettings(interfaceA, interfaceB):
	if enableActualShellCommands:
		shell('tc filter delete dev ' + interfaceA)
		shell('tc filter delete dev ' + interfaceA + ' root')
		shell('tc qdisc delete dev ' + interfaceA + ' root')
		shell('tc qdisc delete dev ' + interfaceA)
		shell('tc filter delete dev ' + interfaceB)
		shell('tc filter delete dev ' + interfaceB + ' root')
		shell('tc qdisc delete dev ' + interfaceB + ' root')
		shell('tc qdisc delete dev ' + interfaceB)

def refreshShapers():
	tcpOverheadFactor = 1.09

	#Verify ShapedDevices.csv is valid
	rowNum = 2
	with open('ShapedDevices.csv') as csv_file:
		csv_reader = csv.reader(csv_file, delimiter=',')
		#Remove comments if any
		commentsRemoved = []
		for row in csv_reader:
			if not row[0].startswith('#'):
				commentsRemoved.append(row)
		#Remove header
		commentsRemoved.pop(0) 
		for row in commentsRemoved:
			circuitID, circuitName, deviceID, deviceName, ParentNode, mac, ipv4_input, ipv6_input, downloadMin, uploadMin, downloadMax, uploadMax, comment = row
			ipv4_hosts = []
			ipv6_hosts = []
			if ipv4_input != "":
				try:
					ipv4_input = ipv4_input.replace(' ','')
					if "," in ipv4_input:
						ipv4_list = ipv4_input.split(',')
					else:
						ipv4_list = [ipv4_input]
					for ipEntry in ipv4_list:
						if '/32' in ipEntry:
							ipEntry = ipEntry.replace('/32','')
							ipv4_hosts.append(ipaddress.ip_address(ipEntry))
						elif '/' in ipEntry:
							ipv4_hosts.extend(list(ipaddress.ip_network(ipEntry).hosts()))
						else:
							ipv4_hosts.append(ipaddress.ip_address(ipEntry))
				except ValueError as e:
						raise Exception("Provided IPv4 '" + ipv4_input + "' in ShapedDevices.csv at row " + str(rowNum) + " is not valid.") from e
			if ipv6_input != "":
				try:
					ipv6_input = ipv6_input.replace(' ','')
					if "," in ipv6_input:
						ipv6_list = ipv6_input.split(',')
					else:
						ipv6_list = [ipv6_input]
					for ipEntry in ipv6_list:
						if '/128' in ipEntry:
							ipEntry = ipEntry.replace('/128','')
							ipv6_hosts.append(ipaddress.ip_address(ipEntry))
						elif '/' in ipEntry:
							ipv6_hosts.extend(list(ipaddress.ip_network(ipEntry).hosts()))
						else:
							ipv6_hosts.append(ipaddress.ip_address(ipEntry))
				except ValueError as e:
						raise Exception("Provided IPv6 '" + ipv6_input + "' in ShapedDevices.csv at row " + str(rowNum) + " is not valid.") from e
			try:
				a = int(downloadMin)
				if a < 1:
					raise Exception("Provided downloadMin '" + downloadMin + "' in ShapedDevices.csv at row " + str(rowNum) + " is < 1 Mbps.")
			except ValueError as e:
				raise Exception("Provided downloadMin '" + downloadMin + "' in ShapedDevices.csv at row " + str(rowNum) + " is not a valid integer.") from e
			try:
				a = int(uploadMin)
				if a < 1:
					raise Exception("Provided uploadMin '" + uploadMin + "' in ShapedDevices.csv at row " + str(rowNum) + " is < 1 Mbps.")
			except ValueError as e:
				raise Exception("Provided uploadMin '" + uploadMin + "' in ShapedDevices.csv at row " + str(rowNum) + " is not a valid integer.") from e
			try:
				a = int(downloadMax)
				if a < 3:
					raise Exception("Provided downloadMax '" + downloadMax + "' in ShapedDevices.csv at row " + str(rowNum) + " is < 3 Mbps.")
			except ValueError as e:
				raise Exception("Provided downloadMax '" + downloadMax + "' in ShapedDevices.csv at row " + str(rowNum) + " is not a valid integer.") from e
			try:
				a = int(uploadMax)
				if a < 3:
					raise Exception("Provided uploadMax '" + uploadMax + "' in ShapedDevices.csv at row " + str(rowNum) + " is < 3 Mbps.")
			except ValueError as e:
				raise Exception("Provided uploadMax '" + uploadMax + "' in ShapedDevices.csv at row " + str(rowNum) + " is not a valid integer.") from e
			rowNum += 1

	# Load Subscriber Circuits & Devices
	subscriberCircuits = []
	knownCircuitIDs = []
	with open('ShapedDevices.csv') as csv_file:
		csv_reader = csv.reader(csv_file, delimiter=',')
		#Remove comments if any
		commentsRemoved = []
		for row in csv_reader:
			if not row[0].startswith('#'):
				commentsRemoved.append(row)
		#Remove header
		commentsRemoved.pop(0)
		for row in commentsRemoved:
			circuitID, circuitName, deviceID, deviceName, ParentNode, mac, ipv4_input, ipv6_input, downloadMin, uploadMin, downloadMax, uploadMax, comment = row
			ipv4_hosts = []
			if ipv4_input != "":
				ipv4_input = ipv4_input.replace(' ','')
				if "," in ipv4_input:
					ipv4_list = ipv4_input.split(',')
				else:
					ipv4_list = [ipv4_input]
				for ipEntry in ipv4_list:
					if '/32' in ipEntry:
						ipv4_hosts.append(ipEntry.replace('/32',''))
					elif '/' in ipEntry:
						theseHosts = ipaddress.ip_network(ipEntry).hosts()
						for host in theseHosts:
							host = str(host)
							if '/32' in host:
								host = host.replace('/32','')
							ipv4_hosts.append(host)
					else:
						ipv4_hosts.append(ipEntry)
			ipv6_hosts = []
			if ipv6_input != "":
				ipv6_input = ipv6_input.replace(' ','')
				if "," in ipv6_input:
					ipv6_list = ipv6_input.split(',')
				else:
					ipv6_list = [ipv6_input]
				for ipEntry in ipv6_list:
					if '/128' in ipEntry:
						ipv6_hosts.append(ipEntry)
					elif '/' in ipEntry:
						theseHosts = ipaddress.ip_network(ipEntry).hosts()
						for host in theseHosts:
							ipv6_hosts.append(str(host))
					else:
						ipv6_hosts.append(ipEntry)
			if circuitID != "":
				if circuitID in knownCircuitIDs:
					for circuit in subscriberCircuits:
						if circuit['circuitID'] == circuitID:
							if circuit['ParentNode'] != "none":
								if circuit['ParentNode'] != ParentNode:
									errorMessageString = "Device " + deviceName + " with deviceID " + deviceID + " had different Parent Node from other devices of circuit ID #" + circuitID
									raise ValueError(errorMessageString)
							if ((circuit['downloadMin'] != round(int(downloadMin)*tcpOverheadFactor))
								or (circuit['uploadMin'] != round(int(uploadMin)*tcpOverheadFactor))
								or (circuit['downloadMax'] != round(int(downloadMax)*tcpOverheadFactor))
								or (circuit['uploadMax'] != round(int(uploadMax)*tcpOverheadFactor))):
								warnings.warn("Device " + deviceName + " with ID " + deviceID + " had different bandwidth parameters than other devices on this circuit. Will instead use the bandwidth parameters defined by the first device added to its circuit.")
							devicesListForCircuit = circuit['devices']
							thisDevice = 	{
											  "deviceID": deviceID,
											  "deviceName": deviceName,
											  "mac": mac,
											  "ipv4s": ipv4_hosts,
											  "ipv6s": ipv6_hosts,
											}
							devicesListForCircuit.append(thisDevice)
							circuit['devices'] = devicesListForCircuit
				else:
					knownCircuitIDs.append(circuitID)
					if ParentNode == "":
						ParentNode = "none"
					ParentNode = ParentNode.strip()
					deviceListForCircuit = []
					thisDevice = 	{
									  "deviceID": deviceID,
									  "deviceName": deviceName,
									  "mac": mac,
									  "ipv4s": ipv4_hosts,
									  "ipv6s": ipv6_hosts,
									}
					deviceListForCircuit.append(thisDevice)
					thisCircuit = {
					  "circuitID": circuitID,
					  "circuitName": circuitName,
					  "ParentNode": ParentNode,
					  "devices": deviceListForCircuit,
					  "downloadMin": round(int(downloadMin)*tcpOverheadFactor),
					  "uploadMin": round(int(uploadMin)*tcpOverheadFactor),
					  "downloadMax": round(int(downloadMax)*tcpOverheadFactor),
					  "uploadMax": round(int(uploadMax)*tcpOverheadFactor),
					  "qdisc": '',
					}
					subscriberCircuits.append(thisCircuit)
			else:
				if circuitName == "":
					circuitName = deviceName
				if ParentNode == "":
					ParentNode = "none"
				ParentNode = ParentNode.strip()
				deviceListForCircuit = []
				thisDevice = 	{
								  "deviceID": deviceID,
								  "deviceName": deviceName,
								  "mac": mac,
								  "ipv4s": ipv4_hosts,
								  "ipv6s": ipv6_hosts,
								}
				deviceListForCircuit.append(thisDevice)
				thisCircuit = {
				  "circuitID": circuitID,
				  "circuitName": circuitName,
				  "ParentNode": ParentNode,
				  "devices": deviceListForCircuit,
				  "downloadMin": round(int(downloadMin)*tcpOverheadFactor),
				  "uploadMin": round(int(uploadMin)*tcpOverheadFactor),
				  "downloadMax": round(int(downloadMax)*tcpOverheadFactor),
				  "uploadMax": round(int(uploadMax)*tcpOverheadFactor),
				  "qdisc": '',
				}
				subscriberCircuits.append(thisCircuit)

	#Verify Network.json is valid json
	with open('network.json') as file:
		try:
			temporaryVariable = json.load(file) # put JSON-data to a variable
		except json.decoder.JSONDecodeError:
			print("network.json is an invalid JSON file") # in case json is invalid
		else:
			print("network.json appears to be a valid JSON file") # in case json is valid

	#Load network heirarchy
	with open('network.json', 'r') as j:
		network = json.loads(j.read())

	# Find queues and CPU cores available. Use min between those two as queuesAvailable
	queuesAvailable = 0
	path = '/sys/class/net/' + interfaceA + '/queues/'
	directory_contents = os.listdir(path)
	for item in directory_contents:
		if "tx-" in str(item):
			queuesAvailable += 1
	
	print("NIC queues:\t" + str(queuesAvailable))
	cpuCount = multiprocessing.cpu_count()
	print("CPU cores:\t" + str(cpuCount))
	queuesAvailable = min(queuesAvailable,cpuCount)

	#Generate Parent Nodes. Spread ShapedDevices.csv which lack defined ParentNode across these (balance across CPUs)
	generatedPNs = []
	for x in range(queuesAvailable):
		genPNname = "Generated_PN_" + str(x+1)
		network[genPNname] =	{
									"downloadBandwidthMbps":generatedPNDownloadMbps,
									"uploadBandwidthMbps":generatedPNUploadMbps
								}
		generatedPNs.append(genPNname)
	genPNcounter = 0
	for circuit in subscriberCircuits:
		if circuit['ParentNode'] == 'none':
			circuit['ParentNode'] = generatedPNs[genPNcounter]
			genPNcounter += 1
			if genPNcounter >= queuesAvailable:
				genPNcounter = 0
	
	#Find the bandwidth minimums for each node by combining mimimums of devices lower in that node's heirarchy
	def findBandwidthMins(data, depth):
		tabs = '   ' * depth
		minDownload = 0
		minUpload = 0
		for elem in data:
			for circuit in subscriberCircuits:
				if elem == circuit['ParentNode']:
					minDownload += circuit['downloadMin']
					minUpload += circuit['uploadMin']
			if 'children' in data[elem]:
				minDL, minUL = findBandwidthMins(data[elem]['children'], depth+1)
				minDownload += minDL
				minUpload += minUL
			data[elem]['downloadBandwidthMbpsMin'] = minDownload
			data[elem]['uploadBandwidthMbpsMin'] = minUpload
		return minDownload, minUpload
	
	minDownload, minUpload = findBandwidthMins(network, 0)

	#Parse network structure. For each tier, create corresponding HTB and leaf classes. Prepare for execution later
	linuxTCcommands = []
	xdpCPUmapCommands = []
	devicesShaped = []
	parentNodes = []
	def traverseNetwork(data, depth, major, minor, queue, parentClassID, parentMaxDL, parentMaxUL):
		tabs = '   ' * depth
		for elem in data:
			#print(tabs + elem)
			elemClassID = hex(major) + ':' + hex(minor)
			#Cap based on this node's max bandwidth, or parent node's max bandwidth, whichever is lower
			elemDownloadMax = min(data[elem]['downloadBandwidthMbps'],parentMaxDL)
			elemUploadMax = min(data[elem]['uploadBandwidthMbps'],parentMaxUL)
			#Based on calculations done in findBandwidthMins(), determine optimal HTB rates (mins) and ceils (maxs)
			#The max calculation is to avoid 0 values, and the min calculation is to ensure rate is not higher than ceil
			elemDownloadMin = round(elemDownloadMax*.95)
			elemUploadMin = round(elemUploadMax*.95)
			#print(tabs + "Download:  " + str(elemDownloadMin) + " to " + str(elemDownloadMax) + " Mbps")
			#print(tabs + "Upload:    " + str(elemUploadMin) + " to " + str(elemUploadMax) + " Mbps")
			#print(tabs, end='')
			linuxTCcommands.append('class add dev ' + interfaceA + ' parent ' + parentClassID + ' classid ' + hex(minor) + ' htb rate '+ str(round(elemDownloadMin)) + 'mbit ceil '+ str(round(elemDownloadMax)) + 'mbit prio 3') 
			#print(tabs, end='')
			linuxTCcommands.append('class add dev ' + interfaceB + ' parent ' + parentClassID + ' classid ' + hex(minor) + ' htb rate '+ str(round(elemUploadMin)) + 'mbit ceil '+ str(round(elemUploadMax)) + 'mbit prio 3') 
			#print()
			thisParentNode =	{
								"parentNodeName": elem,
								"classID": elemClassID,
								"downloadMax": elemDownloadMax,
								"uploadMax": elemUploadMax,
								}
			parentNodes.append(thisParentNode)
			minor += 1
			for circuit in subscriberCircuits:
				#If a device from Shaper.csv lists this elem as its Parent Node, attach it as a leaf to this elem HTB
				if elem == circuit['ParentNode']:
					maxDownload = min(circuit['downloadMax'],elemDownloadMax)
					maxUpload = min(circuit['uploadMax'],elemUploadMax)
					minDownload = min(circuit['downloadMin'],maxDownload)
					minUpload = min(circuit['uploadMin'],maxUpload)
					#print(tabs + '   ' + circuit['circuitName'])
					#print(tabs + '   ' + "Download:  " + str(minDownload) + " to " + str(maxDownload) + " Mbps")
					#print(tabs + '   ' + "Upload:    " + str(minUpload) + " to " + str(maxUpload) + " Mbps")
					#print(tabs + '   ', end='')
					linuxTCcommands.append('class add dev ' + interfaceA + ' parent ' + elemClassID + ' classid ' + hex(minor) + ' htb rate '+ str(minDownload) + 'mbit ceil '+ str(maxDownload) + 'mbit prio 3')
					#print(tabs + '   ', end='')
					linuxTCcommands.append('qdisc add dev ' + interfaceA + ' parent ' + hex(major) + ':' + hex(minor) + ' ' + fqOrCAKE)
					#print(tabs + '   ', end='')
					linuxTCcommands.append('class add dev ' + interfaceB + ' parent ' + elemClassID + ' classid ' + hex(minor) + ' htb rate '+ str(minUpload) + 'mbit ceil '+ str(maxUpload) + 'mbit prio 3') 
					#print(tabs + '   ', end='')
					linuxTCcommands.append('qdisc add dev ' + interfaceB + ' parent ' + hex(major) + ':' + hex(minor) + ' ' + fqOrCAKE)
					parentString = hex(major) + ':'
					flowIDstring = hex(major) + ':' + hex(minor)
					circuit['qdisc'] = flowIDstring
					for device in circuit['devices']:
						if device['ipv4s']:
							for ipv4 in device['ipv4s']:
								#print(tabs + '   ', end='')
								xdpCPUmapCommands.append('./xdp-cpumap-tc/src/xdp_iphash_to_cpu_cmdline --add --ip ' + str(ipv4) + ' --cpu ' + hex(queue-1) + ' --classid ' + flowIDstring)
						if device['deviceName'] not in devicesShaped:
							devicesShaped.append(device['deviceName'])
					#print()
					minor += 1
			#Recursive call this function for children nodes attached to this node
			if 'children' in data[elem]:
				#We need to keep tabs on the minor counter, because we can't have repeating class IDs. Here, we bring back the minor counter from the recursive function
				minor = traverseNetwork(data[elem]['children'], depth+1, major, minor+1, queue, elemClassID, elemDownloadMax, elemUploadMax)
			#If top level node, increment to next queue / cpu core
			if depth == 0:
				if queue >= queuesAvailable:
					queue = 1
					major = queue
				else:
					queue += 1
					major += 1
		return minor
	
	#Here is the actual call to the recursive traverseNetwork() function. finalMinor is not used.
	finalMinor = traverseNetwork(network, 0, major=1, minor=3, queue=1, parentClassID="1:1", parentMaxDL=upstreamBandwidthCapacityDownloadMbps, parentMaxUL=upstreamBandwidthCapacityUploadMbps)
	
	#Record start time of actual filter reload
	reloadStartTime = datetime.now()
	
	#Clear Prior Settings
	clearPriorSettings(interfaceA, interfaceB)

	# Set up XDP-CPUMAP-TC
	shell('./xdp-cpumap-tc/bin/xps_setup.sh -d ' + interfaceA + ' --default --disable')
	shell('./xdp-cpumap-tc/bin/xps_setup.sh -d ' + interfaceB + ' --default --disable')
	shell('./xdp-cpumap-tc/src/xdp_iphash_to_cpu --dev ' + interfaceA + ' --lan')
	shell('./xdp-cpumap-tc/src/xdp_iphash_to_cpu --dev ' + interfaceB + ' --wan')
	if enableActualShellCommands:
		result = os.system('./xdp-cpumap-tc/src/xdp_iphash_to_cpu_cmdline --clear')
	shell('./xdp-cpumap-tc/src/tc_classify --dev-egress ' + interfaceA)
	shell('./xdp-cpumap-tc/src/tc_classify --dev-egress ' + interfaceB)

	# Create MQ qdisc for each interface
	thisInterface = interfaceA
	shell('tc qdisc replace dev ' + thisInterface + ' root handle 7FFF: mq')
	for queue in range(queuesAvailable):
		shell('tc qdisc add dev ' + thisInterface + ' parent 7FFF:' + hex(queue+1) + ' handle ' + hex(queue+1) + ': htb default 2')
		shell('tc class add dev ' + thisInterface + ' parent ' + hex(queue+1) + ': classid ' + hex(queue+1) + ':1 htb rate '+ str(upstreamBandwidthCapacityDownloadMbps) + 'mbit ceil ' + str(upstreamBandwidthCapacityDownloadMbps) + 'mbit')
		shell('tc qdisc add dev ' + thisInterface + ' parent ' + hex(queue+1) + ':1 ' + fqOrCAKE)
		# Default class - traffic gets passed through this limiter with lower priority if not otherwise classified by the Shaper.csv
		# Only 1/4 of defaultClassCapacity is guarenteed (to prevent hitting ceiling of upstream), for the most part it serves as an "up to" ceiling.
		# Default class can use up to defaultClassCapacityDownloadMbps when that bandwidth isn't used by known hosts.
		shell('tc class add dev ' + thisInterface + ' parent ' + hex(queue+1) + ':1 classid ' + hex(queue+1) + ':2 htb rate ' + str(defaultClassCapacityDownloadMbps/4) + 'mbit ceil ' + str(defaultClassCapacityDownloadMbps) + 'mbit prio 5')
		shell('tc qdisc add dev ' + thisInterface + ' parent ' + hex(queue+1) + ':2 ' + fqOrCAKE)
	
	thisInterface = interfaceB
	shell('tc qdisc replace dev ' + thisInterface + ' root handle 7FFF: mq')
	for queue in range(queuesAvailable):
		shell('tc qdisc add dev ' + thisInterface + ' parent 7FFF:' + hex(queue+1) + ' handle ' + hex(queue+1) + ': htb default 2')
		shell('tc class add dev ' + thisInterface + ' parent ' + hex(queue+1) + ': classid ' + hex(queue+1) + ':1 htb rate '+ str(upstreamBandwidthCapacityUploadMbps) + 'mbit ceil ' + str(upstreamBandwidthCapacityUploadMbps) + 'mbit')
		shell('tc qdisc add dev ' + thisInterface + ' parent ' + hex(queue+1) + ':1 ' + fqOrCAKE)
		# Default class - traffic gets passed through this limiter with lower priority if not otherwise classified by the Shaper.csv.
		# Only 1/4 of defaultClassCapacity is guarenteed (to prevent hitting ceiling of upstream), for the most part it serves as an "up to" ceiling.
		# Default class can use up to defaultClassCapacityUploadMbps when that bandwidth isn't used by known hosts.
		shell('tc class add dev ' + thisInterface + ' parent ' + hex(queue+1) + ':1 classid ' + hex(queue+1) + ':2 htb rate ' + str(defaultClassCapacityUploadMbps/4) + 'mbit ceil ' + str(defaultClassCapacityUploadMbps) + 'mbit prio 5')
		shell('tc qdisc add dev ' + thisInterface + ' parent ' + hex(queue+1) + ':2 ' + fqOrCAKE)
	#print()
	
	#Execute actual Linux TC and XDP-CPUMAP-TC filter commands
	with open('linux_tc.txt', 'w') as f:
		for line in linuxTCcommands:
			f.write(f"{line}\n")
	print("Executing linux TC class/qdisc commands")
	shell("/sbin/tc -f -b linux_tc.txt")
	print("Executing XDP-CPUMAP-TC IP filter commands")
	for command in xdpCPUmapCommands:
		shell(command)
	
	reloadEndTime = datetime.now()
	
	#Recap
	for circuit in subscriberCircuits:
		for device in circuit['devices']:
			if device['deviceName'] not in devicesShaped:
				warnings.warn('Device ' + device['deviceName'] + ' with device ID of ' + device['deviceID'] + ' was not shaped. Please check to ensure its Parent Node is listed in network.json.')
	
	#Save for stats
	with open('statsByCircuit.json', 'w') as infile:
		json.dump(subscriberCircuits, infile)
	with open('statsByParentNode.json', 'w') as infile:
		json.dump(parentNodes, infile)
	
	#Report reload time
	reloadTimeSeconds = (reloadEndTime - reloadStartTime).seconds
	print("Queue and IP filter reload completed in " + str(reloadTimeSeconds) + " seconds")
	
	# Done
	currentTimeString = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
	print("Successful run completed on " + currentTimeString)

if __name__ == '__main__':
	refreshShapers()
	print("Program complete")
