# SPDX-License-Identifier: FSL-1.1-MIT
import json
from pathlib import Path

FIRECHAIN_CHAIN_ID = 917
FIRECHAIN_NAME = "Firechain Testnet"
FIRECHAIN_SHORT_NAME = "fire"
FIRECHAIN_DESCRIPTION = "Firechain Testnet"
FIRECHAIN_RPC_URL = "https://rpc-fallback.firestation.io"
FIRECHAIN_TRANSACTION_SERVICE_URL = "http://nginx:8000/txs"

FIRECHAIN_DEPLOYMENT_FILES = {
    "safe_singleton_address": "SafeL2.json",
    "safe_proxy_factory_address": "SafeProxyFactory.json",
    "multi_send_address": "MultiSend.json",
    "multi_send_call_only_address": "MultiSendCallOnly.json",
    "fallback_handler_address": "CompatibilityFallbackHandler.json",
    "sign_message_lib_address": "SignMessageLib.json",
    "create_call_address": "CreateCall.json",
    "simulate_tx_accessor_address": "SimulateTxAccessor.json",
}


def get_default_firechain_deployments_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root.parent / "safe-smart-account" / "deployments" / "firechain"


def load_firechain_contract_addresses(deployments_dir: Path) -> dict[str, str]:
    deployment_chain_id = int((deployments_dir / ".chainId").read_text().strip())
    if deployment_chain_id != FIRECHAIN_CHAIN_ID:
        raise ValueError(
            f"Expected Firechain chain id {FIRECHAIN_CHAIN_ID}, found {deployment_chain_id}"
        )

    addresses: dict[str, str] = {}
    for field_name, deployment_file in FIRECHAIN_DEPLOYMENT_FILES.items():
        deployment = json.loads((deployments_dir / deployment_file).read_text())
        address = deployment.get("address")
        if not address:
            raise ValueError(f"Deployment file {deployment_file} is missing address")
        addresses[field_name] = address

    return addresses
