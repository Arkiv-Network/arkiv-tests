import json
import os
import subprocess

# 1. Setup Configuration
OUTPUT_DIR = "deploy-config"
INTENT_FILE = os.path.join(OUTPUT_DIR, "intent.toml")
KEYS_FILE = os.path.join(OUTPUT_DIR, "keys.txt")

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def create_keypair():
    result = subprocess.run(
        ["cast", "wallet", "new", "--json"],
        capture_output=True,
        text=True,
        check=True
    )
    # Parse the JSON output (cast returns a list of wallets)
    wallet_data = json.loads(result.stdout)[0]

    # Extract variables matching your original format
    addr = wallet_data["address"].lower()
    priv = wallet_data["private_key"]
    return addr, priv

# 2. Generate unique addresses for specific roles
admin_addr, admin_key = create_keypair()
batcher_addr, batcher_key = create_keypair()
proposer_addr, proposer_key = create_keypair()
sequencer_addr, sequencer_key = create_keypair()
challenger_addr, challenger_key = create_keypair() # New Challenger Role

# 3. Define the Intent Content
intent_content = f'''configType = "custom"
l1ChainID = 31337
fundDevAccounts = true

l1ContractsLocator = "https://storage.googleapis.com/oplabs-contract-artifacts/artifacts-v1-579f43b5bbb43e74216b7ed33125280567df86eaf00f7621f354e4a68c07323e.tar.gz"

l2ContractsLocator = "https://storage.googleapis.com/oplabs-contract-artifacts/artifacts-v1-579f43b5bbb43e74216b7ed33125280567df86eaf00f7621f354e4a68c07323e.tar.gz"

[superchainRoles]
  ProxyAdminOwner = "{admin_addr}"
  SuperchainProxyAdminOwner = "{admin_addr}"
  SuperchainGuardian = "{admin_addr}"
  ProtocolVersionsOwner = "{admin_addr}"
  Challenger = "{challenger_addr}"

[[chains]]
  id = "0x000000000000000000000000000000000000000000000000000000000000a455"
  baseFeeVaultRecipient = "{admin_addr}"
  l1FeeVaultRecipient = "{admin_addr}"
  sequencerFeeVaultRecipient = "{admin_addr}"
  
  # Standard OP Stack Fee Params
  eip1559Denominator = 50
  eip1559DenominatorCanyon = 250
  eip1559Elasticity = 6
  gasLimit = 30000000
  
  [chains.roles]
    l1ProxyAdminOwner = "{admin_addr}"
    l2ProxyAdminOwner = "{admin_addr}"
    systemConfigOwner = "{admin_addr}"
    unsafeBlockSigner = "{sequencer_addr}"
    batcher = "{batcher_addr}"
    proposer = "{proposer_addr}"
    challenger = "{challenger_addr}"
'''

# 4. Save to Files
with open(INTENT_FILE, "w") as f:
    f.write(intent_content)

with open(KEYS_FILE, "w") as f:
    f.write(f"ADMIN_PRIVATE_KEY={admin_key}\n")
    f.write(f"BATCHER_PRIVATE_KEY={batcher_key}\n")
    f.write(f"PROPOSER_PRIVATE_KEY={proposer_key}\n")
    f.write(f"SEQUENCER_PRIVATE_KEY={sequencer_key}\n")
    f.write(f"CHALLENGER_PRIVATE_KEY={challenger_key}\n")

print(f"✅ Intent and Keys generated with Challenger role.")