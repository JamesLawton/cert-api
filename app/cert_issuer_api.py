from typing import List, Optional
from functools import lru_cache
from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel
import json
import os
import ipfshttpclient
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

    class Config:
        schema_extra = {
            "example": {
                "recipientPublickey": "0x69575606E8b8F0cAaA5A3BD1fc5D032024Bb85AF",
                "unSignedCerts": ["45c5caba-378b-49eb-bf24-b0056d300f22", "150ed963-dfad-46ee-b242-dfa2eff98671"],
            }
        }


def get_config():
    global config
    if config == None:
        config = cert_issuer.config.get_config()
    return config

def remove_certificates():
    return

def update_ipfs_link():


    return    

def add_file_ipfs(cert_json):
    #Important to put name of IPFS container
    client = ipfshttpclient.connect('/dns/ipfs/tcp/5001')
    hash = client.add_json(cert_json)
    print(hash)
    return hash

@app.post("/issue")
def issue(createToken: createToken, request: Request):
    config = get_config()
    certificate_batch_handler, transaction_handler, connector = \
            ethereum_sc.instantiate_blockchain_handlers(config)
            #Removed File mode from ethereum_sc
            #bitcoin.instantiate_blockchain_handlers(config, False)
    certificate_batch_handler.set_certificates_in_batch(request.json)
    cert_issuer.issue_certificates.issue(config, certificate_batch_handler, transaction_handler, createToken.recipientPublickey)

    #Retrieve file path of certified transaction
    blockchain_file_path = config.blockchain_certificates_dir
    #fileID = certificate_batch_handler.certificates_to_issue.popitem(last=False)[0]
    json_data = []
    for fileID in certificate_batch_handler.certificates_to_issue:
        full_path_with_file = str(blockchain_file_path + '/' + fileID + '.json')
    
        with open(full_path_with_file) as f:
            d = json.load(f)
        #Save JSON Certificate to IPFS
        ipfsHash = add_file_ipfs(d)
        json_data.append(d)
    return json_data

