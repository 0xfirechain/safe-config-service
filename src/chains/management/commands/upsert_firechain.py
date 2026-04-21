# SPDX-License-Identifier: FSL-1.1-MIT
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from django.core.files.base import ContentFile, File
from django.core.management.base import BaseCommand, CommandError

from chains.firechain import (
    FIRECHAIN_CHAIN_ID,
    FIRECHAIN_DESCRIPTION,
    FIRECHAIN_NAME,
    FIRECHAIN_RPC_URL,
    FIRECHAIN_SHORT_NAME,
    FIRECHAIN_TRANSACTION_SERVICE_URL,
    get_default_firechain_deployments_dir,
    load_firechain_contract_addresses,
)
from chains.models import Chain


class Command(BaseCommand):
    help = "Create or update the Firechain chain entry from safe-smart-account deployment artifacts"

    def add_arguments(self, parser):
        parser.add_argument(
            "--deployments-dir",
            default=str(get_default_firechain_deployments_dir()),
            help="Path to safe-smart-account/deployments/firechain",
        )
        parser.add_argument("--chain-name", default=FIRECHAIN_NAME)
        parser.add_argument("--short-name", default=FIRECHAIN_SHORT_NAME)
        parser.add_argument("--description", default=FIRECHAIN_DESCRIPTION)
        parser.add_argument("--rpc-url", default=FIRECHAIN_RPC_URL)
        parser.add_argument("--safe-apps-rpc-url")
        parser.add_argument("--public-rpc-url")
        parser.add_argument(
            "--transaction-service-url", default=FIRECHAIN_TRANSACTION_SERVICE_URL
        )
        parser.add_argument("--vpc-transaction-service-url")
        parser.add_argument("--vpc-rpc-url")
        parser.add_argument("--currency-name", default="Firechain")
        parser.add_argument("--currency-symbol", default="FIRE")
        parser.add_argument("--currency-decimals", default=18, type=int)
        parser.add_argument("--recommended-master-copy-version", default="1.5.0")
        parser.add_argument("--theme-text-color", default="#ffffff")
        parser.add_argument("--theme-background-color", default="#000000")
        parser.add_argument("--explorer-base-url")
        parser.add_argument("--block-explorer-address-template")
        parser.add_argument("--block-explorer-tx-template")
        parser.add_argument("--block-explorer-api-template")
        parser.add_argument("--chain-logo-path")
        parser.add_argument("--currency-logo-path")
        parser.add_argument("--chain-logo-url")
        parser.add_argument("--currency-logo-url")
        parser.add_argument("--relevance", default=100, type=int)

    def handle(self, *args, **options):
        deployments_dir = Path(options["deployments_dir"]).expanduser().resolve()
        if not deployments_dir.exists():
            raise CommandError(f"Deployments dir not found: {deployments_dir}")

        chain = Chain.objects.filter(pk=FIRECHAIN_CHAIN_ID).first()
        creating = chain is None
        if chain is None:
            chain = Chain(id=FIRECHAIN_CHAIN_ID)

        chain.name = options["chain_name"]
        chain.short_name = options["short_name"]
        chain.description = options["description"]
        chain.relevance = options["relevance"]
        chain.l2 = True
        chain.is_testnet = True
        chain.zk = False
        chain.hidden = False
        chain.rpc_authentication = Chain.RpcAuthentication.NO_AUTHENTICATION
        chain.rpc_uri = options["rpc_url"]
        chain.safe_apps_rpc_authentication = Chain.RpcAuthentication.NO_AUTHENTICATION
        chain.safe_apps_rpc_uri = options["safe_apps_rpc_url"] or options["rpc_url"]
        chain.public_rpc_authentication = Chain.RpcAuthentication.NO_AUTHENTICATION
        chain.public_rpc_uri = options["public_rpc_url"] or options["rpc_url"]
        chain.transaction_service_uri = options["transaction_service_url"]
        chain.vpc_transaction_service_uri = (
            options["vpc_transaction_service_url"]
            or options["transaction_service_url"]
        )
        chain.vpc_rpc_uri = options["vpc_rpc_url"] or options["rpc_url"]
        chain.currency_name = options["currency_name"]
        chain.currency_symbol = options["currency_symbol"]
        chain.currency_decimals = options["currency_decimals"]
        chain.theme_text_color = options["theme_text_color"]
        chain.theme_background_color = options["theme_background_color"]
        chain.recommended_master_copy_version = options[
            "recommended_master_copy_version"
        ]
        chain.balances_provider_enabled = False

        address_template, tx_template, api_template = self._get_block_explorer_templates(
            chain, options
        )
        chain.block_explorer_uri_address_template = address_template
        chain.block_explorer_uri_tx_hash_template = tx_template
        chain.block_explorer_uri_api_template = api_template

        contract_addresses = load_firechain_contract_addresses(deployments_dir)
        for field_name, address in contract_addresses.items():
            setattr(chain, field_name, address)

        self._assign_logo(
            chain,
            field_name="chain_logo_uri",
            file_path=options["chain_logo_path"],
            file_url=options["chain_logo_url"],
            required=False,
            creating=creating,
        )
        self._assign_logo(
            chain,
            field_name="currency_logo_uri",
            file_path=options["currency_logo_path"],
            file_url=options["currency_logo_url"],
            required=True,
            creating=creating,
        )

        chain.full_clean()
        chain.save()

        action = "Created" if creating else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} Firechain chain config with SafeL2 {chain.safe_singleton_address}"
            )
        )

    def _assign_logo(
        self,
        chain: Chain,
        *,
        field_name: str,
        file_path: str | None,
        file_url: str | None,
        required: bool,
        creating: bool,
    ) -> None:
        if file_path and file_url:
            raise CommandError(
                f"Provide only one of --{field_name.replace('_uri', '').replace('_', '-')}-path or --{field_name.replace('_uri', '').replace('_', '-')}-url"
            )

        if file_path:
            path = Path(file_path).expanduser().resolve()
            if not path.exists():
                raise CommandError(f"Logo file not found: {path}")
            with path.open("rb") as file_obj:
                getattr(chain, field_name).save(path.name, File(file_obj), save=False)
            return

        if file_url:
            parsed = urlparse(file_url)
            filename = Path(parsed.path).name or f"{field_name}.png"
            with urlopen(file_url, timeout=30) as response:
                content = response.read()
            getattr(chain, field_name).save(
                filename, ContentFile(content), save=False
            )
            return

        if required and creating and not getattr(chain, field_name):
            option_name = field_name.replace("_uri", "").replace("_", "-")
            raise CommandError(
                f"New Firechain chain requires --{option_name}-path or --{option_name}-url"
            )

    def _get_block_explorer_templates(
        self, chain: Chain, options: dict[str, str | int | None]
    ) -> tuple[str, str, str]:
        address_template = options["block_explorer_address_template"]
        tx_template = options["block_explorer_tx_template"]
        api_template = options["block_explorer_api_template"]

        if address_template and tx_template and api_template:
            return address_template, tx_template, api_template

        explorer_base_url = options["explorer_base_url"]
        if explorer_base_url:
            base_url = explorer_base_url.rstrip("/")
            return (
                address_template or f"{base_url}/address/{{{{address}}}}",
                tx_template or f"{base_url}/tx/{{{{txHash}}}}",
                api_template
                or f"{base_url}/api?module={{{{module}}}}&action={{{{action}}}}&address={{{{address}}}}&apiKey={{{{apiKey}}}}",
            )

        if chain.pk:
            return (
                address_template or chain.block_explorer_uri_address_template,
                tx_template or chain.block_explorer_uri_tx_hash_template,
                api_template or chain.block_explorer_uri_api_template,
            )

        return (
            address_template or "https://placeholderURL/address/{{address}}",
            tx_template or "https://placeholderURL/tx/{{txHash}}",
            api_template
            or "https://placeholderURL/api?module={{module}}&action={{action}}&address={{address}}&apiKey={{apiKey}}",
        )
