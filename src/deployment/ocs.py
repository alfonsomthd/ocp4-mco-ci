import logging
import tempfile
import time

from src.framework import config
from src.utility import (constants, templating, version, defaults)
from src.utility.cmd import exec_cmd
from src.ocs.resources.package_manifest import PackageManifest
from src.ocs.resources.package_manifest import get_selector_for_ocs_operator
from src.deployment.operator_deployment import OperatorDeployment


logger = logging.getLogger(__name__)

class OCSDeployment(OperatorDeployment):
    def __init__(self):
        super().__init__(constants.OPENSHIFT_STORAGE_NAMESPACE)

    def deploy_prereq(self):
        # create OCS catalog source
        self.create_catalog_source()
        # deploy ocs operator
        self.ocs_subscription()
        # enable odf-console plugin
        self.enable_console_plugin(constants.OCS_PLUGIN_NAME, config.ENV_DATA.get("enable_ocs_plugin"))

    def ocs_subscription(self):
        logger.info("Creating namespace and operator group.")
        exec_cmd(f"oc apply -f {constants.OLM_YAML}")
        operator_selector = get_selector_for_ocs_operator()
        # For OCS version >= 4.9, we have odf-operator
        ocs_version = version.get_semantic_ocs_version_from_config()
        if ocs_version >= version.VERSION_4_9:
            ocs_operator_name = defaults.ODF_OPERATOR_NAME
            subscription_file = constants.SUBSCRIPTION_ODF_YAML
        else:
            ocs_operator_name = defaults.OCS_OPERATOR_NAME
            subscription_file = constants.SUBSCRIPTION_YAML
        package_manifest = PackageManifest(
            resource_name=ocs_operator_name,
            selector=operator_selector,
        )
        # Wait for package manifest is ready
        package_manifest.wait_for_resource(timeout=300)
        default_channel = package_manifest.get_default_channel()
        subscription_yaml_data = templating.load_yaml(subscription_file)
        custom_channel = config.DEPLOYMENT.get("ocs_csv_channel")
        if custom_channel:
            logger.info(f"Custom channel will be used: {custom_channel}")
            subscription_yaml_data["spec"]["channel"] = custom_channel
        else:
            logger.info(f"Default channel will be used: {default_channel}")
            subscription_yaml_data["spec"]["channel"] = default_channel
        if config.DEPLOYMENT.get("stage"):
            subscription_yaml_data["spec"]["source"] = constants.OPERATOR_SOURCE_NAME
        subscription_manifest = tempfile.NamedTemporaryFile(
            mode="w+", prefix="subscription_manifest", delete=False
        )
        templating.dump_data_to_temp_yaml(
            subscription_yaml_data, subscription_manifest.name
        )
        exec_cmd(f"oc apply -f {subscription_manifest.name}")
        self.wait_for_subscription(ocs_operator_name)
        self.wait_for_csv(ocs_operator_name)
        logger.info("Sleeping for 30 seconds after CSV created")
        time.sleep(30)

    def create_config(self):
        pass

    @staticmethod
    def deploy_ocs(log_cli_level="INFO"):
        pass
