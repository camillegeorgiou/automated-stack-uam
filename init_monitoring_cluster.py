from elasticsearch import Elasticsearch
import json
from jinja2 import Template
import time


def setup_monitoring_cluster(config):
    es = Elasticsearch(cloud_id=config['monitoring_cluster']['cloud_id'], api_key=config['monitoring_cluster']['api_key'])
    
    # Set-up cross-cluster replication
    setup_remote_settings_with_jinja(es, config, '_meta/monitoring_cluster/cluster-settings.json')

    # Set-up cross-cluster search
    with open('_meta/monitoring_cluster/ccr.json') as f:
        ccr_body = json.load(f)
    es.ccr.follow(body=ccr_body, index="kibana_objects-01")
    print("Follower index created")

    # Put enrich processor
    with open('_meta/monitoring_cluster/enrich.json') as f:
        enrich_body = json.load(f)
    es.enrich.put_policy(name="objectid-policy", body=enrich_body)
    print("Enrich policy created")

    es.enrich.execute_policy(name="objectid-policy", wait_for_completion=True)
    print("Enrich policy executed")

     # Create ingest pipeline
    with open('_meta/monitoring_cluster/ingest-pipeline.json') as f:
        pipeline_body = json.load(f)
    es.ingest.put_pipeline(id="enrich-ids", body=pipeline_body)
    print("Ingest pipeline created in monitoring cluster.")

    # Create component template
    with open('_meta/monitoring_cluster/component-template.json') as f:
        template_body = json.load(f)
    es.cluster.put_component_template(name="transform-obj", body=template_body)
    print("Component template created in monitoring cluster.")

    # Create index template
    with open('_meta/monitoring_cluster/index-template.json') as f:
        template_body = json.load(f)
    es.indices.put_index_template(name="kibana-transform", body=template_body)
    print("Index template created in monitoring cluster.")
    
    # Create and start transform
    with open('_meta/monitoring_cluster/transform.json') as f:
        template_body = json.load(f)
    es.transform.put_transform(transform_id="kibana-transform-01", body=template_body)
    print("Transform created in monitoring cluster.")

    # Set-up watcher in mon cluster
    setup_watcher_with_jinja(es, config, '_meta/monitoring_cluster/watcher.json')
    time.sleep(30)

    es.transform.start_transform(transform_id="kibana-transform-01")
    print("Transform started")

     # Check if a certain field exists
    if not check_field_exists(es, config, index="kibana-transform-01", field_name="object_title"):
        es.transform.stop_transform(transform_id="kibana-transform-01", wait_for_completion=True)
        print("Transform stopped because the required field does not exist.")
        
        es.transform.reset_transform(transform_id="kibana-transform-01")
        print("Transform reset.")
        
        es.transform.start_transform(transform_id="kibana-transform-01")
        print("Transform restarted after resetting.")
    
    return es

def setup_remote_settings_with_jinja(es, config, remote_settings_path):
    es = Elasticsearch(cloud_id=config['monitoring_cluster']['cloud_id'], api_key=config['monitoring_cluster']['api_key'])

    with open(remote_settings_path, 'r') as file:
        template_content = file.read()

    template = Template(template_content)
    remote_settings_config_str = template.render(proxy_address=config['remote_cluster']['proxy_address'], server_name=config['remote_cluster']['server_name'])

    remote_settings_config = json.loads(remote_settings_config_str)
    es.cluster.put_settings(body=remote_settings_config)
    print("Cross Cluster Set-up")

def setup_watcher_with_jinja(es, config, watcher_template_path):
    es = Elasticsearch(cloud_id=config['monitoring_cluster']['cloud_id'], api_key=config['monitoring_cluster']['api_key'])

    with open(watcher_template_path, 'r') as file:
        template_content = file.read()

    template = Template(template_content)
    watcher_config_str = template.render(host=config['watcher_monitoring']['host'], api_key=config['watcher_monitoring']['api_key'])

    watcher_config = json.loads(watcher_config_str)
    es.watcher.put_watch(id="policy-execute", body=watcher_config)
    print("Watcher setup in mon cluster.")

def check_field_exists(es, config, index, field_name):
    es = Elasticsearch(cloud_id=config['monitoring_cluster']['cloud_id'], api_key=config['monitoring_cluster']['api_key'])
    body = {
        "query": {
            "exists": {
                "field": field_name
            }
        },
        "size": 0
    }
    response = es.search(index=index, body=body)
    return response['hits']['total']['value'] > 0