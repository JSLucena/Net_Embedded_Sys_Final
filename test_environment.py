import configparser
import csv
import sys
# Function to generate a ring topology
topology_nodes = []
links = []


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

# Function to generate streams based on the configuration
def generate_streams(topology_data, stream_a_enabled, stream_c_enabled, stream_a_properties, stream_c_properties):
    streams_data = []
    compute_nodes = [device["DeviceName"] for device in topology_data if device["DeviceType"] == "ES"]
    
    half_nodes = len(compute_nodes) // 2
    
    # Half of the nodes generate stream A
    if stream_a_enabled:
        for node in compute_nodes[:half_nodes]:
            streams_data.append({
                "PCP": stream_a_properties["PCP"], 
                "StreamName": f"Stream_A_{node}", 
                "StreamType": "ATS", 
                "SourceNode": node, 
                "DestinationNode": "Some_Destination", 
                "Size": stream_a_properties["Size"], 
                "Period": stream_a_properties["Period"], 
                "Deadline": stream_a_properties["Deadline"]
            })
    
    # All nodes generate stream C
    if stream_c_enabled:
        for node in compute_nodes:
            streams_data.append({
                "PCP": stream_c_properties["PCP"], 
                "StreamName": f"Stream_C_{node}", 
                "StreamType": "ATS", 
                "SourceNode": node, 
                "DestinationNode": "Some_Destination", 
                "Size": stream_c_properties["Size"], 
                "Period": stream_c_properties["Period"], 
                "Deadline": stream_c_properties["Deadline"]
            })
    
    return streams_data

# Load config file
config = configparser.ConfigParser()
config.read(sys.argv[1])


# Read topology configuration
switch_count = int(config['Topology']['SwitchCount'])
nodes_per_switch = int(config['Topology']['NodesPerSwitch'])
topology_type = config['Topology']['TopologyType']

if topology_type == "RING":
    topology_nodes, links = generate_ring_topology(switch_count,nodes_per_switch)

#for thing in topology_nodes:
#    print(thing)
#for thing in links:
#    print(thing)
#print(topology_nodes)
#print(links)

#print(generate_network_description(topology_nodes,links))

# Read stream configuration
streams = {}
for stream in config["Streams"]:
    streams[stream] = config['Streams'][stream]
print(streams)


for key, value in streams.items():
    #print
    stream_properties = {}
    stream_properties["PCP"] = int(config[value]['PCP'])
    stream_properties["Size"] = int(config[value]['Size'])
    stream_properties["Period"] = int(config[value]['Period'])
    stream_properties["Deadline"] = int(config[value]['Deadline'])
    stream_properties["Distribution"] = float(config[value]['Distribution'])
    #print(stream_properties)
    streams[key] = stream_properties

print(streams)

