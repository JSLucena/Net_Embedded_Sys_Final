import configparser
import csv
import sys
import random
# Function to generate a ring topology
topology_nodes = []
links = []


def get_es_nodes(devices):
    return [device['DeviceName'] for device in devices if device['DeviceType'] == 'ES']

def generate_ring_topology(switch_count, nodes_per_switch):
    topology_data = []
    links_data = []
    ports = {}
    # Generate switches and nodes
    for i in range(switch_count):
        switch_name = f"Switch_{i}"
        topology_data.append({"DeviceType": "SW", "DeviceName": switch_name, "Ports": nodes_per_switch + 2, "Domain": "Domain_1"})  # +2 for ring links
        ports[switch_name] = 0
        
        for j in range(nodes_per_switch):
            node_name = f"Node_{i}_{j}"
            topology_data.append({"DeviceType": "ES", "DeviceName": node_name, "Ports": 1, "Domain": "Domain_1"})
            links_data.append({"LinkID": f"Link_{i}_{j}", "SourceDevice": node_name, "SourcePort": 0, "DestinationDevice": switch_name, "DestinationPort": j, "Domain": "Domain_1"})
            ports[switch_name] += 1
    
    # Generate links between switches for the ring
    for i in range(switch_count):
        next_switch = (i + 1) % switch_count
        next_switch = f"Switch_{next_switch}"
        switch_name = f"Switch_{i}"
        links_data.append({"LinkID": f"Ring_Link_{i}", "SourceDevice": switch_name, "SourcePort": ports[switch_name], "DestinationDevice": next_switch, "DestinationPort": ports[next_switch], "Domain": "Domain_1"})
        ports[next_switch] += 1
        ports[switch_name] += 1
    
    return topology_data, links_data

def generate_stream_configurations(devices, stream_info):
    es_nodes = get_es_nodes(devices)
    num_es_nodes = len(es_nodes)
    stream_configs = []

    for stream_name, stream_data in stream_info.items():
        num_sources = int(num_es_nodes * stream_data['Distribution'])
        source_nodes = random.sample(es_nodes, num_sources)

        for source in source_nodes:
            destination = random.choice([node for node in es_nodes if node != source])
            config = {
                'StreamName': f"{stream_name}_{source}_{destination}",
                'Source': source,
                'Type' : stream_data['Type'],
                'Destination': destination,
                'PCP': stream_data['PCP'],
                'Size': stream_data['Size'],
                'Period': stream_data['Period'],
                'Deadline': stream_data['Deadline'],
                'Port' : stream_data['Port']
            }
            stream_configs.append(config)

    return stream_configs


def generate_network_description(devices, links):
    output = []
    output.append("package dtu_networks;")
    output.append("")
    output.append("import inet.networks.base.TsnNetworkBase;")
    output.append("import inet.node.ethernet.Eth1G;")
    output.append("import inet.node.tsn.TsnDevice;")
    output.append("import inet.node.tsn.TsnSwitch;")
    output.append("")
    output.append("network ring_3sw_network extends TsnNetworkBase")
    output.append("{")
    output.append('@display("bgb=1500,1000");')
    output.append("")
    output.append("submodules:")

    # Generate submodules
    for device in devices:
        device_type = "TsnSwitch" if device['DeviceType'] == 'SW' else "TsnDevice"
        output.append(f"    {device['DeviceName']}: {device_type} {{")
        output.append(f'        @display("p={100 + hash(device["DeviceName"]) % 1000},{100 + hash(device["DeviceName"]) % 600}");')
        output.append("    }")

    output.append("")
    output.append("connections:")

    # Generate connections
    for link in links:
        output.append(f"    {link['SourceDevice']}.ethg++ <--> Eth1G <--> {link['DestinationDevice']}.ethg++;")

    output.append("}")

    return "\n".join(output)

def write_devices_to_csv(devices, filename='devices.csv'):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        #writer.writerow(['Type', 'Name', 'Ports', 'Domain'])
        
        # Write devices
        for device in devices:
            writer.writerow([
                device['DeviceType'],
                device['DeviceName'],
                device['Ports'],
                device['Domain']
            ])

def write_links_to_csv(links, filename='links.csv'):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        #writer.writerow(['LinkID', 'SourceDevice', 'SourcePort', 'DestinationDevice', 'DestinationPort', 'Domain'])
        
        # Write links
        for link in links:
            writer.writerow([
                link['LinkID'],
                link['SourceDevice'],
                link['SourcePort'],
                link['DestinationDevice'],
                link['DestinationPort'],
                link['Domain']
            ])

def write_streams_to_csv(streams, filename='streams.csv'):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for stream in streams:
            writer.writerow([
                stream['PCP'],
                stream['StreamName'],
                stream['Type'],
                stream['Source'],
                stream['Destination'],
                stream['Size'],
                stream['Period'],
                stream['Deadline']

            ])

# A function to generate distinct colors based on the number of stream types
def generate_colors(num_colors):
    base_colors = ['red1', 'blue4', 'green1', 'orange', 'purple', 'yellow4', 'cyan', 'silver']
    if num_colors <= len(base_colors):
        return base_colors[:num_colors]
    # If there are more stream types than base colors, we cycle through base colors
    colors = base_colors * (num_colors // len(base_colors)) + base_colors[:num_colors % len(base_colors)]
    return colors


def generate_omnetpp_ini(stream_data, types, configs,filename='omnetpp.ini'):
    with open(filename, 'w') as f:
        # General settings
        f.write("[General]\n")
        f.write("network = dtu_networks.ring_3sw_network\n")
        f.write("sim-time-limit = 1.0s\n")
        f.write("\n")
        
        # Visualization settings
        f.write("# enable multiple canvas visualizers\n")
        f.write("*.visualizer.typename = \"IntegratedMultiCanvasVisualizer\"\n")
        f.write("\n")
        
        colors = generate_colors(len(types))
        #print(colors)
        #print(types)
        # Route visualizer setup based on stream names
        f.write("# network route activity visualization\n")
        f.write(f"*.visualizer.numNetworkRouteVisualizers = {len(stream_types)}\n")
        for i, (stream_type, color) in enumerate(zip(types, colors)):
            f.write(f"*.visualizer.networkRouteVisualizer[{i}].packetFilter = \"\\\"{stream_type}*\\\"\"\n")
            f.write(f"*.visualizer.networkRouteVisualizer[{i}].lineColor = \"{color}\"\n")

        # Network bitrate setup
        f.write("\n*.*.eth[*].bitrate = 1Gbps\n\n")

        delay = configs["PacketDelayerDelay"]
        f.write("# packet processing delay\n")
        f.write("*.*.bridging.directionReverser.delayer.typename = \"PacketDelayer\"\n")
        f.write(f"*.*.bridging.directionReverser.delayer.delay = {delay}us\n\n")
        
        nodes = set()
        for stream in stream_data:
            nodes.add(stream['Source'])
            nodes.add(stream['Destination'])
        #print(nodes)
        for node in nodes:
            f.write(f"*.{node}.numApps = {len([s for s in stream_data if s['Source'] == node or s['Destination'] == node])}\n")
        f.write("\n")

        app_count = {node: 0 for node in nodes}
        #print(app_count)
        for stream in stream_data:
            source = stream['Source']
            dest = stream['Destination']
            pcp = stream['PCP']
            stream_type = stream['Type'].split('_')[0]
            size = stream['Size']
            period = stream['Period']
            port = stream['Port']

            f.write(f"*.{source}.app[{app_count[source]}].typename = \"UdpSourceApp\"\n")
            f.write(f"*.{source}.app[{app_count[source]}].display-name = \"{stream_type}\"\n")
            f.write(f"*.{source}.app[{app_count[source]}].io.destAddress = \"{dest}\"\n")
            f.write(f"*.{source}.app[{app_count[source]}].io.destPort = {port}\n")
            f.write(f"*.{source}.app[{app_count[source]}].source.productionInterval = {period}us\n")
            f.write(f"*.{source}.app[{app_count[source]}].source.initialProductionOffset = {period}us\n")
            f.write(f"*.{source}.app[{app_count[source]}].source.packetLength = {size}B\n\n")

            f.write(f"*.{dest}.app[{app_count[dest]}].typename = \"UdpSinkApp\"\n")
            f.write(f"*.{dest}.app[{app_count[dest]}].io.localPort = {port}\n\n")

            app_count[source] += 1
            app_count[dest] += 1
          
        f.write("*.node*.hasUdp = firstAvailableOrEmpty(\"Udp\") != \"\"\n\n")

        f.write("# steering stream identification and coding\n")
        f.write("*.node*.bridging.streamIdentifier.identifier.mapping = [\n")


        ### Ugly hack but whatever
        filters = []
        for s in stream_data:
            found = False
            name = s['StreamName'].split('_')[0]
            for thing in filters:
                if thing[0] == name:
                    found = True
            if not found:
                filters.append((name,s))

        for thing in filters:
            stream_type = thing[0]
            port = thing[1]['Port']
            f.write(f"    {{stream: \"{stream_type}\", packetFilter: expr(udp.destPort == {port})}},\n")
        f.write("]\n\n")
        """ 
        f.write("# traffic configuration\n")
        f.write(f"*.*.eth[*].macLayer.queue.numTrafficClasses = {len(set([s['PCP'] for s in stream_data]))}\n")
        f.write(f"*.*.eth[*].macLayer.queue.numQueues = {len(set([s['PCP'] for s in stream_data]))}\n")
        for i, pcp in enumerate(set([s['PCP'] for s in stream_data])):
            stream_type = [s for s in stream_data if s['PCP'] == pcp][0]#['StreamName'].split('_')[0]
            print(stream_type)
            f.write(f"*.*.eth[*].macLayer.queue.*[{i}].display-name = \"{stream_type}\"\n")
        f.write("\n")
         
        f.write("# client stream encoding\n")
        f.write("*.*.bridging.streamCoder.encoder.mapping = [")
        for pcp in set([s[0] for s in streams]):
            stream_type = [s for s in streams if s[0] == pcp][0][1].split('_')[0]
            f.write(f"{{stream: \"{stream_type}\", pcp: {pcp}}}, ")
        f.write("]\n\n")

        f.write("# enable streams\n")
        f.write("*.*.hasIncomingStreams = true\n")
        f.write("*.*.hasOutgoingStreams = true\n\n")

        f.write("# stream coder mappings for switches\n")
        f.write("*.sw*.bridging.streamCoder.encoder.mapping = [")
        for pcp in set([s[0] for s in streams]):
            stream_type = [s for s in streams if s[0] == pcp][0][1].split('_')[0]
            f.write(f"{{stream: \"{stream_type}\", pcp: {pcp}}}, ")
        f.write("]\n")
        f.write("*.sw*.bridging.streamCoder.decoder.mapping = [")
        for pcp in set([s[0] for s in streams]):
            stream_type = [s for s in streams if s[0] == pcp][0][1].split('_')[0]
            f.write(f"{{stream: \"{stream_type}\", pcp: {pcp}}}, ")
        f.write("]\n")
        f.write("*.sw*.eth[*].macLayer.queue.classifier.mapping = [[0, 1, 2], [0, 1, 2], [0, 1, 2], [0, 1, 2], [0, 1, 2], [0, 1, 1], [0, 0, 0], [0, 1, 2]]\n\n")

        f.write("# enable ingress per-stream filtering\n")
        f.write("*.sw*.hasIngressTrafficFiltering = true\n\n")

        f.write("# enable egress traffic shaping\n")
        f.write("*.*.hasEgressTrafficShaping = true\n\n")

        f.write("# asynchronous shaper traffic metering\n")
        f.write(f"*.sw*.bridging.streamFilter.ingress.numStreams = {len(set([s[0] for s in streams]))}\n")
        f.write("*.sw*.bridging.streamFilter.ingress.classifier.mapping = { ")
        for pcp in set([s[0] for s in streams]):
            stream_type = [s for s in streams if s[0] == pcp][0][1].split('_')[0]
            f.write(f"\"{stream_type}\": {pcp-1}, ")
        f.write("}\n")
        for i, pcp in enumerate(set([s[0] for s in streams])):
            stream_type = [s for s in streams if s[0] == pcp][0][1].split('_')[0]
            f.write(f"*.sw*.bridging.streamFilter.ingress.*[{i}].display-name = \"{stream_type}\"\n")
        f.write("*.sw*.bridging.streamFilter.ingress.meter[*].typename = \"EligibilityTimeMeter\"\n")
        f.write("*.sw*.bridging.streamFilter.ingress.filter[*].typename = \"EligibilityTimeFilter\"\n\n")

        for i, pcp in enumerate(set([s[0] for s in streams])):
            f.write(f"*.sw*.bridging.streamFilter.ingress.meter[{i}].committedInformationRate = 10Mbps\n")
            f.write(f"*.sw*.bridging.streamFilter.ingress.meter[{i}].committedBurstSize = {500 if i == 0 else 5000}B\n")

        f.write("\n# asynchronous traffic shaping\n")
        f.write("*.sw*.eth[*].macLayer.queue.transmissionSelectionAlgorithm[*].typename = \"Ieee8021qAsynchronousShaper\"\n")
        """
    print(f"OMNeT++ .ini file '{filename}' has been generated.")


# Load config file
config = configparser.ConfigParser()
config.read(sys.argv[1])


# Read topology configuration
switch_count = int(config['Topology']['SwitchCount'])
nodes_per_switch = int(config['Topology']['NodesPerSwitch'])
topology_type = config['Topology']['TopologyType']

ini_file_config = {
    "PacketDelayerDelay" : int(config['INI']['PacketDelayerDelay'])
}

if topology_type == "RING":
    topology_nodes, links = generate_ring_topology(switch_count,nodes_per_switch)


streams = {}
stream_types = []
for stream in config["Streams"]:
    streams[stream] = config['Streams'][stream]
    stream_types.append(stream)

for key, value in streams.items():
    #print
    stream_properties = {}
    stream_properties["PCP"] = int(config[value]['PCP'])
    stream_properties["Size"] = int(config[value]['Size'])
    stream_properties["Period"] = int(config[value]['Period'])
    stream_properties["Deadline"] = int(config[value]['Deadline'])
    stream_properties["Distribution"] = float(config[value]['Distribution'])
    stream_properties["Type"] = config[value]['Type']
    stream_properties["Port"] = int(config[value]['Port'])
    #print(stream_properties)
    streams[key] = stream_properties

#print(streams)

stream_data = generate_stream_configurations(topology_nodes,streams)
#for thing in stream_data:
    #print(thing)

write_devices_to_csv(topology_nodes)
write_links_to_csv(links)
write_streams_to_csv(stream_data)


print(generate_omnetpp_ini(stream_data,stream_types,ini_file_config))