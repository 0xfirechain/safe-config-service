# SPDX-License-Identifier: FSL-1.1-MIT
import base64
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase, override_settings

from chains.firechain import (
    FIRECHAIN_CHAIN_ID,
    FIRECHAIN_CONTRACT_ADDRESSES,
    FIRECHAIN_DEPLOYMENT_FILES,
)
from chains.models import Chain

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aP2cAAAAASUVORK5CYII="
)


@override_settings(CGW_URL=None, CGW_AUTH_TOKEN="test-token")
class UpsertFirechainCommandTests(TestCase):
    def test_create_firechain_from_canonical_defaults(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            chain_logo_path = self._write_logo(temp_path / "chain-logo.png")
            currency_logo_path = self._write_logo(temp_path / "currency-logo.png")

            with override_settings(MEDIA_ROOT=temp_path / "media"):
                call_command(
                    "upsert_firechain",
                    explorer_base_url="https://explorer.firechain.example",
                    chain_logo_path=str(chain_logo_path),
                    currency_logo_path=str(currency_logo_path),
                )

            chain = Chain.objects.get(pk=FIRECHAIN_CHAIN_ID)
            self.assertEqual(chain.short_name, "fire")
            self.assertEqual(
                chain.safe_singleton_address,
                FIRECHAIN_CONTRACT_ADDRESSES["safe_singleton_address"],
            )
            self.assertEqual(
                chain.safe_proxy_factory_address,
                FIRECHAIN_CONTRACT_ADDRESSES["safe_proxy_factory_address"],
            )

    def test_create_firechain_from_deployments(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            deployments_dir = self._create_deployments(
                temp_path / "deployments",
                {
                    "SafeL2.json": "0xEdd160fEBBD92E350D4D398fb636302fccd67C7e",
                    "SafeProxyFactory.json": "0x14F2982D601c9458F93bd70B218933A6f8165e7b",
                    "MultiSend.json": "0x218543288004CD07832472D464648173c77D7eB7",
                    "MultiSendCallOnly.json": "0xA83c336B20401Af773B6219BA5027174338D1836",
                    "CompatibilityFallbackHandler.json": "0x3EfCBb83A4A7AfcB4F68D501E2c2203a38be77f4",
                    "SignMessageLib.json": "0x4FfeF8222648872B3dE295Ba1e49110E61f5b5aa",
                    "CreateCall.json": "0x2Ef5ECfbea521449E4De05EDB1ce63B75eDA90B4",
                    "SimulateTxAccessor.json": "0x07EfA797c55B5DdE3698d876b277aBb6B893654C",
                },
            )
            chain_logo_path = self._write_logo(temp_path / "chain-logo.png")
            currency_logo_path = self._write_logo(temp_path / "currency-logo.png")

            with override_settings(MEDIA_ROOT=temp_path / "media"):
                call_command(
                    "upsert_firechain",
                    deployments_dir=str(deployments_dir),
                    explorer_base_url="https://explorer.firechain.example",
                    chain_logo_path=str(chain_logo_path),
                    currency_logo_path=str(currency_logo_path),
                )

            chain = Chain.objects.get(pk=FIRECHAIN_CHAIN_ID)
            self.assertEqual(chain.short_name, "fire")
            self.assertTrue(chain.l2)
            self.assertTrue(chain.is_testnet)
            self.assertFalse(chain.zk)
            self.assertEqual(chain.recommended_master_copy_version, "1.5.0")
            self.assertEqual(
                chain.safe_singleton_address,
                "0xEdd160fEBBD92E350D4D398fb636302fccd67C7e",
            )
            self.assertEqual(
                chain.safe_proxy_factory_address,
                "0x14F2982D601c9458F93bd70B218933A6f8165e7b",
            )
            self.assertEqual(
                chain.block_explorer_uri_address_template,
                "https://explorer.firechain.example/address/{{address}}",
            )
            self.assertEqual(
                chain.block_explorer_uri_tx_hash_template,
                "https://explorer.firechain.example/tx/{{txHash}}",
            )
            self.assertEqual(chain.transaction_service_uri, "http://nginx:8000/txs")
            self.assertTrue(chain.chain_logo_uri.name)
            self.assertTrue(chain.currency_logo_uri.name)

    def test_update_firechain_keeps_existing_logos(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            initial_deployments = self._create_deployments(
                temp_path / "deployments-initial",
                {
                    deployment_file: f"0x{index:040x}"
                    for index, deployment_file in enumerate(
                        FIRECHAIN_DEPLOYMENT_FILES.values(), start=1
                    )
                },
            )
            updated_deployments = self._create_deployments(
                temp_path / "deployments-updated",
                {
                    deployment_file: f"0x{index + 100:040x}"
                    for index, deployment_file in enumerate(
                        FIRECHAIN_DEPLOYMENT_FILES.values(), start=1
                    )
                },
            )
            currency_logo_path = self._write_logo(temp_path / "currency-logo.png")

            with override_settings(MEDIA_ROOT=temp_path / "media"):
                call_command(
                    "upsert_firechain",
                    deployments_dir=str(initial_deployments),
                    currency_logo_path=str(currency_logo_path),
                )

                initial_chain = Chain.objects.get(pk=FIRECHAIN_CHAIN_ID)
                initial_logo_name = initial_chain.currency_logo_uri.name

                call_command(
                    "upsert_firechain",
                    deployments_dir=str(updated_deployments),
                    transaction_service_url="https://txs.firechain.example",
                )

            chain = Chain.objects.get(pk=FIRECHAIN_CHAIN_ID)
            self.assertEqual(Chain.objects.count(), 1)
            self.assertEqual(chain.currency_logo_uri.name, initial_logo_name)
            self.assertEqual(chain.transaction_service_uri, "https://txs.firechain.example")
            self.assertEqual(chain.safe_singleton_address, f"0x{101:040x}")

    def _create_deployments(
        self, deployments_dir: Path, address_map: dict[str, str]
    ) -> Path:
        deployments_dir.mkdir(parents=True, exist_ok=True)
        (deployments_dir / ".chainId").write_text(f"{FIRECHAIN_CHAIN_ID}\n")
        for deployment_file, address in address_map.items():
            (deployments_dir / deployment_file).write_text(
                json.dumps({"address": address})
            )
        return deployments_dir

    def _write_logo(self, file_path: Path) -> Path:
        file_path.write_bytes(PNG_1X1)
        return file_path
