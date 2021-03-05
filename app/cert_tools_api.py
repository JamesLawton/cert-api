from typing import List, Optional
from functools import lru_cache
from fastapi import Depends, FastAPI, Request, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse, Response, JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from cert_tools import instantiate_v3_alpha_certificate_batch, create_v3_alpha_certificate_template
from pydantic import BaseModel, Field, Json
from zipfile import ZipFile
from urllib.error import HTTPError
from lds_merkle_proof_2019.merkle_proof_2019 import MerkleProof2019
import configargparse
import uuid
import pyqrcode
import fitz
import io
import os
import httpx
import time
import json
import requests
import shutil

tags_metadata = [
    {
        "name": "certificate",
        "description": "Creates, transacts, and signs a research object certificate on the bloxberg blockchain. Hashes must be generated client side for each desired file and provided in an array. Each hash corresponds to one research object certificate returned in a JSON object array."
    },
    {
        "name": "pdf",
        "description": "Accepts as input the response from the createBloxbergCertificate endpoint, for example a research object JSON array."
    }
]

app = FastAPI(openapi_tags=tags_metadata)

origins = [
    "http://localhost:3001"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )

class Batch(BaseModel):
    publicKey: str = Field(
        description='Public bloxberg address where the Research Object Certificate token will be minted')
    crid: List[str] = Field(
        description='Cryptographic Identifier of each file you wish to certify. One certificate will be generated per hash up to a maximum of 5001 in a single request',
        max_length=5001)
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
        alias='@context',
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



##Full Workflow
@app.post("/createBloxbergCertificate", tags=['certificate'])
async def createBloxbergCertificate(batch: Batch):

    """
    Creates, transacts, and signs a research object certificate on the bloxberg blockchain. Hashes must be generated client side for each desired file and provided in an array. Each hash corresponds to one research object certificate returned in a JSON object array.
    """

    # Currently don't support IPFS due to performance and space issues.
    if batch.enableIPFS is True:
        raise HTTPException(status_code=400,
                            detail="IPFS is not supported currently due to performance and storage requirements.")
    # limit number of CRIDs to 1000
    print(len(batch.crid))
    if len(batch.crid) >= 5001:
        raise HTTPException(status_code=400,
                            detail="You are trying to certify too many files at once, please limit to 5000 files per batch.")

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
                                                                            batch.crid, batch.cridType, batch.metadataJson)
    else:
        uidArray = instantiate_v3_alpha_certificate_batch.instantiate_batch(conf_instantiate, batch.publicKey,
                                                                            batch.crid, batch.cridType)
    end = time.time()
    print(end - start)
    if python_environment == "production":
        cert_issuer_address = os.getenv("CERT_ISSUER_CONTAINER")
        url = "http://" + cert_issuer_address + "/issueBloxbergCertificate"
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
        print('Bad post request')
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

    return jsonText

# my  the files from given directory that matches the filter
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
        return

@app.post("/generatePDF", tags=['pdf'])
async def generatePDF(request: jsonCertificateBatch, background_tasks: BackgroundTasks):
    """
    Accepts as input the response from the createBloxbergCertificate endpoint, for example a research object JSON array.
    """

    requestJson = request.json()
    certificateObject = json.loads(requestJson)
    uidArray = []
    for certificate in certificateObject:
        certificate['@context'] = certificate.pop('context')
        generatedID = str(uuid.uuid1())
        uidArray.append(generatedID)
        stringCert = json.dumps(certificate)
        bytestring = io.StringIO(stringCert)
        content = io.BytesIO(bytestring.read().encode('utf8'))
        await buildPDF(content, certificate, generatedID)


    tempZip = str(uuid.uuid1())
    filePathZip = "./sample_data/zipFiles/" + tempZip + ".zip"
    zipfilesindir("./sample_data/pdf_certificates", filePathZip, uidArray)

    resp = FileResponse(filePathZip, media_type="application/x-zip-compressed")
    resp.headers['Content-Disposition'] = 'attachment; filename=bloxbergResearchCertificates'

    file_path = str('./sample_data/pdf_certificates/')
    #Clean up after response
    background_tasks.add_task(removeTempFiles, file_path, filePathZip, uidArray)
    return resp

def removeTempFiles(file_path, filePathZip, uidArray):
    os.remove(filePathZip)
    for x in uidArray:
        full_path_with_file = str(file_path + x + '.pdf')
        print(full_path_with_file)
        os.remove(full_path_with_file)

async def buildPDF(content, certificate, generatedID):
    doc = fitz.open('./bloxbergDataCertificate.pdf')
    decodedProof = decode_proof(certificate['proof']['proofValue'])
    blockchainLink = decodedProof['anchors'][0]

    page = doc[0]
    p1 = fitz.Point(65, 330)
    p2 = fitz.Point(65, 380)
    p3 = fitz.Point(65, 430)
    p4 = fitz.Point(65, 480)
    crytographicIdentifier = certificate['crid']
    transactionIdentifier = blockchainLink.replace('blink:eth:bloxberg:', '')
    timestamp = certificate['proof']['created']
    merkleRoot = decodedProof['merkleRoot']

    page.insertText(p1,  # bottom-left of 1st char
                    crytographicIdentifier,  # the text (honors '\n')
                    fontname="helv",  # the default font
                    stroke_opacity=0.50,
                    fontsize=11,  # the default font size
                    rotate=0,  # also available: 90, 180, 270
                    )
    page.insertText(p2,  # bottom-left of 1st char
                    transactionIdentifier,  # the text (honors '\n')
                    fontname="helv",  # the default font
                    stroke_opacity=0.50,
                    fontsize=11,  # the default font size
                    rotate=0,  # also available: 90, 180, 270
                    )
    page.insertText(p3,  # bottom-left of 1st char
                    timestamp,  # the text (honors '\n')
                    fontname="helv",  # the default font
                    stroke_opacity=0.50,
                    fontsize=11,  # the default font size
                    rotate=0,  # also available: 90, 180, 270
                    )
    page.insertText(p4,  # bottom-left of 1st char
                    merkleRoot,  # the text (honors '\n')
                    fontname="helv",  # the default font
                    stroke_opacity=0.50,
                    fontsize=11,  # the default font size
                    rotate=0,  # also available: 90, 180, 270
                    )

    #QRCode Generation
    url = pyqrcode.create('https://certify.bloxberg.org/verify', error='L', version=27)
    buffer = io.BytesIO()
    url.png(buffer)


    #QR code embedding
    rect = fitz.Rect(575, 298, 775, 498)     # where we want to put the image
    pix = fitz.Pixmap(buffer.getvalue())        # any supported image file
    page.insertImage(rect, pixmap=pix, overlay=True)   # insert image
    doc.embeddedFileAdd("bloxbergJSONCertificate", content)
    doc.save('./sample_data/pdf_certificates/' + generatedID + '.pdf', garbage=4, deflate=True)

def decode_proof(proofEncoded):
    mp2019 = MerkleProof2019()
    check_decoded = mp2019.decode(proofEncoded)
    return check_decoded