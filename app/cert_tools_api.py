from typing import List, Optional
from functools import lru_cache
from fastapi import Depends, FastAPI, HTTPException
from cert_tools import instantiate_v3_alpha_certificate_batch, create_v3_alpha_certificate_template
from pydantic import BaseModel, Field, Json
from urllib.error import HTTPError
import configargparse
import os
import httpx
import time
import json
import requests

app = FastAPI()



class Batch(BaseModel):
    publicKey: str = Field(description='Public bloxberg address where the Research Object Certificate token will be minted')
    crid: List[str] = Field(description= 'Cryptographic Identifier of each file you wish to certify. One certificate will be generated per hash up to a maximum of 1000 in a single request', max_length=1000)
    cridType: Optional[str] = Field(description='If crid is not self-describing, provide the type of cryptographic function you used to generate the cryptographic identifier. Plesae use the name field from the multihash list to ensure compatibility: https://github.com/multiformats/multicodec/blob/master/table.csv')
    enableIPFS: bool = Field(description= 'EXPERIMENTAL: Set to true to enable posting certificate to IPFS. If set to false, will simply return certificates in the response. By default, this is disabled on the server due to performance and storage problems with IPFS')
    metadataJson: Optional[Json] = Field(description='Provide optional metadata to describe the research object batch in more detail that will be included in the certificate.')


    class Config:
        schema_extra = {
            "example": {
                "publicKey": "0x69575606E8b8F0cAaA5A3BD1fc5D032024Bb85AF",
                "crid": ["0x0e4ded5319861c8daac00d425c53a16bd180a7d01a340a0e00f7dede40d2c9f6", "0xfda3124d5319861c8daac00d425c53a16bd180a7d01a340a0e00f7dede40d2c9f6"],
                "cridType": "sha2-256",
                "enableIPFS": False,
                "metadataJson": "{\"authors\":\"Albert Einstein\"}"
            }
        }

async def issueRequest(url, headers, payload):
    response = requests.request("POST", url, headers=headers, data = payload)
    encodedResponse = response.text.encode('utf8')
    jsonText = json.loads(encodedResponse)
    # async with httpx.AsyncClient() as client:
    #     response = await client.post(url, headers=headers, data=payload)
    #     encodedResponse = await response.text.encode('utf8')
    #     jsonText = await json.loads(encodedResponse)
    return jsonText


##Full Workflow
@app.post("/createBloxbergCertificate")
async def createBloxbergCertificate(batch: Batch):
    #Currently don't support IPFS due to performance and space issues.
    if batch.enableIPFS is True:
        raise HTTPException(status_code=400, detail="IPFS is not supported currently due to performance and storage requirements.")
    #limit number of CRIDs to 1000
    if len(batch.crid) >= 101:
        raise HTTPException(status_code=400, detail="You are trying to certify too many files at once, please limit to 1000 files per batch.")

    conf = create_v3_alpha_certificate_template.get_config()

    python_environment = os.getenv("app")
    if python_environment == "production":
        full_path_with_file = str(conf.abs_data_dir + '/' + 'unsigned_certificates/')
        for file_name in os.listdir(full_path_with_file):
            if file_name.endswith('.json'):
                print(full_path_with_file + file_name)
                os.remove(full_path_with_file + file_name)

    start = time.time()
    print("generating unsigned certs")
    create_v3_alpha_certificate_template.write_certificate_template(conf, batch.publicKey)
    conf_instantiate = instantiate_v3_alpha_certificate_batch.get_config()
    if batch.metadataJson is not None:
        uidArray = instantiate_v3_alpha_certificate_batch.instantiate_batch(conf_instantiate, batch.publicKey, batch.crid, batch.metadataJson)
    else:
        uidArray = instantiate_v3_alpha_certificate_batch.instantiate_batch(conf_instantiate, batch.publicKey, batch.crid)

    end = time.time()
    print(end - start)
    url = "http://cert_issuer_api:80/issueBloxbergCertificate"
    
    payload = {"recipientPublickey": batch.publicKey, "unSignedCerts": uidArray, "enableIPFS": batch.enableIPFS }
    headers = {
  'Content-Type': 'application/json'
}
    payload = json.dumps(payload)
    start2 = time.time()
    print('starting cert-issuance')
    # TODO: Currently a simple post request, but need to research message queues for microservices
    try:
        jsonText = await issueRequest(url, headers, payload)
        for x in uidArray:
            full_path_with_file = str(conf.abs_data_dir + '/' + 'unsigned_certificates/' + x + '.json')
            os.remove(full_path_with_file)
    except Exception as e:
        print(e)
        for x in uidArray:
            full_path_with_file = str(conf.abs_data_dir + '/' + 'unsigned_certificates/' + x + '.json')
            os.remove(full_path_with_file)
        raise HTTPException(status_code=404, detail="Certifying batch to the blockchain failed.")
    end2 = time.time()
    print(end2 - start2)
    # TODO: Make requests Async

    return jsonText

## Test Certificate Generation Endpoint with issuance
@app.post("/createUnsignedCertificateBatchTest")
def createUnsignedCertificate(batch: Batch):
    #create_v3_alpha_certificate_template(recipient_name, email)
    conf = create_v3_alpha_certificate_template.get_config()
    create_v3_alpha_certificate_template.write_certificate_template(conf, batch.recipient_name, batch.email)
    conf_instantiate = instantiate_v3_alpha_certificate_batch.get_config()
    uidArray = instantiate_v3_alpha_certificate_batch.instantiate_batch(conf_instantiate, batch.publicKey, batch.recipient_name, batch.email, batch.crid)

    return uidArray
