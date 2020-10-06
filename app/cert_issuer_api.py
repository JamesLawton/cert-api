from typing import List, Optional
from functools import lru_cache
from fastapi import Depends, FastAPI, Request, HTTPException
from pydantic import BaseModel
import json
import os
import ipfshttpclient
import uuid
from fastapi.middleware.cors import CORSMiddleware

import cert_issuer.config
from cert_issuer.blockchain_handlers import ethereum_sc
import cert_issuer.issue_certificates

app = FastAPI()
config = None

origins = [
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class createToken(BaseModel):
    recipientPublickey: str
    unSignedCerts: List[str]
    enableIPFS: bool

    #Used only for Testing API, not for entire workflow.
    class Config:
        schema_extra = {
            "example": {
                "recipientPublickey": "0x69575606E8b8F0cAaA5A3BD1fc5D032024Bb85AF",
                "unSignedCerts": ["45c5caba-378b-49eb-bf24-b0056d300f22", "150ed963-dfad-46ee-b242-dfa2eff98671"],
                "enableIPFS": True
            }
        }

def get_config():
    global config
    if config == None:
        config = cert_issuer.config.get_config()
    return config

def update_ipfs_link(token_id, token_uri):
    config = get_config()
    print(config.unsigned_certificates_dir)
    certificate_batch_handler, transaction_handler, connector = \
            ethereum_sc.instantiate_blockchain_handlers(config)
    # calling the smart contract to update the token uri for the token id
    cert_issuer.issue_certificates.update_token_uri(config, certificate_batch_handler, transaction_handler, token_id, token_uri)
    return

def add_file_ipfs(cert_path):
    #Important to put name of IPFS container
    client = ipfshttpclient.connect('/dns/ipfs/tcp/5001')
    hash = client.add(cert_path)
    return hash['Hash']

##Experimental IPNS - IPNS is still in Alpha so it is relatively slow. Not recommended for production
# TODO: Implement key rotation
def add_file_ipns(ipfsHash, generateKey, newKey = None):
    client = ipfshttpclient.connect('/dns/ipfs/tcp/5001')
    if generateKey is True:
        newKey = str(uuid.uuid1())
        client.key.gen(newKey, "rsa")["Name"]
    tempAddress = '/ipfs/' + ipfsHash
    ipnshash = client.name.publish(tempAddress, key=newKey, timeout=300)
    return ipnshash, newKey

#Full Workflow - Called from cert_tools_api
@app.post("/issueBloxbergCertificate")
def issue(createToken: createToken, request: Request):
    print(request)
    config = get_config()
    certificate_batch_handler, transaction_handler, connector = \
            ethereum_sc.instantiate_blockchain_handlers(config)
        # file that stores the ipfs hashes of the certificates in the batch
    if createToken.enableIPFS is True:
        try:
            ipfs_batch_file = "./data/meta_certificates/" + str(uuid.uuid1()) + '.json'
            ipfs_object =  {"file_certifications": []}
            ipfsHash = add_file_ipfs("./data/meta_certificates/.placeholder")
            generateKey = True
            ipnsHash, generatedKey = add_file_ipns(ipfsHash, generateKey)
            print("Initial IPNS Commit")
            tokenURI = 'http://ipfs.io/ipns/' + ipnsHash['Name']
            print(tokenURI)
        except Exception as e:
            print(e)
            return "Couldn't add file to IPFS"
    else:
        tokenURI = 'https://bloxberg.org'
    try:
        certificate_batch_handler.set_certificates_in_batch(request.json)
        # delegating the issuing of the certificate to the respective transaction handler, that will call "createCertificate" on the smart contract
        (tx_id, token_id) = cert_issuer.issue_certificates.issue(config, certificate_batch_handler, transaction_handler, createToken.recipientPublickey, tokenURI)
    except:
        return "Issuing unsigned certificate batch to blockchain failed"
    #Retrieve file path of certified transaction
    blockchain_file_path = config.blockchain_certificates_dir
    json_data = []
    
    for fileID in certificate_batch_handler.certificates_to_issue:
        full_path_with_file = str(blockchain_file_path + '/' + fileID + '.json')
        if createToken.enableIPFS is True:
            ipfsHash = add_file_ipfs(full_path_with_file)

        with open(full_path_with_file) as f:
            d = json.load(f)
        #Save JSON Certificate to IPFS
        if createToken.enableIPFS is True:
            temp = ipfs_object["file_certifications"]
            y = {"id": fileID, "ipfsHash": 'http://ipfs.io/ipfs/' + ipfsHash, "crid": d["crid"]}
            temp.append(y)
        json_data.append(d)

    # write ipfs object into the ipfs batch file
    try:
        if createToken.enableIPFS is True:
            with open(ipfs_batch_file, 'w') as file:
                json.dump(ipfs_object, file)
            ipfs_batch_hash = add_file_ipfs(ipfs_batch_file)
            generateKey = False
            ipnsHash = add_file_ipns(ipfs_batch_hash, generateKey, newKey=generatedKey)
            print("Updated IPNS Hash")
            print(ipnsHash)
            #update_ipfs_link(token_id, 'http://ipfs.io/ipfs/' + ipfs_batch_hash)
    except:
        return "Updating IPNS link failed,"


    python_environment = os.getenv("app")
    if python_environment == "production":
        full_path_with_file = str(conf.blockchain_certificates_dir + '/')
        for file_name in listdir(full_path_with_file):
            if file_name.endswith('.json'):
                print(full_path_with_file + file_name)
                os.remove(full_path_with_file + file_name)

    return json_data

# Test Issuance Endpoint
@app.post("/issueTest")
def issue(createToken: createToken, request: Request):
    config = get_config()

    certificate_batch_handler, transaction_handler, connector = \
            ethereum_sc.instantiate_blockchain_handlers(config)
    
            #Removed File mode from ethereum_sc
            #bitcoin.instantiate_blockchain_handlers(config, False)
    certificate_batch_handler.set_certificates_in_batch(request.json)

    # delegating the issuing of the certificate to the respective transaction handler, that will call "createCertificate" on the smart contract 
    (tx_id, token_id) = cert_issuer.issue_certificates.issue(config, certificate_batch_handler, transaction_handler, createToken.recipientPublickey)

    # file that stores the ipfs hashes of the certificates in the batch
    ipfs_batch_file = "./data/meta_certificates/" + str(uuid.uuid1()) + '.json'
    #Retrieve file path of certified transaction
    blockchain_file_path = config.blockchain_certificates_dir
    json_data = []

    ipfs_object =  {"file_certifications": []}
    
    for fileID in certificate_batch_handler.certificates_to_issue:
        full_path_with_file = str(blockchain_file_path + '/' + fileID + '.json')         
        ipfsHash = add_file_ipfs(full_path_with_file)
        #add_file_ipns(ipfsHash)

        with open(full_path_with_file) as f:
            d = json.load(f)
        #Save JSON Certificate to IPFS
        temp = ipfs_object["file_certifications"]
        #ipfs_list.append('http://ipfs.io/ipfs/' + ipfsHash)
        y = {"id": fileID, "ipfsHash": 'http://ipfs.io/ipfs/' + ipfsHash, "crid": d["cridHash"]}
        temp.append(y)
        json_data.append(d)

    # write ipfs object into the ipfs batch file
    print(ipfs_object)
    with open(ipfs_batch_file, 'w') as file:
        json.dump(ipfs_object, file)

    ipfs_batch_hash = add_file_ipfs(ipfs_batch_file)
    
    update_ipfs_link(token_id, 'http://ipfs.io/ipfs/' + ipfs_batch_hash)

    return json_data
