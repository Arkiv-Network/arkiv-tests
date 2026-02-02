import {
  createPublicClient,
  createWalletClient,
  defineChain,
  http,
} from "@arkiv-network/sdk";
import { privateKeyToAccount } from "@arkiv-network/sdk/accounts";
import { ExpirationTime, jsonToPayload } from "@arkiv-network/sdk/utils";


async function main() {
  let privateKey = process.env.PRIVATE_KEY || "6df676dadffad9321e02bd00209e3cce4546a314c37e85f744b40dc25113f200";
  if (!privateKey) {
    throw new Error("PRIVATE_KEY is not set in the env");
  }
  privateKey = privateKey.replace('0x', '');

  const account = privateKeyToAccount(`0x${privateKey}`);

  const l3Testnet = defineChain({
    id: 31337,
    name: "Arkiv L3 Testnet",
    network: "l3-testnet",
    nativeCurrency: {
      name: "Golem",
      symbol: "GLM",
      decimals: 18,
    },
    rpcUrls: {
      default: {
        http: ["http://localhost:8545"],
      },
    },
  });

  // Create a wallet client to interact with Arkiv.
  const client = createWalletClient({
    chain: l3Testnet,
    transport: http(),
    account: account,
  });

  // Create a public client
  const publicClient = createPublicClient({
    chain: l3Testnet,
    transport: http(),
  });

  // Create an entity
  const {entityKey, txHash} = await client.createEntity({
    payload: jsonToPayload({
      entity: {
        entityType: "document",
        entityId: "doc-123",
        entityContent: "Hello World! This is my first document stored on Arkiv.",
      },
    }),
    contentType: "application/json",
    attributes: [
      {key: "category", value: "documentation"},
      {key: "version", value: "1.0"},
    ],
    expiresIn: ExpirationTime.fromDays(30), // Entity expires in 30 days
  });

  console.log("Created entity:", entityKey);
  console.log("Transaction hash:", txHash);

  const newEntity = await publicClient.getEntity(entityKey);
  console.log("Entity:", newEntity.toJson());
}

main()
  .then(() => {
    console.log("Script executed successfully.");
    process.exit(0);
  })
  .catch((error) => {
    console.error("An error occurred during execution:");
    console.error(error);
    process.exit(1);
  });