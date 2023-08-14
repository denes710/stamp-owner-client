import json
import os
import requests

from web3 import Web3

from dotenv import load_dotenv
load_dotenv()

node_url = os.getenv("NODE_URL")
private_key = os.getenv("PRIVATE_KEY")
public_key = os.getenv("PUBLIC_KEY")
stamper_addr = os.getenv("STAMPER_ADDR")
client_endpoint = os.getenv("CLIENT_ENDPOINT")

# get the last secret token for the stamp
response = requests.get(client_endpoint)
response_json = response.json()
request_uri = response_json["request_uri"]
uid = response_json["uid"]
secret_token = response_json["secret_token"]
print("Client responed with request uri: {}, uid: {}, secret token: {}".format(request_uri, uid, secret_token))

# get the delegated attestation
request_input = {
    "uid": uid,
    "receipent" : public_key
}
headers = {"Authorization": "Bearer {}".format(secret_token)}
response = requests.get(request_uri, data=json.dumps(request_input), headers=headers)
deleg_attest = response.json()["delegated_attestation"]
print("Server responded with json: {}".format(response_json))

# send the delegated attestation
web3 = Web3(Web3.HTTPProvider(node_url))
if web3.isConnected():
    print("-" * 50)
    print("Web3 Connection Successful")
    print("-" * 50)
else:
    print("Web Connection Failed")
    exit()

nonce = web3.eth.get_transaction_count(public_key)
# Initialize contract ABI and address
f = open("abis/Stamper.json")
stamper_abi = json.load(f)["abi"]
# Create smart contract instance
stamper_contract = web3.eth.contract(address=web3.toChecksumAddress(stamper_addr), abi=stamper_abi)
# initialize the chain id, we need it to build the transaction for replay protection
chain_id = web3.eth.chain_id

stamp_input = (
    deleg_attest["schema"],
    (
        str(web3.toChecksumAddress(deleg_attest["data"]["recipient"])),
        int(deleg_attest["data"]["expirationTime"]),
        bool(deleg_attest["data"]["revocable"]),
        deleg_attest["data"]["refUID"],
        bytes(deleg_attest["data"]["data"].encode()),
        int(deleg_attest["data"]["value"])
    ),
    (
        int(deleg_attest["signature"]["v"]),
        hex(deleg_attest["signature"]["r"]),
        hex(deleg_attest["signature"]["s"])
    ),
    web3.toChecksumAddress(deleg_attest["attester"]),
)

print(stamp_input)
call_function = stamper_contract.functions.stamp(stamp_input).buildTransaction({"chainId": chain_id, "from": public_key, "nonce": nonce})

# Sign transaction
signed_tx = web3.eth.account.sign_transaction(call_function, private_key=private_key)
# Send transaction
send_tx = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

# Wait for transaction receipt
tx_receipt = web3.eth.wait_for_transaction_receipt(send_tx)
print(tx_receipt) # Optional