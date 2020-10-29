from typing import List, Optional
from functools import lru_cache
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from cert_tools import instantiate_v3_alpha_certificate_batch, create_v3_alpha_certificate_template
from pydantic import BaseModel, Field, Json
from zipfile import ZipFile
from urllib.error import HTTPError
import configargparse
import uuid
import fitz
import io
import os
import httpx
import time
import json
import requests
import shutil

app = FastAPI()


class Batch(BaseModel):
    publicKey: str = Field(
        description='Public bloxberg address where the Research Object Certificate token will be minted')
    crid: List[str] = Field(
        description='Cryptographic Identifier of each file you wish to certify. One certificate will be generated per hash up to a maximum of 1000 in a single request',
        max_length=1000)
    cridType: Optional[str] = Field(
        description='If crid is not self-describing, provide the type of cryptographic function you used to generate the cryptographic identifier.'
                    ' Please use the name field from the multihash list to ensure compatibility: https://github.com/multiformats/multicodec/blob/master/table.csv')
    enableIPFS: bool = Field(
        description='EXPERIMENTAL: Set to true to enable posting certificate to IPFS. If set to false, will simply return certificates in the response.'
                    ' By default, this is disabled on the server due to performance and storage problems with IPFS')
    metadataJson: Optional[Json] = Field(
        description='Provide optional metadata to describe the research object batch in more detail '
                    'that will be included in the certificate.')

    class Config:
        schema_extra = {
            "example": {
                "publicKey": "0x69575606E8b8F0cAaA5A3BD1fc5D032024Bb85AF",
                "crid": ["0x0e4ded5319861c8daac00d425c53a16bd180a7d01a340a0e00f7dede40d2c9f6",
                         "0xfda3124d5319861c8daac00d425c53a16bd180a7d01a340a0e00f7dede40d2c9f6"],
                "cridType": "sha2-256",
                "enableIPFS": False,
                "metadataJson": "{\"authors\":\"Albert Einstein\"}"
            }
        }


class jsonCertificate(BaseModel):
    context: Optional[List[str]] = Field(
        description='Relevant JSON-LD context links in order to validate Verifiable Credentials according to their spec.'
    )
    id: str
    type: List[str]
    issuer: str
    issuanceDate: str
    credentialSubject: dict
    displayHtml: Optional[str]
    crid: str
    cridType: Optional[str]
    metadataJson: Optional[str]
    proof: dict


    class Config:
        schema_extra = {
            "example":
                    {
                        "@context": [
                            "https://www.w3.org/2018/credentials/v1",
                            "https://w3id.org/blockcerts/schema/3.0-alpha/context.json"
                        ],
                        "type": [
                            "VerifiableCredential",
                            "BlockcertsCredential"
                        ],
                        "issuer": "https://raw.githubusercontent.com/bloxberg-org/issuer_json/master/issuer.json",
                        "issuanceDate": "2020-10-28T14:30:34.011731+00:00",
                        "credentialSubject": {
                            "id": "https://blockexplorer.bloxberg.org/address/0x69575606E8b8F0cAaA5A3BD1fc5D032024Bb85AF",
                            "issuingOrg": {
                                "id": "https://bloxberg.org"
                            }
                        },
                        "displayHtml": "<section class=\"text\" style=\"margin-top:24px;width:100%;display:inline-block;\"><span style=\"display:block;font-family:Helvetica, sans-serif;font-weight:bold;font-size:2.5em;text-align:left;text-transform:none;color:#4e5f6b;margin:0 auto;width:100%\">Research Object Certificate</span></section><section class=\"text\" style=\"margin-top:12px;width:100%;display:inline-block;\"><span style=\"display:block;font-family:Helvetica, sans-serif;font-weight:normal;font-size:1em;text-align:left;text-transform:none;color:#4e5f6b;float: left;width:100%\">This bloxberg certificate serves as a proof of existence that the data corresponding to the  cryptographic identifier were transacted on the bloxberg blockchain at the issued time.</span></section><h1>bloxberg Certificate</h1><h2></h2></div>",
                        "id": "https://bloxberg.org",
                        "crid": "0xfda3124d5319861c8daac00d425c53a16bd180a7d01a340a0e00f7dede40d2c9f6",
                        "cridType": "sha-256",
                        "metadataJson": "{\"authors\": \"Albert Einstein\"}",
                        "proof": {
                            "type": "MerkleProof2019",
                            "created": "2020-10-28T14:30:40.469960",
                            "proofValue": "z2LuLBVSfogU8YhUevw7i7eo94141kAPwfYuY7XGbqmy6PJvWiEvy9Q5C9niJ6B4Cy5PeHo8rC5azvniXW75WxHhziZGRj6jK7G5i3X2EdyurnhSHwTAhjCEo6gE4oFBQUhb65ZcWmidNBVYqbvHCnmFaY7SKiUmmuELmC9dA3Z89X1b1QVquiC8yrqFdMeBptPP8tMk9StHKQfG1X2u4JzWSTmR4RVKnh4XAo8UitRiz8zeQSNZJuQ2kTg2PTMxnigap4US5vVL5UKESKUSB9kAvk1YpBfrzuEtEiVqFWWMk6V48MYkBwP86HnY4yh6LwM31J6c6NyNeUcVmUAjhMFenaFZXoWvkzj6nUmRVcLdRmARkWCAuWikVTbgri4Cw8p7cezHXvE9mmvuC9HYfB",
                            "proofPurpose": "assertionMethod",
                            "verificationMethod": "ecdsa-koblitz-pubkey:0xD748BF41264b906093460923169643f45BDbC32e",
                            "ens_name": "mpdl.berg"
                        }
                    }
                }

class jsonCertificateBatch(BaseModel):
    __root__: Optional[List[jsonCertificate]]

async def issueRequest(url, headers, payload):
    response = requests.request("POST", url, headers=headers, data=payload)
    encodedResponse = response.text.encode('utf8')
    jsonText = json.loads(encodedResponse)
    # async with httpx.AsyncClient() as client:
    #     response = await client.post(url, headers=headers, data=payload)
    #     encodedResponse = await response.text.encode('utf8')
    #     jsonText = await json.loads(encodedResponse)
    return jsonText

# Zip the files from given directory that matches the filter
def zipfilesindir(dirName, zipFileName, filter=None):
    # create a ZipFile object
    with ZipFile(zipFileName, 'w') as zipObj:
        # Iterate over all the files in directory
        for folderName, subfolders, filenames in os.walk(dirName):
            for filename in filenames:
                removedExtension = os.path.splitext(filename)[0]
                if removedExtension in filter or filter is None:
                    # create complete filepath of file in directory
                    filePath = os.path.join(folderName, filename)
                    # Add file to zip
                    zipObj.write(filePath, os.path.basename(filePath))

##Full Workflow
@app.post("/createBloxbergCertificate")
async def createBloxbergCertificate(batch: Batch):
    # Currently don't support IPFS due to performance and space issues.
    if batch.enableIPFS is True:
        raise HTTPException(status_code=400,
                            detail="IPFS is not supported currently due to performance and storage requirements.")
    # limit number of CRIDs to 1000
    if len(batch.crid) >= 101:
        raise HTTPException(status_code=400,
                            detail="You are trying to certify too many files at once, please limit to 1000 files per batch.")

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
        uidArray = instantiate_v3_alpha_certificate_batch.instantiate_batch(conf_instantiate, batch.publicKey,
                                                                            batch.crid, batch.metadataJson)
    else:
        uidArray = instantiate_v3_alpha_certificate_batch.instantiate_batch(conf_instantiate, batch.publicKey,
                                                                            batch.crid)
    end = time.time()
    print(end - start)
    if python_environment == "production":
        url = "http://cert_issuer_api:7001/issueBloxbergCertificate"
    else:
        url = "http://cert_issuer_api:80/issueBloxbergCertificate"

    payload = {"recipientPublickey": batch.publicKey, "unSignedCerts": uidArray, "enableIPFS": batch.enableIPFS
              }
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
        try:
            for x in uidArray:
                full_path_with_file = str(conf.abs_data_dir + '/' + 'unsigned_certificates/' + x + '.json')
                os.remove(full_path_with_file)
                full_path_with_pdf = str(conf.abs_data_dir + '/' + 'pdf_certificates/' + x + '.pdf')
                os.remove(full_path_with_pdf)
        except Exception as e:
            print(e)
        raise HTTPException(status_code=404, detail="Certifying batch to the blockchain failed.")
    end2 = time.time()
    print(end2 - start2)
    # TODO: Make requests Async

    return jsonText



@app.post("/generatePDF")
def generatePDF(request: jsonCertificateBatch):
    requestJson = request.json()
    certificateObject = json.loads(requestJson)
    uidArray = []
    #for certificate in request.__root__:
    for certificate in certificateObject:
        generatedID = str(uuid.uuid1())
        uidArray.append(generatedID)
        stringCert = json.dumps(certificate)
        bytestring = io.StringIO(stringCert)
        content = io.BytesIO(bytestring.read().encode('utf8'))
        doc = fitz.open('./bloxbergDataCertificate.pdf')
        doc.embeddedFileAdd("bloxbergJSONCertificate", content)
        doc.save('./sample_data/pdf_certificates/' + generatedID + '.pdf', garbage=4, deflate=1)

    filePathZip = "./sample_data/bloxbergResearchCertificates.zip"
    zipfilesindir("./sample_data/pdf_certificates", filePathZip, uidArray)
    resp = FileResponse(filePathZip, media_type="application/x-zip-compressed")
    resp.headers['Content-Disposition'] = 'attachment; filename=bloxbergResearchCertificates'

    full_path_with_file = str('./sample_data/pdf_certificates/')

    for file_name in os.listdir(full_path_with_file):
        if file_name.endswith('.pdf'):
            print(full_path_with_file + file_name)
            os.remove(full_path_with_file + file_name)

    return resp
