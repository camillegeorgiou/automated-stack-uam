# Stack UAM Automation

This package deploys the end-to-end assets to enable end-user activity monitoring.

The init_main_cluster and init_monitoring_cluster scripts set up each cluster, respectively.

Some manual steps are still required:

1. Enable auditing at the deployment level, as per instructions 1&2 in the main repo.

1. Update the clusters_config.json file to include values for each of the variables.

2. Run pip install -r requirements.txt

3. Run 'python main.py'

4. Import the dashboards located in: kibana_assets 
