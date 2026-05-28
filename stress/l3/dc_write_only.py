"""
Locust stress test for op-geth-simulator write entities endpoint.

This test generates nodes and workloads using the same logic as append_dc_data.py
and sends them to the op-geth-simulator's POST /entities endpoint.

Usage:
    locust -f locust/write_only.py --host=http://localhost:3000
"""

import os
import random
import sys
from pathlib import Path
import logging
from typing import Any, Dict

from web3.types import TxParams
from arkiv import Arkiv
from arkiv.types import Operations, TxHash, HexStr
from arkiv.utils import to_create_op
from locust import constant, task

# Add the project root (stress-tests/) to Python path so we can import stress.*
file_dir = Path(__file__).resolve().parent
project_root = file_dir.parent.parent  # l3/ -> stress/ -> stress-tests/
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from stress.tools.arkiv_user import ArkivUser

# Add parent directory to path to import from src.db.append_dc_data (kept for backwards compat)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from stress.tools.dc_data import (
    NODE,
    WORKLOAD,
    NodeEntity,
    WorkloadEntity,
    create_node,
    create_workload,
)


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_CREATOR_ADDRESS = "0x0000000000000000000000000000000000dc0001"
DEFAULT_PAYLOAD_SIZE = int(os.getenv("DC_WRITE_ONLY_PAYLOAD_SIZE", "10000"))
REAL_DC_PAYLOAD_CONTENT = False
DEFAULT_DC_NUM = 1
DEFAULT_WORKLOADS_PER_NODE = int(os.getenv("DC_WRITE_ONLY_WORKLOADS_PER_NODE", "5"))
DEFAULT_BLOCK = 1  # Starting block number (will be incremented per user)
DEFAULT_BLOCK_DURATION_SECONDS = 2


# =============================================================================
# Entity Transformation (Arkiv attributes)
# =============================================================================

def node_to_arkiv_attributes(node: NodeEntity, creator_address: str) -> Dict[str, Any]:
    """
    Build Arkiv attributes for a NodeEntity.

    Note: we keep the same attribute names as the previous HTTP endpoint payloads.
    """
    entity_key = node.entity_key
    block = node.block

    # String attributes
    string_attrs: Dict[str, Any] = {
        "dc_id": node.dc_id,
        "type": NODE,
        "node_id": node.node_id,
        "region": node.region,
        "status": node.status,
        "vm_type": node.vm_type,
    }

    # Numeric attributes
    numeric_attrs: Dict[str, Any] = {
        "cpu_count": node.cpu_count,
        "ram_gb": node.ram_gb,
        "price_hour": node.price_hour,
        "avail_hours": node.avail_hours,
    }

    return {**string_attrs, **numeric_attrs}


def workload_to_arkiv_attributes(
    workload: WorkloadEntity, creator_address: str
) -> Dict[str, Any]:
    """
    Build Arkiv attributes for a WorkloadEntity.

    Note: we keep the same attribute names as the previous HTTP endpoint payloads.
    """
    entity_key = workload.entity_key
    block = workload.block

    # String attributes
    string_attrs: Dict[str, Any] = {
        "dc_id": workload.dc_id,
        "type": WORKLOAD,
        "workload_id": workload.workload_id,
        "status": workload.status,
        "assigned_node": workload.assigned_node,
        "region": workload.region,
        "vm_type": workload.vm_type
    }

    # Numeric attributes
    numeric_attrs: Dict[str, Any] = {
        "req_cpu": workload.req_cpu,
        "req_ram": workload.req_ram,
        "max_hours": workload.max_hours,
    }

    return {**string_attrs, **numeric_attrs}


# =============================================================================
# Locust User Class
# =============================================================================

class DataCenterUser(ArkivUser):
    """
    Locust user that generates nodes and workloads and sends them to op-geth-simulator.

    Each user maintains its own counters for unique entity IDs.
    """
    wait_time = constant(1)

    # Per-user state
    node_counter: int = 0
    workload_counter: int = 0
    current_block: int = DEFAULT_BLOCK
    seed: int = None
    creator_address: str = DEFAULT_CREATOR_ADDRESS
    payload_size: int = DEFAULT_PAYLOAD_SIZE
    dc_num: int = DEFAULT_DC_NUM
    workloads_per_node: int = DEFAULT_WORKLOADS_PER_NODE
    real_dc_payload_content: bytes | None = None

    if (REAL_DC_PAYLOAD_CONTENT):
        # load real dc payload content from file
        with open(f"stress/l3/sample_sys_x5.payload", "rb") as f:
            real_dc_payload_content = f.read()
    
    @task
    def write_node_with_workloads(self):
        """
        Generate one node and 5 workloads for that node, then send them to the API.
        
        This is the main task that will be executed repeatedly.
        """
        # Increment counters
        self.node_counter += 1
        self.current_block += 1
        
        # Create the node
        node = create_node(
            dc_num=self.dc_num,
            node_num=self.node_counter,
            payload_size=self.payload_size,
            payload_content=self.real_dc_payload_content,
            block=self.current_block,
            seed=self.seed,
        )

        ttl_blocks = random.randint(100, 1000)
        expires_in_seconds = self._expires_in_seconds_from_blocks(ttl_blocks)

        create_ops = [
            to_create_op(
                payload=node.payload,
                content_type="application/octet-stream",
                attributes=node_to_arkiv_attributes(node, self.creator_address),
                expires_in=node.ttl,
            )
        ]
        
        # Create workloads for this node
        # First workload is assigned if node is busy
        is_busy = node.status == "busy"
        
        for wl_idx in range(self.workloads_per_node):
            self.workload_counter += 1
            
            # First workload is assigned if node is busy
            if is_busy and wl_idx == 0:
                wl_status = "running"
                wl_assigned = node.node_id
            else:
                wl_status = "pending"
                wl_assigned = ""
            
            # Create workload
            workload = create_workload(
                dc_num=self.dc_num,
                workload_num=self.workload_counter,
                nodes_per_dc=self.node_counter,  # Not used when assigned_node provided
                payload_size=self.payload_size,
                payload_content=self.real_dc_payload_content,
                block=self.current_block,
                seed=self.seed,
                status=wl_status,
                assigned_node=wl_assigned,
            )

            create_ops.append(
                to_create_op(
                    payload=workload.payload,
                    content_type="application/octet-stream",
                    attributes=workload_to_arkiv_attributes(workload, self.creator_address),
                    expires_in=workload.ttl,
                )
            )

        w3 = self._initialize_account_and_w3()
        operations = Operations(creates=create_ops)
        nonce = w3.eth.get_transaction_count(self.account.address)
        logging.info(f"Sending tx by user {self.id} with nonce: {nonce}, address: {self.account.address}")
        self._fire_locust_request("write_node_with_workloads", lambda: custom_execute(w3, operations, TxParams(nonce=nonce)))
        logging.info(f"Tx sent by user {self.id} with nonce: {nonce}, address: {self.account.address}")


def custom_execute(w3: Arkiv, operations: Operations, tx_params: TxParams) -> Any:
    # Send transaction and get tx hash
    return w3.arkiv.execute(operations, tx_params)
