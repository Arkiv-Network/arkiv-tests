// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/TestToken.sol"; // Import your token here

// Make sure this matches the name in your command (:DeployTestToken)
contract DeployTestToken is Script {
    function run() external {
        vm.startBroadcast();
        new TestToken(); // This deploys the token
        vm.stopBroadcast();
    }
}