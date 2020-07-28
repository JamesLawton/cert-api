from typing import List, Optional
from functools import lru_cache
from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel
import json
import os

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
    publicKey: str
    ipfsLinks: List[str]

    class Config:
        schema_extra = {
            "example": {
                "publicKey": "0x69575606E8b8F0cAaA5A3BD1fc5D032024Bb85AF",
                "ipfsLinks": ["0x0e4ded5319861c8daac00d425c53a16bd180a7d01a340a0e00f7dede40d2c9f6", "0xfda3124d5319861c8daac00d425c53a16bd180a7d01a340a0e00f7dede40d2c9f6"],
            }
        }


def get_config():
    global config
    if config == None:
        config = cert_issuer.config.get_config()
    return config

def remove_certificates():
    return

@app.post("/issue")
def issue(createToken: createToken, request: Request):
    config = get_config()
    certificate_batch_handler, transaction_handler, connector = \
            ethereum_sc.instantiate_blockchain_handlers(config)
            #Removed File mode from ethereum_sc
            #bitcoin.instantiate_blockchain_handlers(config, False)
    certificate_batch_handler.set_certificates_in_batch(request.json)
    #return tx id, could also return proof
    cert_issuer.issue_certificates.issue(config, certificate_batch_handler, transaction_handler, createToken.publicKey)
    blockchain_file_path = config.blockchain_certificates_dir
    fileID = certificate_batch_handler.certificates_to_issue.popitem(last=False)[0]
    print(config)
    full_path_with_file = str(blockchain_file_path + '/' + fileID + '.json')
    
    with open(full_path_with_file) as f:
        d = json.load(f)
    return d

