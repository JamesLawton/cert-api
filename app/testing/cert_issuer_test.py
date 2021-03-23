import pytest
import httpx
import requests
import asyncio
import time
from jsonschema import validate

from os.path import join, dirname

import json
#from app.testing import valid_certificate_schema

from app.controller.cert_tools.generate_unsigned_certificate import createBloxbergCertificate


@pytest.mark.asyncio
async def test_call_certificate_single():
    test_request_payload = {
        "publicKey": "0x69575606E8b8F0cAaA5A3BD1fc5D032024Bb85AF",
        "crid": [
    "0x0e4ded5319861c8daac00d425c53a16bd180a7d01a340a0e00f7dede40d2c9f6",
    "0xfda3124d5319861c8daac00d425c53a16bd180a7d01a340a0e00f7dede40d2c9f6"
  ],
        "cridType": "sha2-256",
        "enableIPFS": False,
        "metadataJson": "{\"authors\":\"Albert Einstein\"}"
    }

    test_payload = json.dumps(test_request_payload)

    headers = {
        'Content-Type': 'application/json'
    }
    url = "http://localhost:7000/createBloxbergCertificate"

    async with httpx.AsyncClient() as session:  # use httpx
        response = await session.request(method='POST', url=url, headers=headers, data=test_payload, timeout=None)
    encodedResponse = response.text.encode('utf8')
    jsonText = json.loads(encodedResponse)
    assert response.status_code == 200
    assert_valid_schema(jsonText, './valid_certificate_schema.json')
    return jsonText




@pytest.mark.asyncio
async def test_concurrent_requests_certificate():
    max_length = 4
    for i in range(1, max_length):
        start = time.time()  # start time for timing event
        async with httpx.AsyncClient() as session:  # use httpx
            responses = await asyncio.gather(*[call_certificate(session) for x in range(i)])
        print(f'{i} call(s) in {time.time() - start} seconds')
    print(responses)
    assert len(responses) == max_length - 1



async def call_certificate(session):
    test_request_payload = {
        "publicKey": "0x69575606E8b8F0cAaA5A3BD1fc5D032024Bb85AF",
        "crid": [
    "0x0e4ded5319861c8daac00d425c53a16bd180a7d01a340a0e00f7dede40d2c9f6",
            "test0x0e4ded5319861c8daac00d425c53a16bd180a7d01a340a0e00f7dede40d2c9f6"
        ],
        "cridType": "sha2-256",
        "enableIPFS": False,
        "metadataJson": "{\"authors\":\"Albert Einstein\"}"
    }

    test_payload = json.dumps(test_request_payload)

    headers = {
        'Content-Type': 'application/json'
    }
    url = "http://localhost:7000/createBloxbergCertificate"

    response = await session.request(method='POST', url=url, headers=headers, data=test_payload, timeout=None)
    encodedResponse = response.text.encode('utf8')
    jsonText = json.loads(encodedResponse)


    #Validation steps
    assert response.status_code == 200
    assert_valid_schema(jsonText, './valid_certificate_schema.json')

    return jsonText





def assert_valid_schema(data, schema_file):
    """ Checks whether the given data matches the schema """

    schema = _load_json_schema(schema_file)
    return validate(data, schema)


def _load_json_schema(filename):
    """ Loads the given schema file """

    relative_path = join('.', filename)
    absolute_path = join(dirname(__file__), relative_path)

    with open(absolute_path) as schema_file:
        return json.loads(schema_file.read())



# async def test_certification():
#     response = requests.ßget('http://localhost:7000/createBloxbergCertificate')
