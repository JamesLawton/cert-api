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
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
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

def get_config():
    global config
    if config == None:
        config = cert_issuer.config.get_config()
    return config

@app.post("/issue")
def issue(request: Request):
    config = get_config()
    certificate_batch_handler, transaction_handler, connector = \
            ethereum_sc.instantiate_blockchain_handlers(config)
            #Removed File mode from ethereum_sc
            #bitcoin.instantiate_blockchain_handlers(config, False)
    certificate_batch_handler.set_certificates_in_batch(request.json)
    #return tx id, could also return proof
    return cert_issuer.issue_certificates.issue(config, certificate_batch_handler, transaction_handler)
    #return json.dumps(certificate_batch_handler.proof)
