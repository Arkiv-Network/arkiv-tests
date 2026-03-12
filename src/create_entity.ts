import {
  createPublicClient,
  createWalletClient,
  defineChain,
  http,
} from "@arkiv-network/sdk";
import { privateKeyToAccount } from "@arkiv-network/sdk/accounts";
import { ExpirationTime, jsonToPayload } from "@arkiv-network/sdk/utils";
import {eq, QueryBuilder} from "@arkiv-network/sdk/query";
import {Hex} from "viem";


async function main() {
  let privateKey = process.env.PRIVATE_KEY || "6df676dadffad9321e02bd00209e3cce4546a314c37e85f744b40dc25113f200";
  if (!privateKey) {
    throw new Error("PRIVATE_KEY is not set in the env");
  }
  privateKey = privateKey.replace('0x', '');

  const account = privateKeyToAccount(`0x${privateKey}`);

  const l3Testnet = defineChain({
    id: 42069,
    name: "Arkiv L3 Testnet",
    network: "l3-testnet",
    nativeCurrency: {
      name: "Golem",
      symbol: "GLM",
      decimals: 18,
    },
    rpcUrls: {
      default: {
        http: ["http://localhost:8645"],
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
      {key: "category", value: "simple-test"},
      {key: "version", value: "1.0"},
    ],
    expiresIn: ExpirationTime.fromMinutes(10), // Entity expires in 30 days
  });

  console.log("Created entity:", entityKey);
  console.log("Transaction hash:", txHash);

  const newEntity = await publicClient.getEntity(entityKey);
  console.log("Entity:", newEntity.toJson());

  const builder = new QueryBuilder(publicClient)
  const res = await builder
    .where(eq("category", "simple-test"))
    .createdBy(account.address)
    .ownedBy(account.address)
    .fetch();
  console.log("Query builder result:", res.entities.map(e => e.key));

  const query = await publicClient.query(`$owner=${account.address} && $creator=${account.address} && category="simple-test"`, {
    includeData: {
      attributes: true,
      payload: true,
      metadata: true,
    }
  });
  if (query.entities.length === 0) {
    throw Error("No entities found for the query");
  }
  if (query.entities.length > 1) {
    throw Error("More than 1 entity found for the query, expected only 1");
  }
  const ent = query.entities[0];

  console.log("  Hex: ", ent.key);
  console.log("  Content Type: ", ent.contentType);
  console.log("  Creator: ", ent.creator);
  console.log("  Owner: ", ent.owner);
  console.log("  Expires At Block: ", ent.expiresAtBlock);
  console.log("  Created At Block: ", ent.createdAtBlock);
  console.log("  Last Modified At Block: ", ent.lastModifiedAtBlock);
  console.log("  Transaction Index In Block: ", ent.transactionIndexInBlock);
  console.log("  Operation Index In Transaction: ", ent.operationIndexInTransaction);
  console.log(`  Attributes: (${ent.attributes.length})`);
  for (const attr of ent.attributes) {
    console.log(`    - ${attr.key}: ${attr.value}`);
  }
  console.log("Entity payload:", ent.toJson());
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