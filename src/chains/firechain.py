# SPDX-License-Identifier: FSL-1.1-MIT
import json
from pathlib import Path

FIRECHAIN_CHAIN_ID = 917
FIRECHAIN_NAME = "Firechain Testnet"
FIRECHAIN_SHORT_NAME = "fire"
FIRECHAIN_DESCRIPTION = "Firechain Testnet"
FIRECHAIN_RPC_URL = "https://rpc-fallback.firestation.io"
FIRECHAIN_TRANSACTION_SERVICE_URL = "http://nginx:8000/txs"
FIRECHAIN_CONTRACT_ADDRESSES = {
    "safe_singleton_address": "0xEdd160fEBBD92E350D4D398fb636302fccd67C7e",
    "safe_proxy_factory_address": "0x14F2982D601c9458F93bd70B218933A6f8165e7b",
    "multi_send_address": "0x218543288004CD07832472D464648173c77D7eB7",
    "multi_send_call_only_address": "0xA83c336B20401Af773B6219BA5027174338D1836",
    "fallback_handler_address": "0x3EfCBb83A4A7AfcB4F68D501E2c2203a38be77f4",
    "sign_message_lib_address": "0x4FfeF8222648872B3dE295Ba1e49110E61f5b5aa",
    "create_call_address": "0x2Ef5ECfbea521449E4De05EDB1ce63B75eDA90B4",
    "simulate_tx_accessor_address": "0x07EfA797c55B5DdE3698d876b277aBb6B893654C",
}

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


def get_firechain_contract_addresses(
    deployments_dir: Path | None = None,
) -> dict[str, str]:
    if deployments_dir is None:
        return FIRECHAIN_CONTRACT_ADDRESSES.copy()
    return load_firechain_contract_addresses(deployments_dir)
