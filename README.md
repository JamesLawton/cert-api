# cert-api
API for issuing bloxberg certificates via Blockcerts

The API utilizes modified Blockcerts repositories for issuing bloxberg specific certifications.
Each repository (cert-issuer & cert-tools) has it's own api service.

The services can be started by running:

`
docker-compose -f certify-api.yml up
`

This will generate two services, cert-tools for issuing batches available at localhost:7000/docs, and cert-issuer for posting to bloxberg at localhost:7001/docs.

It is assumed that the directory structure looks like

```
.
├── cert-api
├── cert-deployer
├── cert-issuer
├── cert-tools

```
