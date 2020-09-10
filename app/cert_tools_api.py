from typing import List, Optional
from functools import lru_cache
from fastapi import Depends, FastAPI
from cert_tools import instantiate_v3_alpha_certificate_batch, create_v3_alpha_certificate_template
from pydantic import BaseModel, Field
import configargparse
import os
import httpx
import json
import requests

app = FastAPI()



class Batch(BaseModel):
    publicKey: str = Field(description='Public bloxberg address where the Research Object Certificate token will be minted')
    recipient_name: Optional[str]
    email: Optional[str]
    SHA256: List[str] = Field(description= 'SHA256 Hashes of each file you wish to certify. One certificate will be generated per hash up to a maximum of 1000 in a single request', max_length=1000)
    enableIPFS: bool = Field(description= 'Set to true to enable posting certificate to IPFS. If set to false, will simply return certificates in the response.')

    class Config:
        schema_extra = {
            "example": {
                "publicKey": "0x69575606E8b8F0cAaA5A3BD1fc5D032024Bb85AF",
                "recipient_name": "Albert Einstein",
                "email": "einstein@mpg.de",
                "SHA256": ["0x0e4ded5319861c8daac00d425c53a16bd180a7d01a340a0e00f7dede40d2c9f6", "0xfda3124d5319861c8daac00d425c53a16bd180a7d01a340a0e00f7dede40d2c9f6"],
                "enableIPFS": True
            }
        }

##Full Workflow
@app.post("/createBloxbergCertificate")
async def createBloxbergCertificate(batch: Batch):
    if len(batch.SHA256) >= 1001:
        raise HTTPException(status_code=400, detail="You are trying to certify too many files at once, please limit to 1000 files per batch.")
    #create_v3_alpha_certificate_template(recipient_name, email)
    conf = create_v3_alpha_certificate_template.get_config()
    create_v3_alpha_certificate_template.write_certificate_template(conf, batch.recipient_name, batch.email)
    conf_instantiate = instantiate_v3_alpha_certificate_batch.get_config()
    uidArray = instantiate_v3_alpha_certificate_batch.instantiate_batch(conf_instantiate, batch.publicKey, batch.recipient_name, batch.email, batch.SHA256)

    url = "http://cert_issuer_api:80/issueBloxbergCertificate"
    
    payload = {"recipientPublickey": batch.publicKey, "unSignedCerts": uidArray, "enableIPFS": batch.enableIPFS }
    headers = {
  'Content-Type': 'application/json'
}
    payload = json.dumps(payload)

    # TODO: Currently a simple post request, but need to research message queues for microservices
    try:
        response = requests.request("POST", url, headers=headers, data = payload)
        encodedResponse = response.text.encode('utf8')
        jsonText = json.loads(encodedResponse)
        for x in uidArray:
            full_path_with_file = str(conf.abs_data_dir + '/' + 'unsigned_certificates/' + x + '.json')
            os.remove(full_path_with_file)     
    except:
        print(response)
        for x in uidArray:
            full_path_with_file = str(conf.abs_data_dir + '/' + 'unsigned_certificates/' + x + '.json')
            os.remove(full_path_with_file)
        raise HTTPException(status_code=404, detail="Couldn't get connect to cert-issuer microservice, your files were not certified.")

    # TODO: Make requests Async
    #async with httpx.AsyncClient() as client:
    #    r = await client.post(url, data = obj)
    #    print(r)
    for x in uidArray:
        full_path_with_file = str(conf.abs_data_dir + '/' + 'unsigned_certificates/' + x + '.json')
        os.remove(full_path_with_file)        

    return jsonText

## Test Certificate Generation Endpoint

@app.post("/createUnsignedCertificateBatchTest")
def createUnsignedCertificate(batch: Batch):
    #create_v3_alpha_certificate_template(recipient_name, email)
    conf = create_v3_alpha_certificate_template.get_config()
    create_v3_alpha_certificate_template.write_certificate_template(conf, batch.recipient_name, batch.email)
    conf_instantiate = instantiate_v3_alpha_certificate_batch.get_config()
    uidArray = instantiate_v3_alpha_certificate_batch.instantiate_batch(conf_instantiate, batch.publicKey, batch.recipient_name, batch.email, batch.SHA256)

    return uidArray
