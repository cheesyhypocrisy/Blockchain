# -*- coding: utf-8 -*-
"""
Created on Mon May 31 12:35:41 2018

@author: Khan
"""

import datetime
import json
from flask import Flask, jsonify, request,render_template
import hashlib
import requests
from uuid import uuid4
from urllib.parse import urlparse
from apscheduler.scheduler import Scheduler
import urllib


def isfloat(x):
    try:
        a = float(x)
    except ValueError:
        return False
    return True

class Blockchain:
    def __init__(self):
        self.chain = []
        self.transactions = []
        self.difficulty = 4
        self.create_block(nonce = 1, previous_hash = '0')
        self.nodes = set()
        
    def create_block(self, nonce, previous_hash):
        block = {'block_id': len(self.chain)+1,
                 'timestamp': str(datetime.datetime.now()),
                 'nonce': nonce,
                 'previous_hash': previous_hash,
                 'hash': '0',
                 'transactions': self.transactions}
        self.transactions = []
        if len(self.chain) == 0:
            block['hash'], block['nonce'] = self.proof_of_work(block)            
            self.chain.append(block)
        return block
    
    def get_previous_block(self):
        return self.chain[-1]
    
    def proof_of_work(self, block):
        encoded_block = json.dumps(block, sort_keys = True).encode()
        nonce = 1
        valid_hash = False
        while valid_hash is False:
            hash_operation = hashlib.sha256(encoded_block + str(nonce).encode()).hexdigest()
            if hash_operation[:self.difficulty] == self.difficulty*'0':
                valid_hash = True
            else:
                nonce += 1
        return hash_operation, nonce
    
    def add_to_chain(self, block):
        block['hash'], block['nonce'] = self.proof_of_work(block)
        self.chain.append(block)
        return block
    
    def is_chain_valid(self, chain):
        previous_block = chain[0].copy()
        block_index = 1
        while block_index < len(chain):
            block = chain[block_index].copy()
            if block_index == 1:
                previous_block = block
                block_index += 1
            else:
                previous_block['hash'], previous_block['nonce'] = '0', 1
                hash_operation, _ = self.proof_of_work(previous_block)
                if block['previous_hash'] != hash_operation:
                    return False
                block['hash'], block['nonce'] = '0', 1
                hash_operation, _ = self.proof_of_work(block)
                if hash_operation[:self.difficulty] != self.difficulty*'0':
                    return False
                previous_block = block
                block_index += 1
        return True
    
    def add_transaction(self, sender, receiver, bitkhan):
        self.transactions.append({'sender': sender, 'receiver': receiver, 'bitkhan': bitkhan})
        previous_block = self.get_previous_block()
        return previous_block['block_id'] + 1
    
    def add_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)
        
    def consensus(self):
        lengths1 = [len(self.chain)]
        network1 = self.nodes
        for node1 in network1:
            try:
                response1 = requests.get(f'http://{node1}/get_chain')
                if response1.status_code == 200:
                    lengths1.append(response1.json()['length'])
            except Exception:
                continue
        flag1 = False
        prev_length1 = lengths1[0]
        for length1 in lengths1:
            if length1 == prev_length1:
                prev_length1 = length1
                flag1 = True
            else:
                flag1 = False
                break
        if flag1:
            return False
        else:
            len_chain = [len(self.chain)]
            network = self.nodes
            for node in network:
                try:
                    res = requests.get(f'http://{node}/get_chain')
                    if res.status_code == 200:
                        length = res.json()['length']
                        len_chain.append(length)
                except Exception:
                    continue
            min_len = min(len_chain)
            hash_dict = {}
            frequency = {}
            for node in network:
                try:
                    res = requests.get(f'http://{node}/get_chain')
                    if res.status_code == 200:
                        chain = res.json()['chain']
                        if self.is_chain_valid(chain):
                            hash_dict[node] = chain[min_len-1]['hash']
                except Exception:
                    continue
            hash_dict['current_node'] = self.chain[min_len-1]['hash']
            print(hash_dict)
            for i in hash_dict:
                if hash_dict[i] in frequency:
                    frequency[hash_dict[i]] += 1
                else:
                    frequency[hash_dict[i]] = 1
            print(frequency)
            print(sum(frequency.values()))
            valid_hash = None
            for i in frequency:
                print(i)
                if frequency[i]/sum(frequency.values()) >= 0.5:
                    valid_hash = i
            if valid_hash == None:
                self.replace_chain()
                return True
            print(valid_hash)
            ######
            valid_nodes = [k for k,v in hash_dict.items() if v == valid_hash]
            print(valid_nodes)
            if hash_dict['current_node'] == valid_hash:
                valid_chain = [self.chain]
                valid_len = [len(self.chain)]
            else:
                valid_chain, valid_len = [], []
            for valid_node in valid_nodes:
                try:
                    response = requests.get(f'http://{valid_node}/get_chain')
                    if response.status_code == 200:
                        length = response.json()['length']
                        valid_len.append(length)
                        valid_chain.append(response.json()['chain'])
                except Exception:
                    continue
            index = valid_len.index(max(valid_len))  
            longest_chain = valid_chain[index]  
            if longest_chain != self.chain and longest_chain[min_len-1]['hash'] == valid_hash:                   
                self.chain = longest_chain
                return True            
            return False

    def replace_chain(self):
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        for node in network:
            try:
                response = requests.get(f'http://{node}/get_chain')
                if response.status_code == 200:
                    length = response.json()['length']
                    chain = response.json()['chain']
                    if length > max_length and self.is_chain_valid(chain):
                        max_length = length
                        longest_chain = chain
            except Exception:
                continue
        if longest_chain:
            self.chain = longest_chain
            return True
        return False
    
# Creating a WebApp
app = Flask(__name__)

# Creating a address for the node on the Port 5000
node_address = str(uuid4()).replace('-','')

# Initiating a Blockchain
blockchain = Blockchain()

# Getting the full Blockchain    
@app.route('/get_chain', methods = ['GET'])
def get_chain():
    response = {'chain': blockchain.chain,
                'length': len(blockchain.chain)}
    return jsonify(response), 200

@app.route('/getchain', methods = ['GET'])
def getChain():
#    response = {'chain': blockchain.chain,
#                'length': len(blockchain.chain)}
    result = blockchain.chain
    return render_template('get_chain.html',response=result)

@app.route('/getchain', methods = ['POST'])
def getChainConnected():
    print('I think I work')
    node = request.form['node']
    print('Does this fail?')
    print(node)
    blockchain.add_node(node)
    print(blockchain.nodes)
    node_list = []
    print('This is reached actually')
    response1 = requests.get(f'{node}/getNodes')
    if response1.status_code == 200:
        node_list = response1.json()['nodeList']
#    node_dict = urllib.request.urlopen(node)
#    node_dict = node_dict.read()
#    node_list = [node]
#    for node in node_dict['nodeList']:
#        node_list.append(node)
    for node in node_list:
        if node!="":
            print(node)
            blockchain.add_node("http://"+node)
    return render_template('get_chain.html')
#    json = .get_json()
#    nodes = json.get('nodes')
#    if nodes is None:
#        return "No node", 400
#    for node in nodes:
#        blockchain.add_node(node)
#    response = {'message': 'All the nodes are now connected. The Bitkhan blockchain contains the following nodes:',
#                'total_nodes': list(blockchain.nodes)}
#    return jsonify(response), 201

@app.route('/getNodes',methods=['GET'])
def getNodes():
    print("Enter")
    nodes = list(blockchain.nodes)
    requester = request.host
    print(request.path)
    print(requester)
    try:
        nodes.remove(requester)
    except:
        pass
    response = {'nodeList': nodes}
    print(response)
    return jsonify(response), 200

# Checking the validity of Blockchain
@app.route('/is_valid', methods = ['GET'])
def is_valid():
    is_valid = blockchain.is_chain_valid(blockchain.chain)
    if is_valid:
        response = {'message': 'The Blockchain is valid!'}
    else:
        response = {'message': 'The Blockchain is not valid!'}
    return jsonify(response), 200

# Adding a transaction to the Blockchain
@app.route('/add_transaction', methods = ['POST'])
def add_transaction():
    json = request.get_json()
    transaction_keys = ['sender','receiver','bitkhan']
    if not all (key in json for key in transaction_keys):
        return 'Some elements are missing in the transaction', 400
    block_id = blockchain.add_transaction(json['sender'], json['receiver'], json['bitkhan'])
    response = {'message': f'This transaction will be added to Block {block_id}'}
    return jsonify(response), 201

@app.route('/addtransaction', methods = ['GET'])
def transaction_form():
    return render_template('add_transaction.html')

@app.route('/addtransaction', methods = ['POST'])
def transaction_form_post():
        sender = request.form['sender']
        receiver = request.form['receiver']
        bitkhan = request.form['bitkhan']
        #print(type(bitkhan))
        if (sender!="")and(receiver!="")and(isfloat(bitkhan)):
            block_id = blockchain.add_transaction(sender,receiver,bitkhan)
            text = 'This transaction will be added to Block: '+ str(block_id)
            data = [sender,receiver,bitkhan,text]
            return render_template('added_transaction.html',response=data)
        else:
            return render_template('add_transaction.html')

# Connecting new nodes
@app.route('/connect_node', methods = ['POST'])
def connect_node():
    json = request.get_json()
    nodes = json.get('nodes')
    if nodes is None:
        return "No node", 400
    for node in nodes:
        blockchain.add_node(node)
    response = {'message': 'All the nodes are now connected. The Bitkhan blockchain contains the following nodes:',
                'total_nodes': list(blockchain.nodes)}
    return jsonify(response), 201

@app.route('/', methods = ['GET'])
def load_main_page():
    return render_template('index.html')



# Running the App 
cron = Scheduler(daemon=True)
# Explicitly kick off the background thread
cron.start()

@cron.interval_schedule(seconds=10)
def replace_chain():
    is_chain_replaced = blockchain.consensus()
    #is_chain_replaced = blockchain.replace_chain()
    if is_chain_replaced:
        response = {'message': 'The Blockchain was replaced by the longest chain',
                    'new_chain': blockchain.chain}
    else:
        response = {'message': 'All good. No changes needed to the chain',
                    'current_blockchain': blockchain.chain}
    return jsonify(response),200

@cron.interval_schedule(seconds=10)
def mine_block():
    lengths = [len(blockchain.chain)]
    network = blockchain.nodes
    for node in network:
        try:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                lengths.append(response.json()['length'])
        except Exception:
            continue
    flag = False
    prev_length = lengths[0]
    for length in lengths:
        if length == prev_length:
            prev_length = length
            flag = True
        else:
            flag = False
            break
    if flag:
        previous_block = blockchain.get_previous_block()
        if(len(blockchain.transactions)>0):
            blockchain.add_transaction(sender = node_address, receiver = 'laptop_server2', bitkhan = 12.5)
            previous_hash = previous_block['hash']
            block = blockchain.create_block(previous_hash = previous_hash, nonce = 1)
            block = blockchain.add_to_chain(block)
            response = {'message': 'Congrats, you just a mined a block!',
                        'block_id': block['block_id'],
                        'timestamp': block['timestamp'],
                        'nonce': block['nonce'],
                        'previous_hash': block['previous_hash'],
                        'hash': block['hash'],
                        'transactions': block['transactions']}
            return jsonify(response), 200
        else:
            response = {'message': 'You cannot mine a block until a transaction happens here'}
            return jsonify(response), 200
    else:
        response = {'message': 'You cannot mine a block until the next chain update of all the nodes in this network'}
        return jsonify(response), 200
    
    
if __name__ == '__main__':
    app.run(host = '0.0.0.0', port=5000)
    cron.shutdown()
    