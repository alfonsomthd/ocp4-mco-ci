import logging
import sys
import multiprocessing as mp

from src.deployment.ocp import OCPDeployment
from src import framework
from src.framework.logger_factory import set_log_record_factory
from src.utility.constants import LOG_FORMAT
from src.utility.utils import is_cluster_running
from src.utility.utils import email_reports

log = logging.getLogger(__name__)
current_factory = logging.getLogRecordFactory()
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(LOG_FORMAT))
log.addHandler(handler)

def set_log_level(log_cli_level):
    """
            Set the log level of this module based on the pytest.ini log_cli_level
            Args:
                config (pytest.config): Pytest config object
            """
    level = log_cli_level or "INFO"
    log.setLevel(logging.getLevelName(level))

class Deployment(object):
    def __init__(self):
        set_log_record_factory()
        set_log_level(framework.config.RUN['log_level'])

    def deploy_ocp(self, log_cli_level):
        # OCP Deployment
        processes = []
        for i in range(framework.config.nclusters):
            framework.config.switch_ctx(i)
            cluster_path = framework.config.ENV_DATA["cluster_path"]
            cluster_name = framework.config.ENV_DATA["cluster_name"]
            if not framework.config.ENV_DATA.get("skip_ocp_deployment", True):
                if is_cluster_running(cluster_path):
                    log.warning(f"OCP cluster is already running, skipping installation")
                else:
                    ocpDeployment = OCPDeployment(cluster_name, cluster_path)
                    ocpDeployment.deploy_prereq()
                    p = mp.Process(
                        target=OCPDeployment.deploy_ocp,
                        args=(ocpDeployment.installer_binary_path, ocpDeployment.cluster_path, log_cli_level,)
                    )
                    processes.append(p)
        framework.config.switch_default_cluster_ctx()
        if len(processes) > 0:
            [proc.start() for proc in processes]
            # complete the processes
            for proc in processes:
                proc.join()
        for i in range(framework.config.nclusters):
            framework.config.switch_ctx(i)
            if is_cluster_running(cluster_path):
                framework.config.available_ocp_cluster_ctx_list.append(i)
        framework.config.switch_default_cluster_ctx()
    def send_email(self):
        # send email notification
        email_reports()
