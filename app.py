from flask import Flask, render_template, request, jsonify
import matplotlib
matplotlib.use('Agg')
import networkx as nx
import random
import matplotlib.pyplot as plt
import string
from web3 import Web3

app = Flask(__name__)

graph = None
energy_distribution = {}

infura_url = 'https://sepolia.infura.io/v3/3c5b238bb8ae42e9a76ddd561cd51de8'
web3 = Web3(Web3.HTTPProvider(infura_url))
contract_address = '0xF896bB1Da84b8dDE7Ca31D79075B56e51Cdd5582'

contract_abi = [
  {
    "inputs": [
      {
        "internalType": "uint256[]",
        "name": "energies",
        "type": "uint256[]"
      }
    ],
    "name": "storeEnergyDistribution",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "EnergyDistributed",
    "outputs": [
      {
        "internalType": "uint256[]",
        "name": "energies",
        "type": "uint256[]"
      }
    ],
    "stateMutability": "event",
    "type": "event"
  }
]

contract = web3.eth.contract(address=contract_address, abi=contract_abi)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_graph():
    global graph
    data = request.json
    num_nodes = data['num_nodes']

    graph = nx.Graph()
    nodes = list(string.ascii_uppercase[:num_nodes])
    graph.add_nodes_from(nodes)

    for _ in range(num_nodes * 2):
        source = random.choice(nodes)
        target = random.choice(nodes)
        if source != target:
            weight = random.randint(1, 10)
            graph.add_edge(source, target, weight=weight)

    plt.figure(figsize=(8, 6))
    pos = nx.spring_layout(graph)
    nx.draw(graph, pos, with_labels=True, node_color='lightblue', font_weight='bold')
    nx.draw_networkx_edge_labels(graph, pos, edge_labels={(u, v): d['weight'] for u, v, d in graph.edges(data=True)})
    plt.savefig('static/graph.png')
    plt.close()

    return jsonify({"message": "Graph generated successfully."})

@app.route('/distribute', methods=['POST'])
def distribute_energy():
    global graph, energy_distribution
    data = request.json
    energy_amount = float(data['energy'])

    total_inverse_weight = sum(1 / graph[u][v]['weight'] for u, v in graph.edges)

    energy_distribution = {}

    for node in graph.nodes:
        node_inverse_weight = sum(
            1 / graph[u][v]['weight'] for u, v in graph.edges(node))
        distributed_energy = energy_amount * (node_inverse_weight / total_inverse_weight)
        energy_distribution[node] = distributed_energy

    total_distributed_energy = sum(energy_distribution.values())
    normalization_factor = energy_amount / total_distributed_energy

    for node in energy_distribution:
        energy_distribution[node] *= normalization_factor

    plt.figure(figsize=(8, 6))
    pos = nx.spring_layout(graph)
    nx.draw(graph, pos, with_labels=True, node_color='lightblue', font_weight='bold')
    node_labels = {node: f"{energy_distribution[node]:.2f}" for node in graph.nodes}
    offset = 0.1
    adjusted_pos = {node: (x, y + offset) for node, (x, y) in pos.items()}
    nx.draw_networkx_labels(graph, adjusted_pos, labels=node_labels, font_weight='bold', font_size=10)

    plt.savefig('static/graph_updated.png')
    plt.close()

    return jsonify(energy_distribution)

@app.route('/send_to_blockchain', methods=['POST'])
def send_to_blockchain():
    data = request.json
    distribute_energy_data = data['energy_distribution']

    energies = list(distribute_energy_data.values())
    energies = [int(energy * 10**18) for energy in energies]

    account = web3.eth.account.from_key('4e4ed2584441816d729deb11d2c467ea0104db136d5a3b91ed69e671f611f883')
    nonce = web3.eth.get_transaction_count(account.address)

    transaction = contract.functions.storeEnergyDistribution(energies).build_transaction({
        'chainId': 11155111,
        'gas': 25000000,
        'gasPrice': web3.to_wei('20', 'gwei'),
        'nonce': nonce,
    })

    signed_transaction = web3.eth.account.sign_transaction(transaction, private_key='4e4ed2584441816d729deb11d2c467ea0104db136d5a3b91ed69e671f611f883')
    tx_hash = web3.eth.send_raw_transaction(signed_transaction.raw_transaction)

    return jsonify({'transaction_hash': web3.to_hex(tx_hash)})

if __name__ == '__main__':
    app.run(debug=True)
