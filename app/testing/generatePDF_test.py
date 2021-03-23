import pytest
import httpx
import requests
import asyncio
import time
from zipfile import ZipFile
from jsonschema import validate

from os.path import join, dirname

import json
#from app.testing import valid_certificate_schema

from app.controller.cert_tools.generate_unsigned_certificate import createBloxbergCertificate



@pytest.mark.asyncio
async def test_call_pdf_single():
    test_request_payload = [
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
]

    test_payload = json.dumps(test_request_payload)

    headers = {
        'Content-Type': 'application/json'
    }
    url = "http://localhost:7000/generatePDF"

    async with httpx.AsyncClient() as session:  # use httpx
        response = await session.request(method='POST', url=url, headers=headers, data=test_payload, timeout=None)
    assert response.status_code == 200
    return response


@pytest.mark.asyncio
async def test_call_pdf_1000():
    test_request_payload = _load_json_schema("./generate_pdf_1000.json")

    test_payload = json.dumps(test_request_payload)

    headers = {
        'Content-Type': 'application/json'
    }
    url = "http://localhost:7000/generatePDF"
    start = time.time()  # start time for timing event

    async with httpx.AsyncClient() as session:  # use httpx
        response = await session.request(method='POST', url=url, headers=headers, data=test_payload, timeout=None)
    print(f' 1000 PDFs generated in {time.time() - start} seconds')
    assert response.status_code == 200
    return response


@pytest.mark.asyncio
async def test_concurrent_requests_pdf():
    max_length = 4
    for i in range(1, max_length):
        start = time.time()  # start time for timing event
        async with httpx.AsyncClient() as session:  # use httpx
            responses = await asyncio.gather(*[call_generate_pdf(session) for x in range(i)])
        print(f'{i} call(s) in {time.time() - start} seconds')
    print(responses)
    assert len(responses) == max_length - 1


async def call_generate_pdf(session):
    test_request_payload = [
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
]

    test_payload = json.dumps(test_request_payload)

    headers = {
        'Content-Type': 'application/json'
    }
    url = "http://localhost:7000/generatePDF"

    response = await session.request(method='POST', url=url, headers=headers, data=test_payload, timeout=None)


    return response


def _load_json_schema(filename):
    """ Loads the given schema file """

    relative_path = join('.', filename)
    absolute_path = join(dirname(__file__), relative_path)

    with open(absolute_path) as schema_file:
        return json.loads(schema_file.read())