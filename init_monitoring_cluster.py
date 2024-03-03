from elasticsearch import Elasticsearch
import json
from jinja2 import Template
import time

def index_exists(es, index_name):
    try:
        # This returns True if the index exists, False otherwise
        return es.indices.exists(index=index_name)
    except Exception as e:
        print(f"An error occurred while checking if index {index_name} exists: {e}")
        return False  # Assuming non-existence if there's an error
    
def enrich_policy_exists(es, policy_name):
    try:
        es.enrich.get_policy(name=policy_name)
        return True
    except Exception:
        return False

def ingest_pipeline_exists(es, pipeline_id):
    try:
        es.ingest.get_pipeline(id=pipeline_id)
        return True
    except Exception:
        return False

def component_template_exists(es, template_name):
    try:
        es.cluster.get_component_template(name=template_name)
        return True
    except Exception:
        return False

def index_template_exists(es, template_name):
    try:
        es.indices.get_index_template(name=template_name)
        return True
    except Exception:
        return False

def transform_exists(es, transform_id):
    try:
        es.transform.get_transform(transform_id=transform_id)
        return True
    except Exception:
        return False

def watcher_exists(es, watcher_id):
    try:
        es.watcher.get_watch(id=watcher_id)
        return True
    except Exception:
        return False

def setup_remote_settings_with_jinja(es, config, remote_settings_path):
    with open(remote_settings_path, 'r') as file:
        template_content = file.read()

    template = Template(template_content)
    remote_settings_config_str = template.render(proxy_address=config['remote_cluster']['proxy_address'], server_name=config['remote_cluster']['server_name'])

    remote_settings_config = json.loads(remote_settings_config_str)
    es.cluster.put_settings(body=remote_settings_config)
    print("Cross Cluster Set-up")

def setup_watcher_with_jinja(es, config, watcher_template_path):
    watcher_id = "policy-execute"
    if watcher_exists(es, watcher_id):
        print("Watcher already exists in cluster.")
    else:
        with open(watcher_template_path, 'r') as file:
            template_content = file.read()
        
        template = Template(template_content)
        watcher_config_str = template.render(host=config['watcher_monitoring']['host'], api_key=config['watcher_monitoring']['api_key'])

        watcher_config = json.loads(watcher_config_str)
        es.watcher.put_watch(id=watcher_id, body=watcher_config)
        print("Watcher setup in cluster.")

def setup_monitoring_cluster(config):
    es = Elasticsearch(cloud_id=config['monitoring_cluster']['cloud_id'], api_key=config['monitoring_cluster']['api_key'])
    
    setup_remote_settings_with_jinja(es, config, '_meta/monitoring_cluster/cluster-settings.json')

    index_name = "kibana_objects-01"
    if index_exists(es, index_name):
        print(f"Index {index_name} already exists")

    else:
        # Proceed with CCR setup if the index does not exist
        with open('_meta/monitoring_cluster/ccr.json') as f:
            ccr_body = json.load(f)
        es.ccr.follow(body=ccr_body, index=index_name)
        print("Follower index created")

    policy_name = "objectid-policy"
    if enrich_policy_exists(es, policy_name):
        print("Enrich policy already exists")
    else:
        with open('_meta/monitoring_cluster/enrich.json') as f:
            enrich_body = json.load(f)
        es.enrich.put_policy(name=policy_name, body=enrich_body)
        print("Enrich policy created")

    es.enrich.execute_policy(name=policy_name, wait_for_completion=True)
    print("Enrich policy executed")

    pipeline_id = "enrich-ids"
    if ingest_pipeline_exists(es, pipeline_id):
        print("Ingest pipeline already exists in monitoring cluster.")
    else:
        with open('_meta/monitoring_cluster/ingest-pipeline.json') as f:
            pipeline_body = json.load(f)
        es.ingest.put_pipeline(id=pipeline_id, body=pipeline_body)
        print("Ingest pipeline created in monitoring cluster.")

    component_template_name = "transform-obj"
    if component_template_exists(es, component_template_name):
        print("Component template already exists in monitoring cluster.")
    else:
        with open('_meta/monitoring_cluster/component-template.json') as f:
            template_body = json.load(f)
        es.cluster.put_component_template(name=component_template_name, body=template_body)
        print("Component template created in monitoring cluster.")

    index_template_name = "kibana-transform"
    if index_template_exists(es, index_template_name):
        print("Index template already exists in monitoring cluster.")
    else:
        with open('_meta/monitoring_cluster/index-template.json') as f:
            template_body = json.load(f)
        es.indices.put_index_template(name=index_template_name, body=template_body)
        print("Index template created in monitoring cluster.")

    transform_id = "kibana-transform-01"
    if transform_exists(es, transform_id):
        print("Transform already exists in monitoring cluster.")
    else:
        with open('_meta/monitoring_cluster/transform.json') as f:
            transform_body = json.load(f)
        es.transform.put_transform(transform_id=transform_id, body=transform_body)
        print("Transform created in monitoring cluster.")

    es.transform.start_transform(transform_id=transform_id)
    print("Transform started")

    setup_watcher_with_jinja(es, config, '_meta/monitoring_cluster/watcher.json')

    return es
