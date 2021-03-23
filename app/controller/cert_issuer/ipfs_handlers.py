def add_file_ipfs(cert_path):
    ipfs_batch_file = "./data/meta_certificates/" + str(uuid.uuid1()) + '.json'
    ipfs_object = {"file_certifications": []}
    # Important to put name of IPFS container
    client = ipfshttpclient.connect('/dns/ipfs/tcp/5001')
    hash = client.add(cert_path)
    return hash['Hash']

def update_ipfs_link(token_id, token_uri):
    config = get_config()
    print(config.unsigned_certificates_dir)
    certificate_batch_handler, transaction_handler, connector = \
        ethereum_sc.instantiate_blockchain_handlers(config)
    # calling the smart contract to update the token uri for the token id
    cert_issuer.issue_certificates.update_token_uri(config, certificate_batch_handler, transaction_handler, token_id,
                                           token_uri)
    return

##Experimental IPNS - IPNS is still in Alpha so it is relatively slow. Not recommended for production
# TODO: Implement key rotation
def add_file_ipns(ipfsHash, generateKey, newKey=None):
    client = ipfshttpclient.connect('/dns/ipfs/tcp/5001')
    if generateKey is True:
        newKey = str(uuid.uuid1())
        client.key.gen(newKey, "rsa")["Name"]
    tempAddress = '/ipfs/' + ipfsHash
    ipnshash = client.name.publish(tempAddress, key=newKey, timeout=300)
    return ipnshash, newKey