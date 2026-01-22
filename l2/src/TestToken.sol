// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract TestToken is ERC20 {
    constructor() ERC20("Test Token", "TEST") {
        // Mint 1,000,000 tokens to the msg.sender (the deployer)
        _mint(msg.sender, 1000000 * 10 ** decimals());
    }
}