import { createPublicClient, createWalletClient, http } from "@arkiv-network/sdk";
import { privateKeyToAccount } from "@arkiv-network/sdk/accounts";
import { ExpirationTime, jsonToPayload } from "@arkiv-network/sdk/utils";
import * as viem from "viem";
import * as fs from "fs";
import * as path from "path";

// Define the custom Dev chain
const dev = {
  id: 12345,
  name: "Arkiv Dev",
  nativeCurrency: {
    name: "Ethereum",
    symbol: "ETH",
    decimals: 18,
  },
  rpcUrls: {
    default: {
      http: ["http://127.0.0.1:8545"],
      webSocket: ["wss://127.0.0.1:8545"],
    },
  },
  testnet: true,
  network: "dev",
} as const;

// Define interface for the JSON structure
interface AccountData {
  address: string;
  privateKey: string;
}

async function main() {
  // 1. Load accounts from keys.json
  const keysFilePath = path.join(__dirname, "keys.json");
  console.log(`Loading accounts from ${keysFilePath}...`);

  const rawData = fs.readFileSync(keysFilePath, "utf-8");
  const accounts: AccountData[] = JSON.parse(rawData);

  // 2. Initialize the Public Client (shared for reading state)
  const publicClient = createPublicClient({
    chain: dev,
    transport: http(),
  });

  console.log(`Found ${accounts.length} accounts. Starting transactions...\n`);

  // 3. Iterate through each account and perform a transaction
  for (const [index, acc] of accounts.entries()) {
    try {
      console.log(`--- Processing Account ${index + 1}: ${acc.address} ---`);

      // Create Wallet Client for specific account
      const account = privateKeyToAccount(acc.privateKey as `0x${string}`);
      const client = createWalletClient({
        chain: dev,
        transport: http(),
        account: account,
      });

      // Create a unique entity for this user
      // We append the index to the ID to ensure uniqueness
      const uniqueId = `doc-hackathon-${index + 1}`;

      const { entityKey, txHash } = await client.createEntity({
        payload: jsonToPayload({
          entity: {
            entityType: "document",
            entityId: uniqueId,
            entityContent: `Hello from DevConnect Hackathon! Account ${acc.address} says hi.`,
          },
        }),
        contentType: "application/json",
        attributes: [
          { key: "category", value: "documentation" },
          { key: "author", value: acc.address },
          { key: "batch", value: "1.0" },
        ],
        expiresIn: ExpirationTime.fromDays(30),
      });

      console.log(`✅ Transaction sent!`);
      console.log(`   Tx Hash: ${txHash}`);
      console.log(`   Entity Key: ${entityKey}`);

      // Optional: Verify creation
      const newEntity = await publicClient.getEntity(entityKey);
      console.log(`   Verified On-Chain: ID matches '${newEntity?.payload?.entity?.entityId}'\n`);

    } catch (error) {
      console.error(`❌ Error processing account ${acc.address}:`, error);
    }
  }
}

main().catch((error) => {
  console.error("Error executing main function:", error);
  process.exit(1);
});