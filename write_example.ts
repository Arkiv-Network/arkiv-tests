import { createPublicClient, createWalletClient, http } from "@arkiv-network/sdk"
import { privateKeyToAccount } from "@arkiv-network/sdk/accounts"
import { mendoza } from "@arkiv-network/sdk/chains"
import { ExpirationTime, jsonToPayload } from "@arkiv-network/sdk/utils"
import * as viem17 from "viem";

declare const dev: {
  blockTime?: number | undefined | undefined;
  contracts?: {
    [x: string]: viem17.ChainContract | {
      [sourceId: number]: viem17.ChainContract | undefined;
    } | undefined;
    ensRegistry?: viem17.ChainContract | undefined;
    ensUniversalResolver?: viem17.ChainContract | undefined;
    multicall3?: viem17.ChainContract | undefined;
    erc6492Verifier?: viem17.ChainContract | undefined;
  } | undefined;
  ensTlds?: readonly string[] | undefined;
  id: 60138453056;
  name: "Mendoza";
  nativeCurrency: {
    readonly name: "Ethereum";
    readonly symbol: "ETH";
    readonly decimals: 18;
  };
  experimental_preconfirmationTime?: number | undefined | undefined;
  rpcUrls: {
    readonly default: {
      readonly http: readonly ["http://127.0.0.1:8545"];
      readonly webSocket: readonly ["wss://127.0.0.1:8545"];
    };
  };
  sourceId?: number | undefined | undefined;
  testnet: true;
  custom?: Record<string, unknown> | undefined;
  fees?: viem17.ChainFees<undefined> | undefined;
  formatters?: undefined;
  serializers?: viem17.ChainSerializers<undefined, viem17.TransactionSerializable> | undefined;
  readonly network: "dev";
};

async function main() {
// Create a public client
  const publicClient = createPublicClient({
    chain: dev, // mendoza is the Arkiv testnet for the purposes of hackathons organized in Buenos Aires during devconnect 2025
    transport: http(),
  })
// Create a wallet client with an account
  const client = createWalletClient({
    chain: dev,
    transport: http(),
    account: privateKeyToAccount('0x...'), // Replace with your private key
  });

// Create an entity
  const {entityKey, txHash} = await client.createEntity({
    payload: jsonToPayload({
      entity: {
        entityType: 'document',
        entityId: 'doc-123',
        entityContent: "Hello from DevConnect Hackathon 2025! Arkiv Mendoza chain wishes you all the best!"
      },
    }),
    contentType: 'application/json',
    attributes: [
      {key: 'category', value: 'documentation'},
      {key: 'version', value: '1.0'},
    ],
    expiresIn: ExpirationTime.fromDays(30), // Entity expires in 30 days
  });

  console.log('Created entity:', entityKey);
  console.log('Transaction hash:', txHash);

  const newEntity = await publicClient.getEntity(entityKey);
  console.log('Entity:', newEntity);
}

main().catch((error) => {
  console.error('Error executing main function:', error);
  process.exit(1);
}